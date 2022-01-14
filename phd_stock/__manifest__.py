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
    'name': 'PHD: Stock',
    'category': '',
    'version': '1.0',
    'description': """
    """,
    'author': 'Novobi LLC',
    'website': 'http://www.novobi.com',
    'depends': ['account_reports',
                'mrp_subcontracting',
                'purchase_stock',
                'phd_contact',
                'sale_stock',
                'product_expiry',
                'phd_tools',
                'stock_account'],
    'data': [
        'security/ir.model.access.csv',

        'views/assets.xml',

        'views/phd_stock_move_line_views.xml',

        'views/phd_stock_picking_views.xml',

        'views/phd_mrp.xml',

        'views/phd_stock_location_views.xml',

        'views/phd_stock_valuation_layer_views.xml',

        'data/forecasted_quantity_report_templates.xml',

        'report/forecasted_quantity_report_view.xml',

        'report/report_templates.xml',

        'report/reports.xml',

        'wizard/filter_location_views.xml',

        'wizard/stock_quantity_history.xml',

        'views/product_views.xml',
    ],
    'qweb': [

    ],
    'demo': [],
    'application': True,
    'license': 'OEEL-1',
}