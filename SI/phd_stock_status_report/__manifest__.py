# Copyright © 2021 Novobi, LLC
# See LICENSE file for full copyright and licensing details.

{
    'name': 'PHD: Stock Status Report',
    'summary': 'PHD: Stock Status Report',
    "author": "Novobi",
    "website": "https://www.novobi.com/",
    'depends': [
        'phd_demand_forecast'
    ],
    "data": [
        'security/ir.model.access.csv',

        'data/ir_cron.xml',

        'views/assets.xml',
        'views/res_config_settings_views.xml',
        'views/product_product_views.xml',
        'views/inventory_status_report_views.xml',
    ],
    "qweb": [
        'static/src/xml/*.xml',
    ],
    "application": False,
    "installable": True,
    "post_init_hook": '_init_inventory_status_report_line',
}
