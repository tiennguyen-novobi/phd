#coding: utf-8

from odoo import api, models


class product_product(models.Model):
    """
    Overwrite to force minimum stock creation based on category.
    """
    _inherit = "product.product"

    @api.model_create_multi
    def create(self, vals_list):
        """
        Overwrite to prepare minimum stock rules based on categories

        Methods:
         * _update_min_stock_rules_per_category
        """
        res = super(product_product, self).create(vals_list)
        res._update_min_stock_rules_per_category()
        return res

    @api.multi
    def _update_min_stock_rules_per_category(self, extra_categ=None):
        """
        The method to update all rules of impacted categories

        Args:
         * extra_categ - product.category recordset. The goal: used to update previous categories (to remove outdated
           rules)

        Methods:
         * _update_product_rules of product.categ.order.point
        """
        self._cr.commit()
        categ_ids = self.mapped("categ_id")
        if extra_categ:
            categ_ids += extra_categ
        all_rules = self.env["product.categ.order.point"].sudo().search([("category_id", "in", categ_ids.ids)])
        all_rules._update_product_rules()
