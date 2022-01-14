# coding: utf-8
# Part of CAPTIVEA. Odoo 12 EE.

from odoo import fields, models, api


class MainProduct(models.Model):
    """Manage 'main.product' model."""
    _name = "main.product"

    name = fields.Char("Name", required=True)
    deal_stage_ids = fields.Many2many(
        'sale.order.stage',  'rel_sale_stage_main_product', 'main_product_id', 'stage_id', string='Deal Stage')
    master = fields.Boolean("Master")
    convoso_revenue_field_name = fields.Char("Convoso Revenu Field Name")
    convoso_key = fields.Char("Convoso Key")
    product_id = fields.Many2one('product.product',  string='Product')
