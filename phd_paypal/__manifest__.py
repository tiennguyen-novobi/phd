{
    'name': 'PHD Paypal',
    'version': '1.0',
    'category': 'Payment',
    'author': 'Novobi',
    'website': 'https://www.novobi.com',
    'depends': [
        'phd_request_log'
    ],
    'data': [
        'data/paypal_transaction_cron.xml',
        'security/ir.model.access.csv',

        'views/account_res_config_setting_form_views.xml',
        'views/paypal_transaction_views.xml',
        'views/request_log_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
    'license': 'OPL-1',
}
