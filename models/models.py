from odoo import api, fields, models, _
import logging

_logger = logging.getLogger(__name__)

class ProductProduct(models.Model):
    _inherit = 'product.product'

    @api.model
    def create(self, vals):
        # Crear la variante del producto
        record = super(ProductProduct, self).create(vals)
        _logger.info("WSEM creado record")
        # Generar y asignar el barcode
        barcode = self._generate_barcode(record)
        record.write({'barcode': barcode})

        # Log de información
        _logger.info(f'WSEM Barcode generado para el producto {record.name}, {barcode}')

        return record

    def _generate_barcode(self, record):
        """
        Genera un código de barras en el formato PROCODE VARCODE
        """
        # Asegurarse de que el record contiene un 'product_tmpl_id' y un 'id'
        if not record.product_tmpl_id or not record.id:
            _logger.error('Intento de generar un barcode para un producto sin product_tmpl_id o id.')
            return False

        # Generar PROCODE y VARCODE
        _logger.info("WSEM Generando Barcode")
        procode = str(record.product_tmpl_id.id).zfill(5)
        varcode = str(record.id).zfill(5)

        # Formato final del barcode
        barcode = '{} {}'.format(procode, varcode)

        return barcode
