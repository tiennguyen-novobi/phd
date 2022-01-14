#coding: utf-8

from odoo import api, models


class product_template(models.Model):
    """
    Overwrite to force minimum stock creation based on category.
    """
    _inherit = "product.template"

    @api.multi
    def write(self, values):
        """
        Overwrite to prepare minimum stock rules based on categories
        The point to have it here (not in variants), since both fields are template fields not variant fields

        Methods:
         * _update_min_stock_rules_per_category of product.product
        """
        if values.get("categ_id") or values.get("type") or values.get("active"):
            extra_categ = self.mapped("categ_id")
        res = super(product_template, self).write(values)
        if values.get("categ_id") or values.get("type") or values.get("active"):
            products = self.mapped("product_variant_ids")
            products._update_min_stock_rules_per_category(extra_categ=extra_categ)
        return res
