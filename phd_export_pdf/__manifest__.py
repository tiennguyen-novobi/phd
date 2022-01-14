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
    'name': 'PHD: Export PDF',
    'category': '',
    'version': '1.0',
    'description': """
    """,
    'author': 'Novobi LLC',
    'website': 'http://www.novobi.com',
    'depends': ['web','sale'],
    'description': """ """,
    'data': [
        'views/assets.xml',
        'report/report_paper_format.xml',
        'templates/templates.xml',
    ],
    'qweb': [
        "static/src/xml/*.xml",
    ],
    'demo': [],
    'application': True,
    'license': 'OEEL-1',
}