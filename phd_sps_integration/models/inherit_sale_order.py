# -*- coding: utf-8 -*-

import logging


from odoo import api, fields, models, SUPERUSER_ID, _

from odoo.addons.phd_sps_integration.models.edi_transaction import PO_ACK, PO_CHANGE

_logger = logging.getLogger(__name__)

class SalesOrder(models.Model):
    _inherit = 'sale.order'

    ###################################
    # FIELDS
    ###################################

    sps_trading_partner_id = fields.Char('SPS Trading Partner ID', copy=False)

    vendor_code = fields.Char(string="Vendor Code", help="Number assigned by buyer that uniquely identifies the vendor",
                              copy=False)

    packaging_characteristic_code = fields.Char('Packaging Characteristic Code', copy=False)
    packaging_description = fields.Char('Packaging Description', copy=False)
    carrier_routing = fields.Char('Carrier Routing', copy=False)

    edi_transaction_ids = fields.One2many('edi.transaction', 'order_id', string='Acknowledgement')
    order_ack_count = fields.Integer(compute='_compute_order_ack_count',
                                     string='Acknowledgement', default=0, store=True)
    order_change_count = fields.Integer(compute='_compute_order_ack_count',
                                        string='PO Change', default=0, store=True)

    has_sps_order_acknowledgement = fields.Boolean(compute='_compute_has_order_acknowledgement')
    sps_customer_order_number = fields.Char(string='Customer Order Number', help='')
    sps_delivery_window_start_date = fields.Date("Delivery Window Start date")
    sps_delivery_window_end_date = fields.Date("Delivery Window End date")
    sps_division = fields.Char(string='SPS Division')

    ###################################
    # COMPUTE FUNCTIONS
    ###################################
    def _compute_has_order_acknowledgement(self):
        for order in self:
            order.has_sps_order_acknowledgement = order.state in ['draft', 'sent'] \
                                                  and order.get_has_order_acknowledgement(order.partner_id) \
                                                  and not order._get_edi_transaction_ids(PO_ACK) \
                                                  and order.sps_trading_partner_id

    @api.depends('edi_transaction_ids')
    def _compute_order_ack_count(self):
        for order in self:
            order.order_ack_count = len(order._get_edi_transaction_ids(PO_ACK))
            order.order_change_count = len(order._get_edi_transaction_ids(PO_CHANGE))

    ###################################
    # PUBLIC FUNCTIONS
    ###################################
    def action_acknowledge_order(self):
        self.ensure_one()
        context = {
            'default_order_id': self.id,
            'default_type': PO_ACK
        }
        action = {
            'name': _('Order Acknowledgement'),
            'type': 'ir.actions.act_window',
            'views': [(self.env.ref('phd_sps_integration.view_edi_transaction_form').id, 'form')],
            'view_mode': 'form',
            'res_model': 'edi.transaction',
            'context': context
        }
        return action

    def action_view_order_acknowledgement(self):
        """ This function returns an action that display existing acknowledgement orders of given sales order ids.
        When only one found, show the acknowledgement order immediately.
        """
        action = self.env.ref('phd_sps_integration.edi_transaction_action')
        result = action.read()[0]
        edi_transaction_ids = self._get_edi_transaction_ids(PO_ACK)
        # override the context to get rid of the default filtering on operation type
        result['context'] = {'default_order_id': self.id,
                             'create': self.state in ['draft', 'sent'],
                             'default_type': PO_ACK}
        # choose the view_mode accordingly
        if not edi_transaction_ids or len(edi_transaction_ids) > 1:
            result['domain'] = "[('id','in',%s)]" % edi_transaction_ids.ids
        elif len(edi_transaction_ids) == 1:
            res = self.env.ref('phd_sps_integration.view_edi_transaction_form', False)
            form_view = [(res and res.id or False, 'form')]
            if 'views' in result:
                result['views'] = form_view + [(state, view) for state, view in result['views'] if view != 'form']
            else:
                result['views'] = form_view
            result['res_id'] = edi_transaction_ids.id
        return result

    def action_view_order_change(self):
        """ This function returns an action that display existing order change of given sales order ids.
        When only one found, show the order change immediately.
        """
        action = self.env.ref('phd_sps_integration.edi_transaction_action')
        result = action.read()[0]
        edi_transaction_ids = self._get_edi_transaction_ids(PO_CHANGE)
        # override the context to get rid of the default filtering on operation type
        result['context'] = {'create': False,
                             'edit': False}
        # choose the view_mode accordingly
        if not edi_transaction_ids or len(edi_transaction_ids) > 1:
            result['domain'] = "[('id','in',%s)]" % edi_transaction_ids.ids
        elif len(edi_transaction_ids) == 1:
            res = self.env.ref('phd_sps_integration.view_edi_transaction_form', False)
            form_view = [(res and res.id or False, 'form')]
            if 'views' in result:
                result['views'] = form_view + [(state, view) for state, view in result['views'] if view != 'form']
            else:
                result['views'] = form_view
            result['res_id'] = edi_transaction_ids.id
        return result

    ###################################
    # HELPER FUNCTIONS
    ###################################
    def _get_edi_transaction_ids(self, document_type):
        """
        :param document_type:
        :type document_type: str
        :return:
        """
        res = self.edi_transaction_ids.filtered(lambda ack: ack.type == document_type)
        return res

    def get_has_order_acknowledgement(self, partner_obj):
        """
        Get parent has_order_acknowledgement
        :param partner_obj:
        :type partner_obj: object
        :return:
        :rtype:
        """
        has_sps_order_acknowledgement = partner_obj.has_sps_order_acknowledgement
        partner = partner_obj
        while partner.parent_id and not has_sps_order_acknowledgement:
            partner = partner.parent_id
            has_sps_order_acknowledgement = partner.has_sps_order_acknowledgement

        return has_sps_order_acknowledgement
