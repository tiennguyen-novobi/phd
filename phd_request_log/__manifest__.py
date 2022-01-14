{
    'name': 'PHD Request Log',
    'version': '1.0',
    'category': 'Payment',
    'author': 'Novobi',
    'website': 'https://www.novobi.com',
    'depends': [
        'account'
    ],
    'data': [
        'security/ir.model.access.csv',

        'views/request_log_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': True,
    'license': 'OPL-1',
}
