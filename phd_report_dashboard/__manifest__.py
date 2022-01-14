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
    'name': 'PHD: Report Dashboard',
    'category': '',
    'version': '1.0',
    'description': """
    """,
    'author': 'Novobi LLC',
    'website': 'http://www.novobi.com',
    'depends': ['account_dashboard', 'l10n_us_accounting', 'l10n_custom_dashboard', 'phd_sale', 'phd_purchase', 'mrp'],
    'description': """ """,
    'data': [
        'views/assets.xml',
        'security/ir.model.access.csv',
        'data/phd_report_dashboard_data.xml',
        'views/phd_report_dashboard_views.xml',
    ],
    'qweb': ['static/src/xml/*.xml'],
    'demo': [],
    'application': True,
    'license': 'OEEL-1',
}