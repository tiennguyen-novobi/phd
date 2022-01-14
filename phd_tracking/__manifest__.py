# -*- coding: utf-8 -*-
##############################################################################
#
#    Open Source Management Solution
#    Copyright (C) 2015 to 2020 (<http://tiny.be>).
#
#    Copyright (C) 2016 Novobi LLC (<http://novobi.com>)
#
##############################################################################
{
    'name': 'PHD: Tracking',
    'category': '',
    'version': '1.0',
    'description': """
    """,
    'author': 'Novobi LLC',
    'website': 'http://www.novobi.com',
    'depends': ['phd_purchase', 'phd_sale', 'phd_mrp'],
    'description': """ """,
    'data': [
        'security/ir.model.access.csv',
        'wizard/delay_tracker_creation_view.xml',
        'views/assets.xml',
        'views/inherit_sale_order_views.xml',
        'views/inherit_purchase_order_views.xml',
        'views/inherit_mrp_production_views.xml',
    ],
    'qweb': [
    ],
    'demo': [],
    'application': False,
    'license': 'OEEL-1',
}