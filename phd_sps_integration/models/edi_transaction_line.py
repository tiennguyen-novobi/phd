# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from odoo.addons.phd_sps_integration.models.edi_transaction import PO_ACK, PO_CHANGE, LINE_ACCEPT, \
    LINE_DATE_RESCHEDULED, LINE_QUANTITY_CHANGE, LINE_REJECT, \
    LINE_CHANGE, LINE_DELETE, LINE_QTY_DECREASE, LINE_QTY_INCREASE, LINE_DATE_CHANGE, LINE_PRICE_QTY_CHANGE, \
    LINE_PRICE_CHANGE, LINE_ADD, LINE_CHANGE_PRICING, LINE_BACK_ORDER


class EDITransactionLine(models.Model):
    _name = "edi.transaction.line"
    _description = "EDI Transaction Line"

    ###################################
    # FIELDS
    ###################################
    sps_sequence_number = fields.Char('SPS Line Sequence')
    order_line_id = fields.Many2one('sale.order.line', string='Order Line', ondelete='set null')
    product_id = fields.Many2one('product.product', string='Product')
    edi_transaction_id = fields.Many2one('edi.transaction', ondelete='cascade', string='EDI Transaction')
    ack_status_code = fields.Selection([(LINE_ACCEPT, _('Accept')),
                                        (LINE_DATE_RESCHEDULED, _('Accept - Date Rescheduled')),
                                        (LINE_QUANTITY_CHANGE, _('Accept - Quantity Changed')),
                                        (LINE_REJECT, _('Item Rejected')),
                                        (LINE_CHANGE_PRICING, _('Change The Pricing')),
                                        (LINE_BACK_ORDER, _('Back Order'))],
                                       string='Status Code')
    change_status_code = fields.Selection([(LINE_CHANGE, _('Changes To Line Items')),
                                           (LINE_DELETE, _('Delete Item(s)')),
                                           (LINE_QTY_DECREASE, _('Quantity Decrease')),
                                           (LINE_QTY_INCREASE, _('Quantity Increase')),
                                           (LINE_DATE_CHANGE, _('Change of Dates')),
                                           (LINE_PRICE_QTY_CHANGE, _('Unit Price/ Quantity Change')),
                                           (LINE_PRICE_CHANGE, _('Price Change')),
                                           (LINE_ADD, _('Add Additional Item(s)'))],
                                          string='Status Code')
    old_price_unit = fields.Float('Old Price Unit', digits='Product Price')
    price_unit = fields.Float('Unit Price', digits='Product Price')

    old_product_uom_qty = fields.Float('Old Quantity', digits='Product Unit of Measure')
    product_uom_qty = fields.Float('Quantity', digits='Product Unit of Measure')
    product_schedule_date = fields.Datetime(string='Schedule Date')
    note = fields.Char(string="Note")

    ###################################
    # ONCHANGE FUNCTIONS
    ###################################
    @api.onchange('order_line_id')
    def _onchange_order_line(self):
        order_line_id = self.order_line_id
        if self.order_line_id:
            self.update({
                'product_id': order_line_id.product_id,
                'sps_sequence_number': order_line_id.sps_sequence_number
            })

    ###################################
    # GENERAL FUNCTIONS
    ###################################
    @api.model
    def create(self, vals):
        res = super(EDITransactionLine, self).create(vals)
        if res.order_line_id:
            vals = {}
            if not res.product_id:
                vals.update({'product_id': res.order_line_id.product_id})
            if not res.sps_sequence_number:
                vals.update({'product_id': res.order_line_id.sps_sequence_number})
            if vals:
                res.write(vals)
        return res

    @api.constrains('ack_status_code')
    def _constrains_ack_status_code(self):
        for record in self:
            vendor_855_code = self.env['edi.transaction.setting'].search(
                [('partner_id', '=', record.edi_transaction_id.partner_id.id)],
                limit=1).vendor_line_status_code_ids.mapped('code')
            if record.ack_status_code:
                if not record.ack_status_code in vendor_855_code:
                    raise UserError(
                        _("Ack Status Code '%s' is not supported for Partner : %s" % (
                        record.ack_status_code, record.edi_transaction_id.partner_id.name)))
