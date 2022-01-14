# -*- coding: utf-8 -*-
from datetime import datetime

from odoo import models, fields, api, _
from odoo.addons.phd_tracking.models.delay_tracker import DELAYED, ON_TRACK, ON_HOLD


class DelayTrackerCreation(models.TransientModel):
    _name = "delay.tracker.creation"
    _description = "Delay Tracker Creation"

    ###################################
    # FIELDS
    ###################################
    status_date = fields.Date(string="Status Date",
                              copy=False, default=lambda self: datetime.now())
    promised_date = fields.Date(string="Promised Date", required=True)
    number_of_day_delayed = fields.Integer(string="Number of Days Delayed",
                                           copy=False)
    status = fields.Selection([(DELAYED, _('Delayed')),
                               (ON_TRACK, _('On Track')),
                               (ON_HOLD, _('On Hold'))])

    reason = fields.Text(string='Reason')

    ###################################
    # ONCHANGE FUNCTIONS
    ###################################
    @api.onchange('promised_date')
    def _onchange_promised_date(self):
        promised_date = self.promised_date
        if promised_date:
            update_delay_tracker_id = self._context.get('update_delay_tracker_id')

            # If update the old record, then tracking date is the first promised date
            tracking_date = promised_date if update_delay_tracker_id \
                else self.get_tracking_date() or promised_date

            # Set number of delayed day and status
            number_of_day_delayed = (promised_date - tracking_date).days
            number_of_day_delayed = max(0, number_of_day_delayed)

            status = DELAYED if number_of_day_delayed > 0 else ON_TRACK

            self.update({
                'number_of_day_delayed': number_of_day_delayed,
                'status': status
            })

    ###############################
    # PUBLIC FUNCTIONS
    ###############################
    def action_update_tracker(self):
        delay_tracker_env = self.env['delay.tracker']
        update_delay_tracker_id = self._context.get('update_delay_tracker_id')

        # Get all info of tracker
        tracking_vals = self.get_tracking_vals()

        # If state is not confirm, update the old tracker else create new one
        if update_delay_tracker_id:
            delay_tracker = delay_tracker_env.browse(update_delay_tracker_id)
            res = delay_tracker.write(tracking_vals)
        else:
            res = delay_tracker_env.create(tracking_vals)

        return res

    ###################################
    # HELPER FUNCTIONS
    ###################################
    def get_tracking_date(self):
        tracking_date = self._context.get('tracking_date')
        tracking_date = fields.Date.to_date(tracking_date) if tracking_date else None

        return tracking_date

    def get_tracking_vals(self):
        vals = {
            'status_date': self.status_date,
            'promised_date': self.promised_date,
            'number_of_day_delayed': self.number_of_day_delayed,
            'status': self.status,
            'reason': self.reason,
            'sale_id': self._context.get('sale_id', False),
            'purchase_id': self._context.get('purchase_id', False),
            'production_id': self._context.get('production_id', False),
        }

        return vals
