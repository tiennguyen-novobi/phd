# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Novobi: Improvements for Accounting in MRP - Subcontracting',
    'summary': 'Novobi: Improvements for Accounting in MRP - Subcontracting',
    'category': 'Accounting',
    "author": "Novobi",
    "website": "https://www.novobi.com/",
    'depends': [
        'stock',
        'account_accountant',
        'mrp',
        'stock_account',
        'mrp_subcontracting_account',
    ],
    'data': [
        'security/ir.model.access.csv',
    ],
    'qweb': [
        'static/src/xml/*.xml',
    ],
    "application": False,
    "installable": True,
}
