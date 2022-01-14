# -*- coding: utf-8 -*-

from odoo import tools
from odoo import models, fields, api

from functools import lru_cache


class AccountInvoiceDetailReport(models.Model):
    _name = "account.invoice.detail.report"
    _description = "Invoices Detail Report"
    _auto = False
    _order = 'invoice_date, name desc'

    ###################################
    # FIELDS
    ###################################
    move_id = fields.Many2one('account.move', readonly=True)
    name = fields.Char(readonly=True)
    order_id = fields.Many2one('sale.order', readonly=True)
    partner_id = fields.Many2one('res.partner', string="Customer", readonly=True)
    client_order_ref = fields.Text(readonly=True)
    picking_id = fields.Many2one('stock.picking', readonly=True)
    invoice_date = fields.Datetime(readonly=True)
    default_code = fields.Char(readonly=True)
    product_id = fields.Many2one('product.product', readonly=True)
    quantity = fields.Float(readonly=True)
    price_subtotal = fields.Float(readonly=True)
    price_unit = fields.Float(readonly=True)
    price_total = fields.Float(readonly=True)
    lot_name = fields.Char('Lot Name', readonly=True)
    state = fields.Selection(selection=[('draft', 'Draft'),
                                        ('posted', 'Posted'),
                                        ('cancel', 'Cancelled')],
                             readonly=True)

    ###################################
    # INIT FUNCTIONS
    ###################################
    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute('''
             CREATE OR REPLACE VIEW %s AS (
                 %s %s %s
             )
         ''' % (
            self._table, self._select(), self._from(), self._where()
        ))

    ###################################
    # HELPER FUNCTIONS
    ###################################
    @api.model
    def _select(self):
        return """
            SELECT
                am.invoice_date,
                am.name,
                am.state,
                am.id AS move_id,
                so.id AS order_id,
                am.partner_id,
                so.client_order_ref,
                sp.id as picking_id,
                row_number() OVER (ORDER BY aml.id) AS id,
                aml.price_unit,
                aml.product_id,
                (aml.quantity / line_uom.factor * product_uom.factor)
                    *(aml.price_unit * ( 1 - (aml.discount / 100))) as price_subtotal,
                aml.price_total,
                product.default_code,
                aml.lot_name,
                aml.quantity / line_uom.factor * product_uom.factor AS quantity
        """

    @api.model
    def _from(self):
        return """
            FROM account_move_line aml
                JOIN account_move am ON aml.move_id = am.id
                JOIN product_product product ON product.id = aml.product_id
                JOIN product_template ON product.product_tmpl_id = product_template.id
                LEFT JOIN sale_order so ON am.order_id = so.id
                LEFT JOIN stock_picking sp ON so.id = sp.sale_id
                LEFT JOIN uom_uom line_uom ON line_uom.id = aml.product_uom_id
                LEFT JOIN uom_uom product_uom ON product_uom.id = product_template.uom_id
        """

    @api.model
    def _where(self):
        return """
                WHERE am.type IN ('out_invoice')
                    AND aml.account_id IS NOT NULL
                    AND NOT aml.exclude_from_invoice_tab
        """
