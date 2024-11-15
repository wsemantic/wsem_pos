from odoo import api, fields, models, _
import logging

_logger = logging.getLogger(__name__)

class ProductTemplate(models.Model):
    _inherit = 'product.template'    
    model_code = fields.Char(string='Codigo', help="Model Codigo", readonly=True)
    
    @api.model
    def create(self, vals):
        if not vals.get('model_code'):
            vals['model_code'] = self.env['ir.sequence'].next_by_code('product.template.ref')
        return super(ProductTemplate, self).create(vals)
        
class ProductProduct(models.Model):
    _inherit = 'product.product'

    @api.model
    def create(self, vals):
        # Crear la variante del producto
        record = super(ProductProduct, self).create(vals)
        _logger.info("WSEM creado record")
        # Generar y asignar el barcode
        barcode = self._generate_barcode(record)
        if barcode:
            record.write({'barcode': barcode})
            # Log de información
            _logger.info(f'WSEM Barcode v3 generado para el producto {record.name}, {barcode}')
        else:
            return False

        return record
        
        
    def _generate_barcode(self, record):
        """
        Genera un código de barras en el formato PROCODE-COLORCODE-SIZENAME.
        No hace nada si alguna de las cadenas (producto, color, talla) no está rellena o está vacía.
        """
        # Asegurarse de que el record contiene un 'product_tmpl_id'
        if not record.product_tmpl_id:
            _logger.error('Intento de generar un barcode para un producto sin product_tmpl_id.')
            return False

        # Obtener el model_code del producto template
        model_code = record.product_tmpl_id.model_code or ''
        if not model_code.strip():
            _logger.warning('El model_code del producto no está relleno.')
            return False

        # Obtener el code del color
        color_code = ''
        for attr_value in record.product_template_attribute_value_ids:
            if attr_value.attribute_id.name.lower() == 'color':
                color_code = attr_value.product_attribute_value_id.code or ''
                break
        if not color_code.strip():
            _logger.warning('El color_code del producto no está relleno.')
            return False

        # Obtener el name de la talla
        size_name = ''
        for attr_value in record.product_template_attribute_value_ids:
            if attr_value.attribute_id.name.lower() == 'talla':
                size_name = attr_value.product_attribute_value_id.name or ''
                break
        if not size_name.strip():
            _logger.warning('El size_name del producto no está relleno.')
            return False

        # Generar el código de barras en el formato esperado
        barcode = f'{model_code}{color_code}{size_name}'
        return barcode
      
        
'''class PosOrderLine(models.Model):
    _inherit = 'pos.order.line'

    def get_loyalty_card(self):
        self.ensure_one()
        LoyaltyCard = self.env['loyalty.card']
        loyalty_card = LoyaltyCard.search([('order_id', '=', self.order_id.id)], limit=1)
        return loyalty_card'''
