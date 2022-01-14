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
    'name': 'PHD: Account Reports',
    'category': '',
    'version': '1.0',
    'description': """
    """,
    'author': 'Novobi LLC',
    'website': 'http://www.novobi.com',
    'depends': ['account_reports','sale_stock', 'phd_account'],
    'description': """ """,
    'data': [
        'security/ir.model.access.csv',
        'data/general_ledger_data.xml',
        'views/assets.xml',
        'views/inherit_account_report_views.xml',
        'views/inherit_res_config_settings_views.xml'
    ],
    'qweb': [
    ],
    'demo': [],
    'application': False,
    'license': 'OEEL-1',
}