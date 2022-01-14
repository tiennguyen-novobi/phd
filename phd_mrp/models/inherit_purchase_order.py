# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError

from odoo.addons.purchase.models.purchase import PurchaseOrder as Purchase


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    ###################################
    # FIELDS
    ###################################

    subcontract_picking_type_id = fields.Many2one(
        'stock.picking.type', 'Operation Type',
        help=_("The Subcontract Operation Type to define component location and finished product location"),
        states=Purchase.READONLY_STATES)

    production_count = fields.Integer(compute='_compute_production_count',
                                      string='Picking count', default=0, store=True)
    production_ids = fields.One2many('mrp.production', 'purchase_id',
                                     string='Production Order',
                                     copy=False)

    ###################################
    # ONCHANGE FUNCTIONS
    ###################################

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        if self.partner_id:
            picking_type_id = self.partner_id.picking_type_id or self._default_picking_type()
            subcontract_picking_type_id = self.partner_id.subcontract_picking_type_id
            self.update({
                'picking_type_id': picking_type_id,
                'subcontract_picking_type_id': subcontract_picking_type_id
            })

    ###################################
    # COMPUTE FUNCTIONS
    ###################################
    @api.depends('production_ids')
    def _compute_production_count(self):
        for order in self:
            order.production_count = len(order.production_ids)

    ###################################
    # PUBLIC FUNCTIONS
    ###################################

    def button_confirm(self):
        if self.partner_id.subcontract_picking_type_id and not self._context.get('skip_bom_check'):
            have_not_set_bom_line = self.order_line.filtered(lambda line: line.product_id.bom_count == 0)
            if have_not_set_bom_line:
                warning_message = _('BOM(s) cannot be found for the following product(s): %s'
                                    % ', '.join([line.product_id.display_name for line in have_not_set_bom_line]))

                view = self.env.ref('phd_mrp.view_confirm_purchase_popup')
                return {
                    'string': 'Check BOM for Subcontracting Partner',
                    'type': 'ir.actions.act_window',
                    'view_mode': 'form',
                    'res_model': 'confirm.purchase',
                    'views': [(view.id, 'form')],
                    'view_id': view.id,
                    'target': 'new',
                    'context': {
                        'default_purchase_id': self.id,
                        'default_warning_message': warning_message
                    },
                }

        res = super(PurchaseOrder, self).button_confirm()
        return res

    def action_view_production(self):
        """ This function returns an action that display existing manufacturing order orders of given purchase order ids.
        When only one found, show the manufacturing order immediately.
        """
        action = self.env.ref('mrp.mrp_production_action')
        result = action.read()[0]
        result['context'] = None
        production_ids = self.mapped('production_ids')
        # choose the view_mode accordingly
        if not production_ids or len(production_ids) > 1:
            result['domain'] = "[('id','in',%s)]" % (production_ids.ids)
        elif len(production_ids) == 1:
            res = self.env.ref('mrp.mrp_production_form_view', False)
            form_view = [(res and res.id or False, 'form')]
            if 'views' in result:
                result['views'] = form_view + [(state,
                                                view) for state, view in result['views']
                                               if view != 'form']
            else:
                result['views'] = form_view
            result['res_id'] = production_ids.id

        return result


class InheritPurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    @api.constrains('price_unit')
    def _constrains_price_unit(self):
        for record in self:
            production_ids = record.order_id.production_ids.filtered(
                lambda x: x.purchase_line_id.id == record.id and x.state not in ('draft', 'done', 'cancel'))
            if production_ids:
                production_ids[0].extra_cost = record.price_unit
