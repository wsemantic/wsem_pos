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

    
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
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
                    _logger.info(f'WSEM generate model code sequence')
                    vals['model_code'] = self.env['ir.sequence'].next_by_code('product.template.ref')
        return super(ProductTemplate, self).create(vals_list)

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
            elif variant_count == 0:
                archived_variants = template.with_context(active_test=False).product_variant_ids
                if len(archived_variants) == 1 and not archived_variants.barcode:
                    archived_variants.barcode = template.barcode

        
class ProductProduct(models.Model):
    _inherit = 'product.product'
                    
    model_code = fields.Char(
        string="Modelo codigo",
        related="product_tmpl_id.model_code",
        store=True,
        readonly=True,
        index=True,
    )
    
    @api.model_create_multi
    def create(self, vals_list):
        # Create the product variant
        records = super(ProductProduct, self).create(vals_list)
        _logger.info("WSEM records created")
        # Generate and assign the barcode
        pos_barcode_config_value = self.env['ir.config_parameter'].sudo().get_param('wsem_pos.codigo_de_barras_por_atributos')
        _logger.info(f'WPOS barcode expression by attributes {pos_barcode_config_value}')
        # Check if the configuration value is NOT null or an empty string
        if pos_barcode_config_value:
            for record in records:
                barcode = self._generate_barcode(record)
                if barcode:
                    _logger.info(f'WSEM Barcode v3 Assigning for the product {record.name}, {barcode}')
                    record.write({'default_code': barcode, 'barcode': barcode})
                    # Information log
        return records
        
    def _generate_barcode(self, record):
        """Generates a dynamic barcode based on the configured expression."""
        pos_barcode_config_value = self.env['ir.config_parameter'].sudo().get_param('wsem_pos.codigo_de_barras_por_atributos')
        
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

'''class PosOrderLine(models.Model):
    _inherit = 'pos.order.line'

    def get_loyalty_card(self):
        self.ensure_one()
        LoyaltyCard = self.env['loyalty.card']
        loyalty_card = LoyaltyCard.search([('order_id', '=', self.order_id.id)], limit=1)
        return loyalty_card'''
