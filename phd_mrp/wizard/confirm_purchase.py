# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class ConfirmPurchase(models.TransientModel):
    _name = 'confirm.purchase'
    _description = 'Subcontracting Product BOM check'

    purchase_id = fields.Many2one('purchase.order')
    warning_message = fields.Char()

    def action_confirm(self):
        self.ensure_one()
        return self.purchase_id.with_context(skip_bom_check=True).button_confirm()
