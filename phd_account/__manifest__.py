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
    'name': 'PHD: Account',
    'category': '',
    'version': '1.0',
    'description': """
    """,
    'author': 'Novobi LLC',
    'website': 'http://www.novobi.com',
    'depends': ['account_accountant', 'phd_sale', 'phd_sps_integration', 'mrp', 'stock', 'l10n_us_accounting','account_batch_payment'],
    'description': """ """,
    'data': [
        'security/phd_account.xml',
        'security/phd_account_group_view_only_security.xml',
        'security/ir.model.access.csv',
        'wizard/warning_tags_analytic.xml',
        'data/account_type.xml',
        'views/res_partner_category_views.xml',
        'views/inherit_account_move_views.xml',
        'views/phd_disable_create_edit_many2one_views.xml',
        'views/inherit_customer_vendor_deposit_payment.xml',
        'views/credit_card_charge_refund_views.xml',
        'reports/account_invoice_detail_report_templates.xml',
        'reports/account_invoice_detail_report_views.xml',
        'reports/inherit_invoice_report_templates.xml',
    ],
    'qweb': [
    ],
    'demo': [],
    'application': False,
    'license': 'OEEL-1',
}