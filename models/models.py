from odoo import api, fields, models, _
import logging
import re

_logger = logging.getLogger(__name__)

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    codigo_de_barras_por_atributos = fields.Char(
        string="Código de Barras por Atributos",
        config_parameter='wsem_pos.codigo_de_barras_por_atributos',
        help="Define la lógica o texto relacionado con la generación de códigos de barras por atributos en el PoS."
    )
    
class ProductTemplate(models.Model):
    _inherit = 'product.template'    
    model_code = fields.Char(string='Codigo', help="Model Codigo")
    """
    detailed_type = fields.Selection(
        selection=[
            ('product', 'Almacenable'),
            ('consu', 'Consumible'),
            ('service', 'Servicio'),
        ],
        string="Tipo de Producto",
        default='product',  # Asegúrate de que el predeterminado también esté configurado
        required=True
    )
    """
    
    @api.model
    def create(self, vals):
        if not vals.get('model_code'):
            # Verificar si 'default_code' está informado y es una cadena de números
            default_code = vals.get('default_code')
            if default_code and default_code.isdigit():
                _logger.info(f'WSEM default code como model {default_code}')
                vals['model_code'] = default_code
                
                # Actualizar la secuencia al máximo entre el siguiente valor y default_code + 1
                sequence = self.env['ir.sequence'].search([('code', '=', 'product.template.ref')], limit=1)
                if sequence:                    
                    next_number = max(sequence.number_next_actual, int(default_code) + 1)
                    _logger.info(f'WSEM encontrada secuencia next {next_number}')
                    sequence.write({'number_next_actual': next_number})
            else:
                # Si no, generar el código usando la secuencia
                _logger.info(f'WSEM generar model code secuencia')
                vals['model_code'] = self.env['ir.sequence'].next_by_code('product.template.ref')
        return super(ProductTemplate, self).create(vals)
        
    def _set_barcode(self):
        variant_count = len(self.product_variant_ids)
        if variant_count == 1:
            # Solo asignar el barcode si la variante no tiene uno
            if not self.product_variant_ids.barcode:
                self.product_variant_ids.barcode = self.barcode
        elif variant_count == 0:
            archived_variants = self.with_context(active_test=False).product_variant_ids
            if len(archived_variants) == 1:
                if not archived_variants.barcode:
                    default_code=self.barcode
                    archived_variants.barcode = self.barcode
        
class ProductProduct(models.Model):
    _inherit = 'product.product'
                    
    @api.model
    def create(self, vals):
        # Crear la variante del producto
        record = super(ProductProduct, self).create(vals)
        _logger.info("WSEM creado record")
        # Generar y asignar el barcode
        pos_barcode_config_value = self.env['ir.config_parameter'].sudo().get_param('wsem_pos.codigo_de_barras_por_atributos')
        _logger.info(f'WPOS expresion codigo barras por atributos {pos_barcode_config_value}')
        # Verificar si el valor de la configuración NO es nulo ni cadena vacía
        if pos_barcode_config_value:
            
            barcode = self._generate_barcode(record)
            if barcode:
                _logger.info(f'WSEM Barcode v3 Asignando para el producto {record.name}, {barcode}')
                record.write({'default_code': barcode})
                record.write({'barcode': barcode})
                # Log de información
 

        return record
        
        
    def _generate_barcode(self, record):
        """Genera un código de barras dinámico en base a la expresión configurada."""
        pos_barcode_config_value = self.env['ir.config_parameter'].sudo().get_param('wsem_pos.codigo_de_barras_por_atributos')

        if not pos_barcode_config_value:
            _logger.warning('WPOS No se encontró expresión para generar el código de barras.')
            return False

        if not record.product_tmpl_id:
            _logger.error('WPOS Intento de generar un barcode para un producto sin product_tmpl_id.')
            return False

        segment_strings = re.findall(r'\(([^)]+)\)', pos_barcode_config_value)
        if not segment_strings:
            _logger.warning('WPOS La expresión de código de barras no contiene segmentos válidos.')
            return False

        segments = []
        segment_pattern = re.compile(r'^(?P<attr>[a-zA-Z_]+)(?P<field>\.name)?(?P<length>\{[^}]+\})?$')

        for raw_segment in segment_strings:
            cleaned_segment = raw_segment.strip()
            match = segment_pattern.match(cleaned_segment)
            if not match:
                _logger.warning('WPOS Segmento de código de barras inválido: %s', cleaned_segment)
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
                        _logger.warning('WPOS Longitud inválida en segmento: %s', cleaned_segment)
                        min_length = max_length = None
                else:
                    try:
                        fixed = int(length_content.strip())
                        min_length = max_length = fixed
                    except ValueError:
                        _logger.warning('WPOS Longitud fija inválida en segmento: %s', cleaned_segment)

            segments.append({
                'attr': attr,
                'field': field,
                'min_length': min_length,
                'max_length': max_length,
                'raw': cleaned_segment,
            })

        if not segments:
            _logger.warning('WPOS No se pudieron procesar segmentos válidos para la expresión del código de barras.')
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
                    _logger.warning('WPOS El model_code del producto no está relleno.')
                    return False
            else:
                value = _get_attribute_value(attr, field)
                if attr == 'color' and not value.strip():
                    _logger.warning('WPOS El color_code del producto no está relleno.')
                    return False
                if attr == 'talla' and not value.strip():
                    _logger.warning('WPOS El size_code del producto no está relleno. Se genera sin talla')

            value = _truncate_value(value, max_length)

            if min_length and len(value) < min_length:
                _logger.warning('WPOS El valor para %s no cumple la longitud mínima.', segment['raw'])

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
        
'''class PosOrderLine(models.Model):
    _inherit = 'pos.order.line'

    def get_loyalty_card(self):
        self.ensure_one()
        LoyaltyCard = self.env['loyalty.card']
        loyalty_card = LoyaltyCard.search([('order_id', '=', self.order_id.id)], limit=1)
        return loyalty_card'''
