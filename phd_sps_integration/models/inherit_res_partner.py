# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class ResPartner(models.Model):
    _inherit = 'res.partner'

    ###################################
    # FIELDS
    ###################################
    _sql_constraints = [
        ('address_location_number_uniq', 'unique(address_location_number)',
         'Address Location Number has already set for another contact')]

    address_location_number = fields.Char("Address Location Number", copy=False, index=True)

    has_sps_order_acknowledgement = fields.Boolean(string='Order Acknowledgement', copy=False)
    has_sps_order_change = fields.Boolean(string='Order Change', copy=False)
    has_sps_order_change_ack = fields.Boolean(string='Order Change Acknowledgement', copy=False)

    sps_delivery_window_start_date_code = fields.Many2one('sps.date.qualifier', string="SPS Delivery Window Start Code")
    sps_delivery_window_end_date_code = fields.Many2one('sps.date.qualifier', string="SPS Delivery Window End Code")
    sps_requested_delivery_date_code = fields.Many2one('sps.date.qualifier',
                                                       string="SPS Requested Delivery Window Code")
    has_sps_rejected_reason = fields.Boolean(string="Rejected Reason")
    sps_item_schedule_qualifier = fields.Char(string='Item Schedule Qualifier')
    sps_current_scheduled_delivery_date_code = fields.Char(string='Current Scheduled Delivery Date Code')
    # vendor_number = fields.Char('Vendor Number')
    # sps_division = fields.Char(string="SPS Division")
