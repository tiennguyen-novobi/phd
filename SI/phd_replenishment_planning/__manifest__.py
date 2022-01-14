# Copyright © 2021 Novobi, LLC
# See LICENSE file for full copyright and licensing details.

{
    'name': 'PHD: Replenishment Planning',
    'summary': 'PHD: Replenishment Planning',
    "author": "Novobi",
    "website": "https://www.novobi.com/",
    'depends': [
        'phd_stock_status_report', 'me_replenishment_planning'
    ],
    "data": [

        'views/assets.xml',
        'views/inventory_status_report_views.xml',
        'views/product_views.xml',
        "views/replenishment_report_views.xml",
        'views/res_config_setting_views.xml',

        "report/replenishment_planning_report.xml",

        'wizard/detail_transaction.xml'
    ],
    "qweb": [
        'static/src/xml/*.xml',
    ],
    "application": False,
    "installable": True,
}
