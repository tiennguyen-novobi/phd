# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.addons.phd_tracking.models.delay_tracker import DELAYED, ON_TRACK, ON_HOLD

class DelayTrackerPublicInfo(models.Model):
    _name = "delay.tracker.mixin"
    _description = "Delay Tracker Public Info"

    ###################################
    # FIELDS
    ###################################
    delay_tracker_ids = fields.One2many('delay.tracker', 'sale_id', string='Delay Trackers',
                                        copy=False)

    number_of_day_delayed = fields.Integer("Number of Days Delayed", compute='_compute_delay_info', store=True)
    status = fields.Selection([(DELAYED, _('Delayed')),
                               (ON_TRACK, _('On Track')),
                               (ON_HOLD, _('On Hold'))], compute='_compute_delay_info', store=True)

    ###################################
    # PUBLIC FUNCTIONS
    ###################################
    @api.depends('delay_tracker_ids')
    def _compute_delay_info(self):
        for tracker_info in self:
            if tracker_info.delay_tracker_ids:
                delay_tracker = tracker_info.delay_tracker_ids[-1]
                tracker_info.update({
                    'number_of_day_delayed': delay_tracker.number_of_day_delayed,
                    'status': delay_tracker.status,
                })



