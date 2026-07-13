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

    'category': 'Uncategorized',
    'version': '18.0.0.1',

    'depends': ['sale', 'point_of_sale'],

    'data': [
        'views/views.xml',
    ],
    'assets': {
        'point_of_sale._assets_pos': [
            'wsem_pos/static/src/app/barcode/barcode_reader_patch.js',
        ],
    },
    "license": "AGPL-3",
}
