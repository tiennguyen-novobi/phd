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
    'name': 'PHD: Purchase',
    'category': '',
    'version': '1.0',
    'description': """
    """,
    'author': 'Novobi LLC',
    'website': 'http://www.novobi.com',
    'depends': ['phd_tools', 'purchase_stock', 'phd_export_pdf', 'phd_stock', 'phd_inventory', 'product'],
    'description': """ """,
    'data': [
        'security/phd_purchase.xml',
        'security/phd_purchase_group_view_only_security.xml',
        'security/ir.model.access.csv',
        'data/phd_purchase_order_stage.xml',
        'reports/inherit_report_purchase_order.xml',
        'views/assets.xml',
        'views/phd_res_partner.xml',
        'views/phd_account_move_views.xml',
        'views/phd_purchase.xml',
        'views/phd_disable_create_edit_many2one_views.xml',
        'reports/report_templates.xml',
        'reports/reports.xml',
    ],
    'qweb': [

    ],
    'demo': [],
    'application': True,
    'license': 'OEEL-1',
}