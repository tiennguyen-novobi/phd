# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from odoo.addons.phd_sps_integration.models.edi_transaction import PO_ACK, PO_CHANGE, LINE_ACCEPT, \
    LINE_DATE_RESCHEDULED, LINE_QUANTITY_CHANGE, LINE_REJECT, \
    LINE_CHANGE, LINE_DELETE, LINE_QTY_DECREASE, LINE_QTY_INCREASE, LINE_DATE_CHANGE, LINE_PRICE_QTY_CHANGE, \
    LINE_PRICE_CHANGE, LINE_ADD


class EDITransactionLineSetting(models.Model):
    _name = "edi.transaction.setting"
    _description = "EDI Transaction Setting"
    _rec_name = 'partner_id'

    ###################################
    # FIELDS
    ###################################
    partner_id = fields.Many2one('res.partner', string='Customer')
    vendor_line_status_code_ids = fields.Many2many('edi.vendor.line.status.code')


