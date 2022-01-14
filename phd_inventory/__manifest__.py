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
    'name': 'PHD: Inventory',
    'category': '',
    'version': '1.0',
    'description': """
    """,
    'author': 'Novobi LLC',
    'website': 'http://www.novobi.com',
    'depends': ['product', 'stock', 'stock_enterprise', 'stock_account', 'product_expiry', 'phd_tools', 'stock_landed_costs'],
    'description': """ """,
    'data': [
        'security/phd_inventory.xml',
        'security/phd_inventory_group_view_only_security.xml',
        'security/ir.model.access.csv',

        'wizard/phd_action_update_date_views.xml',
        'views/assets.xml',

        'views/inherit_res_partner_views.xml',
        'views/inherit_product_views.xml',
        'views/inherit_stock_picking_views.xml',
        'views/inherit_stock_move_line_views.xml',
        'views/inherit_stock_picking_type_views.xml',
        'views/phd_disable_create_edit_many2one_views.xml',
    ],
    'qweb': [
    ],
    'demo': [],
    'application': False,
    'license': 'OEEL-1',
}