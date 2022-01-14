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
    'name': 'PHD: SPS Commerce Intergration',
    'category': '',
    'version': '1.0',
    'description': """
    """,
    'author': 'Novobi LLC',
    'website': 'http://www.novobi.com',
    'depends': ['base',
                'base_setup',
                'phd_sale'],
    'description': """
        Using Paramiko Lib 2.7.2
     """,
    'data': [
        'security/ir.model.access.csv',

        'data/ir_cron_data.xml',
        'data/mail_activity_data.xml',
        'data/edi_vendor_line_status_code.xml',

        'views/phd_sftp_res_config.xml',
        'views/phd_sps_commerce_files.xml',
        'views/inherit_res_partner_views.xml',
        'views/inherit_sale_order_views.xml',
        'views/edi_transaction_views.xml',
        'views/edi_transaction_setting_views.xml',

        'wizard/reject_edi_860.xml'
    ],
    'demo': [],
    'application': True,
    'license': 'OEEL-1',
}
