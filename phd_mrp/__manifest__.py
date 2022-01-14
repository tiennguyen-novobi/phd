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
    'name': 'PHD: Manufacturing',
    'category': '',
    'version': '1.0',
    'description': """
    """,
    'author': 'Novobi LLC',
    'website': 'http://www.novobi.com',
    'depends': ['phd_purchase',
                'mrp_subcontracting',
                'mrp_account',
                'phd_tools',
                'phd_export_pdf',
                'phd_inventory'],
    'description': """ """,
    'data': [
        'security/phd_mrp.xml',
        'security/phd_mrp_group_view_only_security.xml',
        'security/ir.model.access.csv',
        'data/phd_mrp_order_stage.xml',
        'data/cron.xml',
        'views/assets.xml',
        'views/phd_mrp.xml',
        'views/phd_mrp_subcontracting.xml',
        'views/inherit_res_partner_views.xml',
        'views/inherit_product_views.xml',
        'views/inherit_purchase_order_views.xml',
        'views/inherit_mrp_production_views.xml',
        'views/inherit_res_config_settings_views.xml',
        'views/phd_disable_create_edit_many2one_views.xml',
        'wizard/phd_mrp_product_produce_views.xml',
        'wizard/phd_mrp_add_qty_to_produce.xml',
        'wizard/confirm_purchase_views.xml',
        'wizard/phd_produce_confirmation_views.xml',
        'reports/inherit_cost_structure_report.xml',
        'reports/raw_material_consumption_report_views.xml',
        'views/inherit_mrp_bom_views.xml',
    ],
    'qweb': [
        "static/src/xml/phd_mrp_order_calendar.xml",
    ],
    'demo': [],
    'application': True,
    'license': 'OEEL-1',
}
