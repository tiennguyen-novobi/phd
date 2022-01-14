# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class RoyaltyInfo(models.Model):
    _name = "royalty.info"
    _description = 'Royalty Tracking Info'
    _order = 'min_qty asc'

    ###################################
    # FIELDS
    ###################################

    royalty_tracking_id = fields.Many2one('royalty.tracking')
    royalty_tracking_line_ids = fields.One2many('royalty.tracking.line', 'royalty_info_id')

    min_qty = fields.Float(string='Min Qty', required=True, digits='Product Unit of Measure')
    standard_price = fields.Float(string='Cost', required=True, digits='Product Price')

    ###################################
    # CONSTRAINS
    ###################################
    @api.constrains('min_qty')
    def _check_min_qty(self):
        for info in self:
            if info.min_qty < 0:
                raise ValidationError(_('Min Quantity must be greater 0.'))
