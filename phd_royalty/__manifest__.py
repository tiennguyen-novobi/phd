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
    'name': 'PHD: Royalty',
    'category': '',
    'version': '1.0',
    'description': """
    """,
    'author': 'Novobi LLC',
    'website': 'http://www.novobi.com',
    'depends': ['stock_account', 'phd_mrp'],
    'description': """ """,
    'data': [
        'security/ir.model.access.csv',

        'data/royalty_cron.xml',

        'views/royalty_tracking_views.xml'
    ],
    'demo': [],
    'application': True,
    'license': 'OEEL-1',
}
