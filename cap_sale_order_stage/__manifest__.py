# coding: utf-8
# Part of CAPTIVEA. Odoo 12 EE.

{
    'name': "cap_sale_order_stage",
    'version': "12.0.1.0.0",
    'author': "captivea-jpa",
    'summary': "Manage stages for 'sale.order', 'main product' and 'sale order' models.",
    'depends': ['sale', 'sale_management'],
    'data': [#"data/ir_ui_menu.xml",
            "security/cap_sale_order_stage.xml",
            "views/cap_sale_stage_view.xml",
	        "views/main_product_view.xml",
            "views/sale_order_view.xml",
             ],
    'installable': True
}
