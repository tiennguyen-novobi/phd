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
    'name': 'PHD: Contact',
    'category': '',
    'version': '1.0',
    'description': """
    """,
    'author': 'Novobi LLC',
    'website': 'http://www.novobi.com',
    'depends': ['contacts', 'l10n_us_accounting'],
    'description': """ """,
    'data': [
        'security/ir.model.access.csv',

        'data/address_format.xml',

        'views/inherit_res_partner_views.xml',
    ],
    'qweb': [
    ],
    'demo': [],
    'application': False,
    'license': 'OEEL-1',
}