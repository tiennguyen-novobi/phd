# -*- coding: utf-8 -*-

from odoo import models, fields, api, _

from odoo.exceptions import UserError
from odoo.addons.purchase.models.purchase import PurchaseOrder as Purchase


class PurchaseOrder(models.Model):
    _name = 'purchase.order'
    _inherit = ['delay.tracker.mixin', 'purchase.order']

    ###################################
    # FIELDS
    ###################################
    delay_tracker_ids = fields.One2many(inverse_name='purchase_id')

    date_planned = fields.Datetime(copy=False)

    ###################################
    # PUBLIC FUNCTIONS
    ###################################
    def action_cancel(self):
        res = super(PurchaseOrder, self).action_cancel()

        self.mapped('delay_tracker_ids').unlink()
        self.write({
            'date_planned': False
        })

        return res

    def button_confirm(self):
        for purchase_order in self:
            if not purchase_order.date_planned:
                raise UserError(_('Purchase Order %s\'s Receipt Date need to be set' % purchase_order.name))
        res = super(PurchaseOrder, self).button_confirm()

        return res

    def action_update_promised_receipt_date(self):
        purchase_order = self
        action = purchase_order.delay_tracker_ids.get_action_update_promised_date(purchase_order)

        return action

    def update_receipt_date(self, receipt_date):
        self.date_planned = receipt_date
        picking_ids = self.picking_ids.filtered(lambda pick: pick.state in ['draft', 'confirmed', 'assigned'])
        picking_ids.write({
            'scheduled_date': receipt_date
        })
        

    @api.model
    def create(self, vals_list):
        res = super(PurchaseOrder, self).create(vals_list)
        if res and res.date_planned and res.state == 'draft':
            delay_tracker_id = {
                'promised_date': res.date_planned,
                'status_date': res.date_planned,
                'status': 'on_track',
                'purchase_id': res.id,
            }
            self.env['delay.tracker'].create(delay_tracker_id)
        return res
    
