from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
import logging
import re

_logger = logging.getLogger(__name__)


class ResCompany(models.Model):
    _inherit = 'res.company'

    codigo_de_barras_por_atributos = fields.Char(
        string="Código de Barras por Atributos",
        help="Expresión para la generación de códigos de barras por atributos en PoS para esta compañía.",
    )
    disponible_tpv_por_defecto = fields.Boolean(
        string="Disponible TPV por defecto",
        default=True,
        help="Si está activo, los productos almacenables nuevos se marcarán como disponibles en TPV automáticamente.",
    )
    talla_color_requerido_en_compras = fields.Boolean(
        string="Talla y color requeridos (compras y web)",
        default=False,
        help="Si está activo, se aplican las reglas de 'Talla'/'Color' sobre los productos almacenables: "
             "en compras se exigen ambos; fuera de compra, si existe uno se exige el otro y, si faltan los "
             "dos, el producto se marca automáticamente como 'Excluido de la web'. Módulos como ws_shopify "
             "activan esta opción. (El nombre del campo se conserva por compatibilidad.)",
    )


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    codigo_de_barras_por_atributos = fields.Char(
        string="Código de Barras por Atributos",
        related='company_id.codigo_de_barras_por_atributos',
        readonly=False,
        help="Define la lógica o texto relacionado con la generación de códigos de barras por atributos en el PoS para la compañía activa.",
    )
    disponible_tpv_por_defecto = fields.Boolean(
        string="Disponible TPV por defecto",
        related='company_id.disponible_tpv_por_defecto',
        readonly=False,
        help="Marca automáticamente como disponible en TPV los productos almacenables creados cuando está activo.",
    )
    talla_color_requerido_en_compras = fields.Boolean(
        string="Talla y color requeridos (compras y web)",
        related='company_id.talla_color_requerido_en_compras',
        readonly=False,
        help="Aplica las reglas de 'Talla'/'Color': en compras se exigen ambos; fuera de compra, "
             "si existe uno se exige el otro y, si faltan los dos, se marca 'Excluido de la web'.",
    )


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    model_code = fields.Char(string='Codigo', help="Model Codigo")
    excluir_de_web = fields.Boolean(
        string="Excluir de la web / Shopify",
        default=False,
        help="Si está marcado, el producto no se sincroniza con Shopify (se salta al exportar). "
             "Se marca automáticamente al guardar un bien almacenable sin 'Talla' ni 'Color' "
             "(cuando está activa la opción de talla/color requeridos).",
    )

    @staticmethod
    def _is_purchase_context(env):
        # The custom purchase checks only apply when the product is being managed
        # from a purchase order / line. Any other write path (UI product form,
        # imports, the migrator, POS, ...) is left untouched.
        ctx = env.context
        if ctx.get('active_model') in {'purchase.order', 'purchase.order.line'}:
            return True
        # "Crear y editar" un producto desde la línea de compra NO trae
        # active_model, pero sí marcadores del origen compra: 'quotation_only'
        # (lo pone el contexto del campo product en purchase) y/o la acción web
        # 'purchase' en params. Con esto la constraint (proveedor/precio/
        # talla/color) vuelve a exigirse al crear la plantilla desde una compra.
        if ctx.get('quotation_only'):
            return True
        params = ctx.get('params') or {}
        if params.get('action') == 'purchase':
            return True
        return False

    def _wsem_missing_attributes(self, attr_names):
        # Helper reutilizable (compras, ws_shopify, ...): devuelve los nombres de
        # atributo que NO tienen ninguna línea con valores en esta plantilla.
        # No decide *cuándo* exigirlos, solo *qué* falta.
        self.ensure_one()
        missing = []
        for name in attr_names:
            lines = self.attribute_line_ids.filtered(
                lambda l: l.attribute_id.name and l.attribute_id.name.lower() == name.lower()
            )
            if not lines or not any(line.value_ids for line in lines):
                missing.append(name)
        return missing

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        # Al crear el producto desde una línea de compra, el contexto trae el
        # proveedor del pedido ('partner_id'); pre-rellenamos una línea de
        # proveedor con él para no tener que seleccionarlo (solo falta teclear el
        # precio, que la constraint exige > 0). Solo en contexto de compra.
        if 'seller_ids' in fields_list and not res.get('seller_ids') \
                and self._is_purchase_context(self.env):
            partner_id = self.env.context.get('partner_id')
            if partner_id:
                res['seller_ids'] = [(0, 0, {'partner_id': partner_id})]
        # Reflejar ya en el formulario "Disponible en TPV" para un bien nuevo
        # cuando la compañía lo tiene activo (el create() también lo asegura,
        # pero sin esto la casilla se ve desmarcada hasta guardar). Se clava en
        # type='consu' (default del core) para no depender del orden con el
        # default de is_storable que pone wsem_attribute_serie.
        if 'available_in_pos' in fields_list and res.get('type', 'consu') == 'consu' \
                and self.env.company.disponible_tpv_por_defecto:
            # Asignación directa (no setdefault): el core ya devuelve
            # available_in_pos=False en default_get, así que un setdefault no
            # pisaría nada (mismo caso que is_storable).
            res['available_in_pos'] = True
        return res

    @api.model_create_multi
    def create(self, vals_list):
        product_defaults = self.default_get(['is_storable'])
        for vals in vals_list:
            # El default is_storable=True (bien almacenable) lo aplica
            # wsem_attribute_serie.create (que es el create externo por depender
            # de este módulo), así que aquí ya llega en vals y lo leemos para el
            # default de disponibilidad en TPV.
            company = self.env['res.company'].browse(vals.get('company_id')) if vals.get('company_id') else self.env.company
            is_storable = vals.get('is_storable', product_defaults.get('is_storable'))
            if is_storable and company.disponible_tpv_por_defecto:
                vals['available_in_pos'] = True

            if not vals.get('model_code'):
                # Check if ‘default_code’ is provided and is a string of numbers
                default_code = vals.get('default_code')
                if default_code and default_code.isdigit():
                    _logger.info(f'WSEM default code as model {default_code}')
                    vals['model_code'] = default_code

                    # Update the sequence to the maximum between the next value and default_code + 1
                    sequence = self.env['ir.sequence'].search([('code', '=', 'product.template.ref')], limit=1)
                    if sequence:
                        next_number = max(sequence.number_next_actual, int(default_code) + 1)
                        _logger.info(f'WSEM found sequence next {next_number}')
                        sequence.write({'number_next_actual': next_number})
                else:
                    # Otherwise, generate the code using the sequence
                    _logger.info('WSEM generate model code sequence')
                    vals['model_code'] = self.env['ir.sequence'].next_by_code('product.template.ref')
        products = super(ProductTemplate, self).create(vals_list)
        # Precio de venta obligatorio en almacenables SOLO en contexto de compra
        # (junto al resto de reglas de _check_purchase_fields). Detecta un precio
        # olvidado: si 'list_price' no viajó en vals el core aplicó su default
        # (1.0); un valor provisto -- aunque sea 0 o 1 -- se considera editado y
        # pasa (el migrador e importaciones siempre lo envían explícito). Vive en
        # create() (no en la constraint) porque solo aquí se distingue un 1.0
        # tecleado del 1.0 por defecto.
        if self._is_purchase_context(self.env):
            for vals, product in zip(vals_list, products):
                if product.is_storable and 'list_price' not in vals:
                    raise ValidationError(_(
                        "Para los productos almacenables creados desde pedidos de compra debe indicarse el precio de venta."
                    ))
        products._wsem_enforce_web_rules()
        return products

    def _wsem_enforce_web_rules(self):
        # Reglas de talla/color FUERA de compra (venta en web/Shopify), aplicadas
        # al guardar un bien almacenable cuando la compañía tiene activada la
        # opción de talla/color requeridos:
        #   - Falta UNA de las dos (una sí, la otra no) -> error, no deja guardar.
        #   - Faltan las DOS -> se marca 'excluir_de_web' automáticamente (sin
        #     error): el producto no se venderá en la web pero se puede guardar.
        # El aviso previo lo da _onchange_warn_talla_color. La exclusión NO se
        # auto-desmarca al añadir después los atributos (respeta decisiones
        # manuales); el usuario la desmarca si procede.
        if self.env.context.get('wsem_skip_web_rules'):
            return
        if self._is_purchase_context(self.env):
            return
        for product in self:
            if not product.is_storable:
                continue
            company = product.company_id or self.env.company
            if not company.talla_color_requerido_en_compras:
                continue
            missing = product._wsem_missing_attributes(['Talla', 'Color'])
            if len(missing) == 1:
                raise ValidationError(_(
                    "El producto tiene un atributo de 'Talla'/'Color' pero le falta el otro (%s). "
                    "Debe indicar ambos para poder venderse en la web."
                ) % missing[0])
            if len(missing) == 2 and not product.excluir_de_web:
                product.with_context(wsem_skip_web_rules=True).write({'excluir_de_web': True})

    @api.onchange('attribute_line_ids', 'is_storable')
    def _onchange_warn_talla_color(self):
        # Aviso estándar (no bloqueante) al editar en el formulario: si un bien
        # almacenable se queda sin 'Talla' ni 'Color', se informa de que no se
        # venderá en la web. No frena el guardado (eso lo resuelve
        # _wsem_enforce_web_rules marcando 'excluir_de_web').
        if self._is_purchase_context(self.env) or not self.is_storable:
            return
        company = self.company_id or self.env.company
        if not company.talla_color_requerido_en_compras:
            return
        if len(self._wsem_missing_attributes(['Talla', 'Color'])) == 2:
            return {'warning': {
                'title': _("Sin Talla ni Color"),
                'message': _(
                    "Este producto no tiene 'Talla' ni 'Color': no se venderá en la web y, al "
                    "guardar, se marcará como 'Excluido de la web'. Añade ambos atributos si "
                    "quieres sincronizarlo con Shopify."
                ),
            }}

    @api.constrains('is_storable', 'type', 'seller_ids', 'attribute_line_ids')
    def _check_purchase_fields(self):
        # Reglas de compra genéricas (proveedor, precio y, si la compañía lo pide,
        # talla+color). La exigencia de "serie de tallas" NO vive aquí: es
        # específica de wsem_attribute_serie y se queda en ese módulo.
        is_purchase_context = self._is_purchase_context(self.env)
        if not is_purchase_context:
            # Fuera de compra (UI/POS/quick-create) no se aplica ninguna regla.
            return
        for product in self:
            if not product.is_storable:  # v18: is_storable sustituye a type=='product'
                continue
            if not product.seller_ids:
                raise ValidationError(_(
                    "Para los productos almacenables creados desde pedidos de compra debe existir al menos un proveedor."
                ))
            if not any(s.price > 0 for s in product.seller_ids):
                raise ValidationError(_(
                    "Para los productos almacenables creados desde pedidos de compra, al menos un proveedor debe tener precio de compra mayor que cero."
                ))
            company = product.company_id or self.env.company
            if company.talla_color_requerido_en_compras:
                missing = product._wsem_missing_attributes(['Talla', 'Color'])
                if missing:
                    raise ValidationError(_(
                        "Para los productos almacenables creados desde pedidos de compra deben "
                        "indicarse valores para los atributos: %s."
                    ) % ", ".join(missing))

    def write(self, vals):
        should_force_pos = any(field in vals for field in ('is_storable', 'company_id')) and 'available_in_pos' not in vals
        result = super(ProductTemplate, self).write(vals)
        if should_force_pos:
            templates_to_enable = self.filtered(
                lambda template: template.is_storable and (template.company_id or self.env.company).disponible_tpv_por_defecto and not template.available_in_pos
            )
            if templates_to_enable:
                super(ProductTemplate, templates_to_enable).write({'available_in_pos': True})
        # Reevaluar las reglas web de talla/color salvo en la reentrada del propio
        # auto-marcado (wsem_skip_web_rules) y salvo escrituras que no afectan a
        # atributos/almacenable (evita trabajo en cada guardado irrelevante).
        if not self.env.context.get('wsem_skip_web_rules') \
                and any(f in vals for f in ('attribute_line_ids', 'is_storable', 'company_id')):
            self._wsem_enforce_web_rules()
        return result

    def _set_default_code(self):
        """No pisar el default_code de la variante con el vacío de la plantilla.

        En plantillas de una sola variante, el inverse estándar volcaría el
        default_code (vacío) de la plantilla sobre la variante, borrando el
        barcode que se genera en ProductProduct.create.
        """
        templates = self.filtered(
            lambda t: not (
                len(t.product_variant_ids) == 1
                and not t.default_code
                and t.product_variant_ids.default_code
            )
        )
        return super(ProductTemplate, templates)._set_default_code()

    def _set_product_variant_field(self, fname):
        """Override to only set barcode on variant if it doesn't already have one.

        For barcode field: preserves existing variant barcodes (doesn't overwrite).
        For other fields: uses default behavior from base class.
        """
        if fname != 'barcode':
            return super()._set_product_variant_field(fname)

        for template in self:
            variant_count = len(template.product_variant_ids)
            if variant_count == 1:
                if not template.product_variant_ids.barcode:
                    template.product_variant_ids.barcode = template.barcode
                    template.product_variant_ids.default_code = template.barcode
            elif variant_count == 0:
                archived_variants = template.with_context(active_test=False).product_variant_ids
                if len(archived_variants) == 1 and not archived_variants.barcode:
                    archived_variants.barcode = template.barcode
                    archived_variants.default_code = template.barcode


class ProductProduct(models.Model):
    _inherit = 'product.product'

    model_code = fields.Char(
        string="Modelo codigo",
        related="product_tmpl_id.model_code",
        store=True,
        readonly=True,
        index=True,
    )

    def _compute_display_name(self):
        # v18 port of the v16 name_get override: show the variant's attribute
        # values in the displayed name (used on labels) even for single-variant
        # templates. In v17+ name_get was removed; display_name is a computed
        # field, so the logic lives in _compute_display_name.
        super()._compute_display_name()
        for product in self:
            # Strip any variant suffix the core may already have appended.
            base_name = (product.display_name or product.name or "").split(" (")[0]
            attribute_values = product.product_template_attribute_value_ids.mapped('name')
            if attribute_values:
                product.display_name = "%s (%s)" % (base_name, ", ".join(attribute_values))

    def _get_barcode_expression_for_record(self, record):
        company = record.company_id or self.env.company
        expression = company.codigo_de_barras_por_atributos
        if not expression:
            _logger.warning('WPOS No barcode expression for company %s (%s).', company.display_name, company.id)
        return expression

    @api.model_create_multi
    def create(self, vals_list):
        # Create the product variant
        records = super(ProductProduct, self).create(vals_list)
        _logger.info("WSEM records created")
        for record in records:
            expression = self._get_barcode_expression_for_record(record)
            if not expression:
                continue
            barcode = self._generate_barcode(record, expression=expression)
            if barcode:
                _logger.info(f'WSEM Barcode v3 Assigning for the product {record.name}, {barcode}')
                record.write({'default_code': barcode, 'barcode': barcode})
        return records

    def _generate_barcode(self, record, expression=None):
        """Generates a dynamic barcode based on the configured expression."""
        pos_barcode_config_value = expression or self._get_barcode_expression_for_record(record)

        if not pos_barcode_config_value:
            _logger.warning('WPOS No expression found to generate the barcode.')
            return False

        if not record.product_tmpl_id:
            _logger.error('WPOS Attempt to generate a barcode for a product without product_tmpl_id.')
            return False

        segment_strings = re.findall(r'\(([^)]+)\)', pos_barcode_config_value)
        if not segment_strings:
            _logger.warning('WPOS The barcode expression does not contain valid segments.')
            return False

        segments = []
        segment_pattern = re.compile(r'^(?P<attr>[a-zA-Z_]+)(?P<field>\.name)?(?P<length>\{[^}]+\})?$')

        for raw_segment in segment_strings:
            cleaned_segment = raw_segment.strip()
            match = segment_pattern.match(cleaned_segment)
            if not match:
                _logger.warning('WPOS Invalid barcode segment: %s', cleaned_segment)
                continue

            attr = match.group('attr').lower()
            field = 'name' if match.group('field') else 'code'
            length_group = match.group('length')
            min_length = max_length = None
            if length_group:
                length_content = length_group[1:-1]
                if ',' in length_content:
                    try:
                        min_length, max_length = [int(value.strip()) for value in length_content.split(',', 1)]
                    except ValueError:
                        _logger.warning('WPOS Invalid length in segment: %s', cleaned_segment)
                        min_length = max_length = None
                else:
                    try:
                        fixed = int(length_content.strip())
                        min_length = max_length = fixed
                    except ValueError:
                        _logger.warning('WPOS Invalid fixed length in segment: %s', cleaned_segment)

            segments.append({
                'attr': attr,
                'field': field,
                'min_length': min_length,
                'max_length': max_length,
                'raw': cleaned_segment,
            })

        if not segments:
            _logger.warning('WPOS Valid segments for the barcode expression could not be processed.')
            return False

        barcode = ''

        def _truncate_value(value, max_length):
            if max_length is not None and value:
                return value[:max_length]
            return value

        def _get_attribute_value(attribute_name, field_name):
            for attr_value in record.product_template_attribute_value_ids:
                attribute = attr_value.attribute_id.name or ''
                if attribute.lower() == attribute_name:
                    attribute_record = attr_value.product_attribute_value_id
                    return getattr(attribute_record, field_name, '') or ''
            return ''

        for index, segment in enumerate(segments):
            attr = segment['attr']
            field = segment['field']
            min_length = segment['min_length']
            max_length = segment['max_length']

            value = ''
            if attr == 'model':
                if field == 'name':
                    value = record.product_tmpl_id.name or ''
                else:
                    value = record.product_tmpl_id.model_code or ''
                if not value.strip():
                    _logger.warning('WPOS The product model_code is not filled in.')
                    return False            
            else:
                value = _get_attribute_value(attr, field)
                if attr == 'color' and not value.strip():
                    _logger.warning('WPOS The product color_code is not filled in.')
                    return False
                if attr == 'talla' and not value.strip():
                    _logger.warning('WPOS The product size_code is not filled in. It is generated without size')

            value = _truncate_value(value, max_length)

            if min_length and len(value) < min_length:
                _logger.warning('WPOS The value for %s does not meet the minimum length.', segment['raw'])

            barcode += (value or '').lower()

            should_add_separator = False
            if attr == 'color':
                if max_length is not None and min_length is not None:
                    should_add_separator = min_length != max_length
                elif len(value) >= 3:
                    should_add_separator = True

            if should_add_separator and index < len(segments) - 1:
                barcode += '.'

        return barcode
      
class ProductAttributeValue(models.Model):
    _inherit = 'product.attribute.value'

    code = fields.Char(string='Code', help="Codigo", readonly=True, default=lambda self: self._generate_code())
    
    @api.model
    def _generate_code(self):
        return self.env['ir.sequence'].next_by_code('product.attribute.value.code')
