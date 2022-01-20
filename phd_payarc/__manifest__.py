{
    'name': 'PHD PayArc',
    'version': '1.0',
    'category': 'Payment',
    'author': 'Novobi',
    'website': 'https://www.novobi.com',
    'depends': [
        'phd_request_log'
    ],
    'data': [
        'data/payarc_batch_report_cron.xml',

        'security/ir.model.access.csv',

        'views/account_journal_views.xml',
        'views/payarc_batch_report_views.xml',
        'views/authorize_transaction_views.xml',
        'views/released_fund_views.xml',
        'views/settlement_report_views.xml',
        'views/request_log_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
    'license': 'OPL-1',
}
