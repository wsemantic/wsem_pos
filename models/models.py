from odoo import api, fields, models, _
import logging

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
    model_code = fields.Char(string='Codigo', help="Model Codigo", readonly=True)
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
        """
        Genera un código de barras en el formato PROCODE-COLORCODE-SIZENAME.
        No hace nada si alguna de las cadenas (producto, color, talla) no está rellena o está vacía.
        """
        # Asegurarse de que el record contiene un 'product_tmpl_id'
        if not record.product_tmpl_id:
            _logger.error('WPOS Intento de generar un barcode para un producto sin product_tmpl_id.')
            return False

        # Obtener el model_code del producto template
        model_code = record.product_tmpl_id.model_code or ''
        if not model_code.strip():
            _logger.warning('WPOS El model_code del producto no está relleno.')
            return False

        # Obtener el code del color
        color_code = ''
        for attr_value in record.product_template_attribute_value_ids:
            if attr_value.attribute_id.name.lower() == 'color':
                color_code = attr_value.product_attribute_value_id.code or ''
                break
        if not color_code.strip():
            _logger.warning('WPOS El color_code del producto no está relleno.')
            return False

        # Obtener el name de la talla
        size_code = ''
        for attr_value in record.product_template_attribute_value_ids:
            if attr_value.attribute_id.name.lower() == 'talla':
                size_code = attr_value.product_attribute_value_id.code or ''
                break
        if not size_code.strip():
            _logger.warning('WPOS El size_code del producto no está relleno. Se genera sin talla')

        # Generar el código de barras en el formato esperado
        if len(color_code) >= 3:
            barcode = f'{model_code}{color_code}.{size_code}'.lower()
        else:
            barcode = f'{model_code}{color_code}{size_code}'.lower()

        return barcode
      
        
'''class PosOrderLine(models.Model):
    _inherit = 'pos.order.line'

    def get_loyalty_card(self):
        self.ensure_one()
        LoyaltyCard = self.env['loyalty.card']
        loyalty_card = LoyaltyCard.search([('order_id', '=', self.order_id.id)], limit=1)
        return loyalty_card'''
