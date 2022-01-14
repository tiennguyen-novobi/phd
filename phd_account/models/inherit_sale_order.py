# -*- coding: utf-8 -*-

from odoo import models, fields, api, _

from odoo.addons.purchase.models.purchase import PurchaseOrder as Purchase


class SalesOrder(models.Model):
    _inherit = 'sale.order'

    ###################################
    # HELPER FUNCTIONS
    ###################################
    def _prepare_invoice(self):
        res = super(SalesOrder, self)._prepare_invoice()
        res.update({
            'order_id': self.id,
            'sps_po_number': self.sps_trading_partner_id and self.client_order_ref
        })

        return res
