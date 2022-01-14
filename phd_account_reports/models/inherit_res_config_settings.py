# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api, _


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    general_ledger_delivered_account = fields.Many2one(related='company_id.general_ledger_delivered_account',
                                                       string='Stock Delivered', readonly=False)
