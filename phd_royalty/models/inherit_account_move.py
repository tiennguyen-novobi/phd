# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class AccountMove(models.Model):
    _inherit = 'account.move'

    ###################################
    # FIELDS
    ###################################

    royalty_tracking_id = fields.Many2one('royalty.tracking.line')
