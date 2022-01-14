# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from datetime import datetime


class RoyaltyTrackingLine(models.Model):
    _name = "royalty.tracking.line"
    _description = 'Royalty Tracking Line'

    ###################################
    # FIELDS
    ###################################

    royalty_tracking_id = fields.Many2one('royalty.tracking')

    royalty_info_id = fields.Many2one('royalty.info')

    invoice_id = fields.Many2one('account.move')

    royalty_tracking_line_detail_ids = fields.One2many('royalty.tracking.line.detail', 'royalty_tracking_line_id')

    date_start = fields.Datetime(string='Start Date',
                                 default=lambda self: datetime.now().replace(hour=0, minute=0, second=0, microsecond=0))
    date_end = fields.Datetime(string='End Date', copy=False)

    product_id = fields.Many2one('product.product', related='royalty_tracking_id.product_id', store=True)
    qty_consumed = fields.Float(string='Total Used', digits='Product Unit of Measure', compute='_compute_quantity')
    qty_invoiced = fields.Float(string='Total Paid', digits='Product Unit of Measure', compute='_compute_quantity')

    standard_price = fields.Float(string='Cost', related='royalty_info_id.standard_price', digits='Product Price')


    ###################################
    # COMPUTE FUNCTIONS
    ###################################

    @api.depends('royalty_tracking_line_detail_ids')
    def _compute_quantity(self):
        for tracking_line in self:
            tracking_line.qty_consumed = tracking_line._get_consumed_qty()
            tracking_line.qty_invoiced = 0

    def action_show_details(self):
        self.ensure_one()
        domain = [('royalty_tracking_line_id', '=', self.id)]
        action = {
            'type': 'ir.actions.act_window',
            'views': [(self.env.ref('phd_royalty.royalty_tracking_line_detail_tree_view').id, 'tree')],
            'view_mode': 'tree,form',
            'name': _('Royalty Tracking Lines'),
            'res_model': 'royalty.tracking.line.detail',
            'domain': domain
        }
        return action

    def _prepare_invoice_line(self):
        self.ensure_one()
        res = {
            'account_id': self.product_id.categ_id.property_consumable_account_id.id,
            'product_id': self.product_id.id,
            'product_uom_id': self.product_id.uom_id.id,
            'quantity': self.qty_consumed,
            'price_unit': self.standard_price,
            'move_id': self.invoice_id.id,
        }
        return res

    def _get_consumed_qty(self):
        consumed_qty = sum(self.royalty_tracking_line_detail_ids.mapped('product_uom_qty'))
        return consumed_qty
