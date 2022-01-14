# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class PHDProduceConfirmation(models.TransientModel):
    _name = 'phd.produce.confirmation'

    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id)
    mrp_product_produce_id = fields.Many2one('mrp.product.produce')
    extra_cost = fields.Monetary()

    def action_confirm(self):
        if self.mrp_product_produce_id:
            context = self.env.context
            return self.mrp_product_produce_id.with_context(context).do_produce()
