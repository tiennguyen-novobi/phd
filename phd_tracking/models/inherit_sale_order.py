# -*- coding: utf-8 -*-

from odoo import models, fields, api, _

from odoo.exceptions import UserError
from odoo.addons.phd_tracking.models.delay_tracker import ON_TRACK


class SaleOrder(models.Model):
    _name = 'sale.order'
    _inherit = ['delay.tracker.mixin', 'sale.order']

    ###################################
    # FIELDS
    ###################################
    delay_tracker_ids = fields.One2many(inverse_name='sale_id')

    ###################################
    # GENERAL FUNCTIONS
    ###################################
    @api.model
    def create(self, vals):
        commitment_date = vals.get('commitment_date')
        delay_tracker_ids = vals.get('delay_tracker_ids')
        if commitment_date and not delay_tracker_ids:
            delay_tracker_id = {
                'promised_date': commitment_date,
                'status': ON_TRACK,
            }
            vals.update({'delay_tracker_ids': [(0, 0, delay_tracker_id)]})

        res = super(SaleOrder, self).create(vals)
        return res

    ###################################
    # PUBLIC FUNCTIONS
    ###################################
    def action_cancel(self):
        res = super(SaleOrder, self).action_cancel()

        self.mapped('delay_tracker_ids').unlink()
        self.write({
            'commitment_date': False
        })

        return res

    def action_confirm(self):
        for sale_order in self:
            if not sale_order.commitment_date:
                raise UserError(_('Sale Order %s\'s Delivery Date need to be set' % sale_order.name))

        res = super(SaleOrder, self).action_confirm()
        return res

    def action_update_promised_delivery_date(self):
        sale_order = self
        action = sale_order.delay_tracker_ids.get_action_update_promised_date(sale_order)

        return action

    def update_delivery_date(self, delivery_date):
        self.commitment_date = delivery_date
        picking_ids = self.picking_ids.filtered(lambda pick: pick.state in ['draft', 'confirmed', 'assigned'])
        picking_ids.write({
            'scheduled_date': delivery_date
        })
