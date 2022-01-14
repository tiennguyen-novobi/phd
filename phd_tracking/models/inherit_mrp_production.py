# -*- coding: utf-8 -*-

from odoo import models, fields, api, _

from odoo.exceptions import UserError
from odoo.addons.purchase.models.purchase import PurchaseOrder as Purchase
from odoo.addons.phd_tracking.models.delay_tracker import ON_TRACK

class MrpProduction(models.Model):
    _name = 'mrp.production'
    _inherit = ['delay.tracker.mixin', 'mrp.production']

    ###################################
    # FIELDS
    ###################################
    delay_tracker_ids = fields.One2many(inverse_name='production_id')
    date_planned_finished = fields.Datetime(default=False)
    last_delay_tracker_id = fields.Many2one('delay.tracker', compute='_compute_last_delay_tracker_id', store=False)
    last_delay_tracker_status = fields.Char(string='Current Status', store=True)
    last_delay_tracker_reason = fields.Text(related='last_delay_tracker_id.reason', string='Description', store=True)

    ###################################
    # GENERAL FUNCTIONS
    ###################################
    @api.model
    def create(self, vals):
        date_planned_finished = vals.get('date_planned_finished')
        if date_planned_finished:
            tracking_vals = {
                'promised_date': date_planned_finished,
                'status': ON_TRACK
            }
            vals.update({'delay_tracker_ids': [(0, 0, tracking_vals)]})
        res = super(MrpProduction, self).create(vals)
        return res

    ###################################
    # PUBLIC FUNCTIONS
    ###################################

    def action_cancel(self):
        res = super(MrpProduction, self).action_cancel()

        self.mapped('delay_tracker_ids').unlink()
        self.write({
            'date_planned_finished': False
        })

        return res

    def action_confirm(self):
        for production in self:
            if not production.date_planned_finished:
                raise UserError(_('Manufacturing Order %s\'s Finished Date need to be set' % production.name))
        res = super(MrpProduction, self).action_confirm()

        return res

    def action_update_promised_finished_date(self):
        production = self
        action = production.delay_tracker_ids.get_action_update_promised_date(production)

        return action

    def update_finished_date(self, finished_date):
        self.date_planned_finished = finished_date
        move_finished_ids = self.move_finished_ids.filtered(
            lambda pick: pick.state in ['draft', 'confirmed', 'assigned'])
        move_finished_ids.write({
            'date_expected': finished_date
        })
        move_raw_ids = self.move_raw_ids.filtered(lambda comp: comp.state in ['draft', 'confirmed', 'assigned'])
        if move_raw_ids:
            move_raw_ids.write({
                'date_expected': finished_date
            })
            for move in move_raw_ids:
                if move.move_line_ids:
                    move.move_line_ids.write({
                        'date': finished_date
                    })

    ###################################
    # ONCHANGE FUNCTIONS
    ###################################
    @api.onchange('date_planned_start')
    def _onchange_date_planned_start(self):
        res = super(MrpProduction, self)._onchange_date_planned_start()
        self.date_planned_finished = self.delay_tracker_ids[-1].promised_date \
            if self.delay_tracker_ids else False
        return res

    @api.depends('delay_tracker_ids')
    def _compute_last_delay_tracker_id(self):
        switcher = {
            'delayed': 'Delayed',
            'on_track': 'On Track',
            'on_hold': 'On Hold',
        }
        for record in self:
            if record.delay_tracker_ids:
                last_delay_tracker = self.env['delay.tracker'].search(
                    [('production_id', '=', record.id)], order="promised_date desc", limit = 1)
                if last_delay_tracker:
                    record.last_delay_tracker_id = last_delay_tracker[0].id
                    record.last_delay_tracker_status = switcher.get(last_delay_tracker[0].status,'')
                else:
                    record.last_delay_tracker_id = False
                    record.last_delay_tracker_status =''
            else:
                record.last_delay_tracker_id = False
                record.last_delay_tracker_status = ''