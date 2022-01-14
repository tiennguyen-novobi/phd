# Copyright © 2021 Novobi, LLC
# See LICENSE file for full copyright and licensing details.

{
    'name': 'PHD: Demand Forecast',
    'summary': 'PHD: Demand Forecast',
    "author": "Novobi",
    "website": "https://www.novobi.com/",
    'depends': [
        'stock',
        'phd_inventory'
    ],
    "data": [
        'security/ir.model.access.csv',
        
        'data/ir_config_parameter_data.xml',
        'data/ir_cron.xml',
        'data/import_template.xml',
        
        'views/assets.xml',
        'views/demand_forecast_item_views.xml',
        'views/product_product_views.xml',
    ],
    "qweb": [
        'static/src/xml/*.xml',
    ],
    "application": False,
    "installable": True,
    "uninstall_hook": "uninstall_hook",
}
