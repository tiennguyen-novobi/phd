#coding: utf-8

from odoo import api, fields, models


class stock_warehouse_orderpoint(models.Model):
    """
    Overwrite to link product and category ordering rules

    To-do:
     * search /grpup by category rule
     * search independent rules
    """
    _inherit = "stock.warehouse.orderpoint"

    @api.multi
    def _inverse_category_rule_id(self):
        """
        Inverse method for category_rule_id
        If category rule is changed manually (not via SQL), its factors should update the current rule

        Methods:
         * _prepare_vals_for_rule of product.categ.order.point
        """
        for orderpoint in self:
            if orderpoint.category_rule_id:
                new_vals = orderpoint.category_rule_id._prepare_vals_for_rule()
                if new_vals.get("category_rule_id"):
                    new_vals.pop("category_rule_id")
                orderpoint.write(new_vals)

    @api.multi
    def _inverse_active(self):
        """
        Inverse method for active to re-calculate related category rule

        Methods:
         * _update_min_stock_rules_per_category of product.product
        """
        products = self.mapped("product_id")
        products._update_min_stock_rules_per_category()

    category_rule_id = fields.Many2one(
        "product.categ.order.point",
        string="Rule per Category",
        help="Leave it empty to set the rule for this product & location always manually",
        inverse=_inverse_category_rule_id,
    )
    product_category_id = fields.Many2one(
        related="product_id.categ_id",
    )
    active = fields.Boolean(inverse=_inverse_active)

    @api.multi
    def unlink(self):
        """
        Re-write to trigger categories rules re-calculation

        Methods:
         * _update_min_stock_rules_per_category of product.product
        """
        products = self.mapped("product_id")
        res = super(stock_warehouse_orderpoint, self).unlink()
        products._update_min_stock_rules_per_category()
        return res
