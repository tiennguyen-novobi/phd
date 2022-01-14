# Copyright © 2021 Novobi, LLC
# See LICENSE file for full copyright and licensing details.

import logging
import pandas as pd
from datetime import datetime

from odoo import models, fields, api, _
from odoo.tools import float_compare
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class ReplenishmentHistory(models.Model):
    _name = "replenishment.history"
    _description = "Replenishment History"
    _order = "create_date desc"

    ###############################
    # FIELDS DECLARATION
    ###############################
    name = fields.Char(string='Replenishment Reference', required=True, readonly=True, index=True, default=lambda self: _('New'))
    replenishment_date = fields.Datetime(string='Replenishment Date', required=True, readonly=True, index=True,
                                         default=lambda self: datetime.utcnow(),
                                         help="The default value is the current time at user's timezone."
                                              "If timezone of the user is not set, we use UTC")
    replenishment_history_lines = fields.One2many(
        'replenishment.history.line', 'replenishment_id', string='Replenishment Lines')
    purchase_order_ids = fields.Many2many(
        'purchase.order',
        relation='replenishment_history_purchase_order_rel',
        columns1='id',
        columns2='replenishment_id',
        copy=False)
    manufacturing_order_ids = fields.Many2many(
        'mrp.production',
        relation='replenishment_history_mrp_production_rel',
        columns1='id',
        columns2='replenishment_id',
        copy=False)
    number_of_purchased_products = fields.Integer(string='# Of Purchased Products',
        readonly=True, compute='_compute_purchased_and_manufactured_products', store=True)
    number_of_manufactured_products = fields.Integer(
        string='# Of Manufactured Products', readonly=True,
        compute='_compute_purchased_and_manufactured_products', store=True)
    number_of_purchase_orders = fields.Integer(
        string='# Purchase Orders', compute='_compute_number_of_purchase_orders')
    number_of_manufactured_orders = fields.Integer(
        string='# Manufacturing Orders', compute='_compute_number_of_manufactured_orders')
    purchased_products = fields.Many2many(
        "replenishment.history.line",
        relation="purchased_products_rel",
        compute='_compute_purchased_and_manufactured_products',
        readonly=True,
        help="Listing all products will be added to the linked Purchase Plan when this Replenishment History is created")
    manufactured_products = fields.Many2many(
        "replenishment.history.line",
        "manufactured_products_rel",
        compute='_compute_purchased_and_manufactured_products',
        readonly=True,
        help="Listing all products will be generated Manufacturing Orders when this Replenishment History is created")
    responsible_id = fields.Many2one(
        'res.users', string="Responsible", help="Person responsible for this replenishment.", readonly=True)
    timezone = fields.Selection(
        string='User timezone', related='responsible_id.tz', readonly=True,
        help="User's timezone when they created this replenishment")
    company_id = fields.Many2one(
        'res.company', string='Company', default=lambda self: self.env.company.id, readonly=True)

    #################################
    # COMPUTE METHODS
    #################################
    @api.depends('purchase_order_ids')
    def _compute_number_of_purchase_orders(self):
        self.number_of_purchase_orders = len(self.purchase_order_ids)

    @api.depends('manufacturing_order_ids')
    def _compute_number_of_manufactured_orders(self):
        self.number_of_manufactured_orders = len(self.manufacturing_order_ids)

    @api.depends('replenishment_history_lines')
    def _compute_purchased_and_manufactured_products(self):
        company_id = self.env.company.id
        records = self.env['replenishment.history.line'].search_read(
            [('replenishment_id', '=', self.id),
             ('company_id', '=', company_id)], ['id', 'order_type'])

        # filter records to show in Purchase Plan Information/Manufacturing Orders Information tab
        purchased_ids = []
        manufactured_ids = []
        for item in records:
            item_order_type = item.get('order_type')
            item_id = item.get('id')
            if item_order_type == 'by_purchase':
                purchased_ids.append(item_id)
            elif item_order_type == 'by_manufacture':
                manufactured_ids.append(item_id)

        # update the result
        self.purchased_products = [(6, 0, purchased_ids)]
        self.manufactured_products = [(6, 0, manufactured_ids)]
        self.number_of_purchased_products = len(purchased_ids)
        self.number_of_manufactured_products = len(manufactured_ids)

    #################################
    # ACTION METHODS
    #################################
    @api.model
    def auto_replenishment(self, data, warehouse_id, create_po=True, create_mo=True):
        """
        Open a tree view of Replenishment History
        :param data: the quantity of each product in the Replenishment Planning report to create Purchase Order or Manufacturing Orders
        :type data: List[dict]
            Ex: [{'bom_id': dataset.id || null, 'line': dataset.line, 'parent_id': dataset.parent_id,
                  'product_id': dataset.alternative_product_id, 'level': dataset.level || 1, 'po_qty': po_qty,
                  'mo_qty': mo_qty, 'requested_qty': requested_qty, 'po_percentage': po_percentage,}]
        """
        if not data:
            raise UserError(_("No need to replenish any products at this time"))

        df = pd.DataFrame.from_records(data)
        df = df.groupby(['product_id'], as_index=False).aggregate({'po_qty': 'sum', 'mo_qty': 'sum'})
        df['product_id'] = df['product_id'].astype(int)
        total_purchase_manufacture_qty = df['po_qty'].sum() + df['mo_qty'].sum()
        if float_compare(total_purchase_manufacture_qty, 0.0, precision_digits=3) <= 0:
            raise UserError(_("No need to replenish any products at this time"))

        # Get the factor of UoM
        product_env = self.env['product.product']
        product_ids = df['product_id'].unique().tolist()
        product_uom_factors = product_env._get_product_uom(product_ids=product_ids)
        purchase_uom_factors = product_env._get_product_uom_of_purchase(product_ids=product_ids)
        bom_uom_factors = product_env._get_product_uom_of_manufacture(product_ids=product_ids)

        df['is_purchased'] = df['po_qty'] > 0
        df['is_manufactured'] = df['mo_qty'] > 0
        df['product_uom_factor'] = df['product_id'].apply(
            lambda row: product_uom_factors.get(row, {}).get('factor', 1))
        df['purchase_uom_factor'] = df[['product_id', 'is_purchased']].apply(
            lambda row: purchase_uom_factors.get(row['product_id'], {}).get('purchase_uom_factor', 1) if \
                row['is_purchased'] is True else 1, axis=1)
        df['bom_uom_factor'] = df[['product_id', 'is_manufactured']].apply(
            lambda row: bom_uom_factors.get(row['product_id'], {}).get('bom_uom_factor', 1) if \
                row['is_manufactured'] is True else 1, axis=1)
        # Convert order qty to qty at Purchase UoM or Manufactured UoM
        df['po_qty'] = (df['po_qty'] / df['product_uom_factor']) * df['purchase_uom_factor']
        df['mo_qty'] = (df['mo_qty'] / df['product_uom_factor']) * df['bom_uom_factor']

        new_replenishment_lines = []
        for row_id, row_values in df.iterrows():
            pid = row_values.get('product_id')
            po_qty = row_values.get('po_qty', 0)
            mo_qty = row_values.get('mo_qty', 0)
            # Note: a product can be list in Purchase Plans tab and Manufacturing Orders tab
            if create_po and float_compare(po_qty, 0.0, precision_digits=3) > 0:
                new_replenishment_lines.append({
                    'product_id': pid,
                    'order_quantity': po_qty,
                    'order_type': 'by_purchase',
                    'purchase_uom': purchase_uom_factors.get(pid, {}).get('purchase_uom_id')
                })

            if create_mo and float_compare(mo_qty, 0.0, precision_digits=3) > 0:
                new_replenishment_lines.append({
                    'product_id': pid,
                    'order_quantity': mo_qty,
                    'order_type': 'by_manufacture',
                    'bom_uom': bom_uom_factors.get(pid, {}).get('bom_uom_id')
                })
        if not new_replenishment_lines:
            raise UserError(_("No need to replenish any products at this time"))

        _logger.info('Records to create replenishment history lines: %s', new_replenishment_lines)
        vals = {
            'replenishment_date': datetime.utcnow(),
            'responsible_id': self.env.user.id,
            'company_id': self.env.company.id,
            'replenishment_history_lines': [(0, 0, item) for item in new_replenishment_lines],
        }
        if create_po:
            new_purchase_orders = self.env['purchase.order'].create_purchase_order_from_replenishment_planning(data, warehouse_id)
            vals['purchase_order_ids'] = new_purchase_orders and [(6, 0, new_purchase_orders.ids)] or []
        if create_mo:
            new_manufacturing_orders = self.env['mrp.production'].create_manufacturing_orders_from_replenishment_planning(data, warehouse_id)
            vals['manufacturing_order_ids'] = new_manufacturing_orders and [(6, 0, new_manufacturing_orders.ids)] or []
        new_replenishment_record = self.create(vals)
        view_id = self.env.ref('me_replenishment_planning.replenishment_history_view_form').id
        action_data = {
            'type': 'ir.actions.act_window',
            'name': _('Replenishment History'),
            'res_model': 'replenishment.history',
            'view_mode': 'tree,form',
            'view_type': 'form',
            'views': [[view_id, 'form']],
            'res_id': new_replenishment_record.id,
            'context': {},
            'target': 'current'
        }
        return action_data

    def action_view_purchase_orders(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Purchase Orders'),
            'res_model': 'purchase.order',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', self.purchase_order_ids.ids)],
            'context': {}
        }

    def action_view_manufacturing_orders(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Manufacturing Orders'),
            'res_model': 'mrp.production',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', self.manufacturing_order_ids.ids)]
        }

    #################################
    # CRUD METHODS
    #################################
    def create(self, vals):
        if not vals.get('name', False):
            vals['name'] = self.get_next_sequence_replenishment_history()
        return super(ReplenishmentHistory, self).create(vals)

    #################################
    # BUSINESS METHODS
    #################################
    def get_next_sequence_replenishment_history(self):
        """
            Generate new name for a new Replenishment History
        """
        return self.env['ir.sequence'].next_by_code('replenishment.history')
