# Copyright © 2021 Novobi, LLC
# See LICENSE file for full copyright and licensing details.

{
    "name": "ME: Replenishment Planning",
    "summary": "ME: Replenishment Planning",
    "version": "14.0.1.0.0",
    "category": "Manufacturing",
    "website": "https://novobi.com",
    "author": "Novobi, LLC",
    "license": "OPL-1",
    "depends": [
        "base", "mrp", "stock", "purchase", "purchase_stock",
    ],
    "excludes": [],
    "data": [
        # ============================== DATA =================================
        "data/me_replenishment_planning_data.xml",

        # ============================== MENU =================================

        # ============================== VIEWS ================================
        "views/assets.xml",
        "views/product_product_views.xml",
        "views/product_template_views.xml",
        "views/res_config_settings_views.xml",
        "views/replenishment_history_views.xml",
        "views/replenishment_planning_report_views.xml",

        # ============================== SECURITY =============================
        "security/ir.model.access.csv",

        # ============================== TEMPLATES =============================

        # ============================== REPORT =============================
        "report/replenishment_planning_report.xml",

        # ============================== WIZARDS =============================
        'wizard/detail_transaction.xml',

    ],
    "demo": [],
    "qweb": [
        "static/src/xml/*.xml",
    ],
    "application": False,
    "installable": True,
}
