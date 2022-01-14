# Copyright © 2021 Novobi, LLC
# See LICENSE file for full copyright and licensing details.

import logging

from odoo import fields, models, api, exceptions, _
from odoo.tools.float_utils import float_is_zero, float_compare, float_round

_logger = logging.getLogger(__name__)


class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    ###############################
    # FIELDS DECLARATION
    ###############################

    ###############################
    # BUSINESS METHODS
    ###############################
    @api.model
    def create_manufacturing_orders_from_replenishment_planning(self, data, warehouse_id):
        """
        :param data:
        Ex: {
            (product_id, bom_id):
                {
                    'bom_id': bom_id,
                    'line': line_id,
                    'parent_id': parent_id,
                    'product_id': material.id,
                    'level': level,
                    'po_qty': po_qty,
                    'mo_qty': mo_qty,
                    'requested_qty': requested_qty,
                    'po_percentage': po_percentage,
                }, ...
        }
        """
        decimal_pre = self.env['decimal.precision'].precision_get('Product Unit of Measure')
        stock_move_env = self.env['stock.move'].sudo()
        create_data_product_dict = self.generate_create_data(data, warehouse_id, decimal_pre)

        # The data that can not be merged, create the new manufacturing orders to manufacture those finish goods
        create_data = list(create_data_product_dict.values())
        manufacturing_orders = self.browse()
        if create_data:
            manufacturing_orders = self.create(create_data)
            for mo in manufacturing_orders:
                stock_move_env.create(mo._get_moves_raw_values())
                mo._generate_finished_moves()
                product_qty = mo.product_uom_id._compute_quantity(mo.product_qty,
                                                                  mo.bom_id.product_uom_id)
                exploded_boms, dummy = mo.bom_id.explode(mo.product_id,
                                                         product_qty / mo.bom_id.product_qty,
                                                         picking_type=mo.bom_id.picking_type_id)
                mo._generate_workorders(exploded_boms)
        return manufacturing_orders

    def generate_create_data(self, data, warehouse_id, decimal_pre):
        """
            Remove the line with 0 order request

        :param data:
        :param decimal_pre:
        :return:
        Ex: {
                (product_id, bom_id):
                    {
                        'bom_id': bom_id,
                        'line': line_id,
                        'parent_id': parent_id,
                        'product_id': material.id,
                        'level': level,
                        'po_qty': po_qty,
                        'mo_qty': mo_qty,
                        'requested_qty': requested_qty,
                        'po_percentage': po_percentage,
                    }, ...
            }
        :rtype: dict
        """
        create_data = []
        create_data_product_dict = {}
        manufacturing_product_ids = []
        warehouse = self.env['stock.warehouse'].browse(warehouse_id)

        # Remove 0 request quantity line
        for line in data:
            bom_id = int(line.get('bom_id', 0) or 0)
            product_id = int(line['product_id'])
            mo_qty = float(line['mo_qty'])
            if bom_id and float_compare(mo_qty, 0.0, precision_digits=decimal_pre) > 0:
                create_data.append({
                    'product_id': product_id,
                    'product_qty': mo_qty,
                    'bom_id': bom_id,
                    'picking_type_id': warehouse.manu_type_id.id,
                    'location_src_id': warehouse.manu_type_id.default_location_src_id.id,
                    'location_dest_id': warehouse.manu_type_id.default_location_dest_id.id,
                })
                manufacturing_product_ids.append(product_id)

        _logger.info("Data to create MO: %s", create_data)

        products = self.env['product.product'].search([('id', 'in', manufacturing_product_ids)])
        product_uom_dict = products.get_product_uom_dict()
        for data in create_data:
            product_id = data['product_id']
            bom_id = data['bom_id']
            data_item = create_data_product_dict.get((product_id, bom_id))
            if data_item:
                data_item['product_qty'] += data['product_qty']
            else:
                create_data_product_dict[(product_id, bom_id)] = data
                data_item = data
            data_item['product_uom_id'] = product_uom_dict.get(product_id)

        return create_data_product_dict
