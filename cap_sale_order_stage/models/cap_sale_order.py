# coding: utf-8
# Part of CAPTIVEA. Odoo 12 EE.

from odoo import fields, models, api


class SaleOrder(models.Model):
    """Manage 'sale.order' model."""
    _inherit = "sale.order"

    stage_id = fields.Many2one(
        'sale.order.stage',  domain="[('id', 'in', main_product_stage_ids)]", string='New stage')
    main_product_id = fields.Many2one('main.product',  string='Main Product')
    main_product_stage_ids = fields.Many2many(
        related='main_product_id.deal_stage_ids', readonly=True)

    @api.onchange('main_product_id')
    def onchange_lang_localization(self):
        """Managed onchange for set default value of stage and if stage 
        has no other stage_ids then it will not set default value.."""
        if self.main_product_id:
            if len(self.main_product_id.deal_stage_ids) > 0:
                self.stage_id = self.main_product_id.deal_stage_ids[0]
            else:
                self.stage_id = False
