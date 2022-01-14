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
    'name': 'PHD: Marketing',
    'category': '',
    'version': '1.0',
    'description': """
    """,
    'author': 'Novobi LLC',
    'website': 'http://www.novobi.com',
    'depends': ['product'],
    'description': """ """,
    'data': [
        'security/phd_marketing.xml',
        'security/ir.model.access.csv',
        'data/mko_stage_data.xml',
        'data/ir_sequence_data.xml',
        'data/email_template.xml',
        'views/ir_attachment_view.xml',
        'views/phd_mko_templates.xml',
        'views/phd_mko_views.xml',
        'views/phd_mko_report_views.xml',
        'views/phd_disable_create_edit_many2one_views.xml',
    ],
    'qweb': [
        "static/src/xml/phd_calendar_template.xml",
        "static/src/xml/phd_filter_date_ranges_template.xml",
    ],
    'demo': [],
    'application': True,
    'license': 'OEEL-1',
}