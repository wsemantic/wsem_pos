from odoo import models, fields

#     @api.depends('value')
#     def _value_pc(self):
#         for record in self:
#             record.value2 = float(record.value) / 100


class ProductProduct(models.Model):
    _inherit = 'product.product'    
    
    def generate_barcode(self):
        for product in self:
            if not product.barcode:
                template_id = product.product_tmpl_id.id
                product_id = product.id
                
                procode = str(template_id).zfill(5)
                varcode = str(product_id).zfill(5)
                
                barcode = f"{procode}#{varcode}"
                product.barcode = barcode
            
    def create(self, vals):
        variant = super(ProductProduct, self).create(vals)
        variant.generate_barcode()
        return variant