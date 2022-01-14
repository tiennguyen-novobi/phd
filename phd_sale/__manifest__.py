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
    'name': 'PHD: Sale',
    'category': '',
    'version': '1.0',
    'description': """
    """,
    'author': 'Novobi LLC',
    'website': 'http://www.novobi.com',
    'depends': ['sale_management', 'sale_stock', 'sale_partner_deposit', 'phd_tools', 'phd_export_pdf', 'phd_stock', 'sale'],
    'description': """ """,
    'data': [
        'security/phd_sale.xml',
        'security/ir.model.access.csv',
        'security/phd_sale_group_view_only_security.xml',
        'data/phd_sale_order_stage.xml',
        'views/assets.xml',
        'views/phd_sale.xml',
        'views/inherit_product_views.xml',
        'views/product_customerinfo_views.xml',
        'views/phd_disable_create_edit_many2one_views.xml',
        'report/phd_report_templates.xml',
        'report/phd_sale_reports.xml',
    ],
    'demo': [],
    'application': True,
    'license': 'OEEL-1',
}
