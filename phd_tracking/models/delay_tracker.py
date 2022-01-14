# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from datetime import date, datetime
from dateutil import tz

DELAYED = 'delayed'
ON_TRACK = 'on_track'
ON_HOLD = 'on_hold'


class DelayTracker(models.Model):
    _name = "delay.tracker"
    _description = "Delay Tracker"

    ###################################
    # FIELDS
    ###################################
    sale_id = fields.Many2one('sale.order', string="Sales Order",
                              copy=False, ondelete='cascade')
    purchase_id = fields.Many2one('purchase.order', string="Purchase Order",
                                  copy=False, ondelete='cascade')
    production_id = fields.Many2one('mrp.production', string="Production Order",
                                    copy=False, ondelete='cascade')

    partner_id = fields.Many2one('res.partner', compute='_compute_partner_id',
                                 store=True, copy=False)

    status_date = fields.Date(copy=False, default=lambda self: datetime.now())
    promised_date = fields.Date("Promised Date")
    number_of_day_delayed = fields.Integer("Number of Days Delayed", copy=False)

    status = fields.Selection([(DELAYED, _('Delayed')),
                               (ON_TRACK, _('On Track')),
                               (ON_HOLD, _('On Hold'))])

    reason = fields.Text(string='Reason')

    ###################################
    # COMPUTE FUNCTIONS
    ###################################
    @api.depends('sale_id.partner_id', 'purchase_id.partner_id')
    def _compute_partner_id(self):
        for tracker in self:
            if tracker.sale_id:
                tracker.partner_id = tracker.sale_id.partner_id
            elif tracker.purchase_id:
                tracker.partner_id = tracker.purchase_id.partner_id

    ###################################
    # GENERAL FUNCTIONS
    ###################################
    @api.model
    def create(self, vals):
        res = super(DelayTracker, self).create(vals)
        res.update_move_scheduled_date()
        return res

    @api.model
    def write(self, vals):
        res = super(DelayTracker, self).write(vals)
        self.update_move_scheduled_date()
        return res

    ###################################
    # PUBLIC FUNCTIONS
    ###################################
    def get_action_update_promised_date(self, tracking_obj):
        """
        Tracking Obj is Sales Order, Purchase Order and Manufacturing Order
        """
        tracking_obj_model = tracking_obj._name
        state = tracking_obj.state

        is_reason_required = True
        update_delay_tracker_id = None

        # When Obj in draft state, no need to create new tracker, just update the old one
        if state in ['draft', 'sent']:
            is_reason_required = False
            update_delay_tracker_id = tracking_obj.delay_tracker_ids.id

        ctx = {
            'is_reason_required': is_reason_required,
            'update_delay_tracker_id': update_delay_tracker_id
        }
        if tracking_obj_model == 'sale.order':
            action_name = _('Update Delivery Date')
            ctx.update({
                'sale_id': tracking_obj.id,
                'tracking_date': tracking_obj.commitment_date
            })
        elif tracking_obj_model == 'purchase.order':
            action_name = _('Update Receipt Date')
            ctx.update({
                'purchase_id': tracking_obj.id,
                'tracking_date': tracking_obj.date_planned
            })
        elif tracking_obj_model == 'mrp.production':
            action_name = _('Update Finished Date')
            ctx.update({
                'production_id': tracking_obj.id,
                'tracking_date': tracking_obj.date_planned_finished
            })
        return {'type': 'ir.actions.act_window',
                'name': action_name,
                'res_model': 'delay.tracker.creation',
                'target': 'new',
                'view_id': self.env.ref('phd_tracking.delay_tracker_creation_form_view').id,
                'view_mode': 'form',
                'context': ctx
                }

    ###################################
    # HELPER FUNCTIONS
    ###################################
    def update_move_scheduled_date(self):
        promised_date = self.promised_date
        promised_date = self.from_date_to_utc_datetime(promised_date,
                                                       self.env.user.tz)
        if self.sale_id:
            self.sale_id.update_delivery_date(promised_date)
        elif self.purchase_id:
            self.purchase_id.update_receipt_date(promised_date)
        elif self.production_id:
            self.production_id.update_finished_date(promised_date)

        return True

    def from_date_to_utc_datetime(self, from_date, time_zone):
        """
        Using this function when get date from some different timezone environment
        but want to store it to datetime on DB (default UTC)
        :param from_date: Environment timezone
        :type from_date: date
        :param time_zone:
        :type time_zone: str
        :return:
        :rtype: datetime
        """
        from_zone = tz.gettz(time_zone)

        to_zone = tz.tzutc()

        # Convert fromDate to Datetime with time part is 00:00:00 and timezone is time_zone
        dt = datetime.combine(from_date, datetime.min.time(), from_zone)

        to_date_time = dt.astimezone(to_zone).replace(tzinfo=None)

        return to_date_time
