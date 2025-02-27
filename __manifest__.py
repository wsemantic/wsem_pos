# -*- coding: utf-8 -*-
{
    'name': "wsem_pos",

    'summary': """
        Modelo de producto y codigo de barras automatico""",

    'description': """
        Añade modelo de producto y genera codigo de barras automatico en base variantes
    """,

    'author': "Semantic Web Software SL",
    'website': "https://wsemantic.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/16.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '16.0.0.2',

    # any module necessary for this one to work correctly
    'depends': ['sale'], 

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        'views/views.xml',
        'views/templates.xml'
    ],
    'assets': {
        'point_of_sale.assets': [
            'wsem_pos/static/src/js/pos_barcode_case_insensitive.js',
        ],
    },   
    # only loaded in demonstration mode
    'demo': [
    ],
    "license": "AGPL-3",
}
