# Copyright © 2021 Novobi, LLC
# See LICENSE file for full copyright and licensing details.

import logging

from odoo import api, fields, models, _


_logger = logging.getLogger(__name__)


class StockMove(models.Model):
    _inherit = 'stock.move'

    ###############################
    # FIELDS DECLARATION
    ###############################

    ###############################
    # BUSINESS METHODS
    ###############################
    def _get_move_in_dict_of_purchase_order(self, uom_dict, product_uom_dict, owner_id, warehouse_id, product_ids):
        """
        Return the tuple with the fist is the dictionary of the Move
        """
        move_dict = {}
        move_ids = []
        purchase_location_domain = self._get_purchase_location_domain(warehouse_id)
        moves_in_todo = self._search_moves_in_of_purchase_order(purchase_location_domain, owner_id, product_ids)
        for move_item in moves_in_todo:
            move_id = move_item['id']
            product_id = move_item['product_id']

            # Convert the move quantity from the pol UoM to the standard uom of product
            move_uom_factor = uom_dict.get(move_item['product_uom'], {}).get('factor')
            product_uom_factor = uom_dict.get(product_uom_dict.get(product_id), {}).get('factor')
            if move_uom_factor and product_uom_factor:
                move_item['product_qty'] = move_item['product_qty'] / move_uom_factor * product_uom_factor
            else:
                _logger.warning("Missing the UoM factor of product %s(%s) or move %s(%s)",
                                product_id, product_uom_factor, move_id, move_uom_factor)

            move_item['quantity_done'] = 0
            move_dict[move_id] = move_item
            move_ids.append(move_id)
        self.get_quantity_done_from_move_lines(move_dict, move_ids, uom_dict, product_uom_dict)
        return move_dict

    def _search_moves_in_of_purchase_order(self, location_domain, owner_id, product_ids):
        """
        The function the return the dictionary contain the corresponding move of the Purchase order.

        :return list[dict]:`
            Ex: [{'id': 2123, 'product_id': 2131, 'product_qty': 321, 'purchase_line_id': 13224,
                 'product_uom_qty': 321, 'product_uom': 2}, ...]
        """
        self = self.sudo()
        domain_move_in = [('product_id', 'in', product_ids)] + location_domain
        if owner_id is not None:
            domain_move_in += [('restrict_partner_id', '=', owner_id)]
        domain_move_in_todo = [('purchase_line_id', '!=', None),
                               ('state', 'in', ('waiting', 'confirmed', 'assigned', 'partially_available'))] \
                              + domain_move_in

        query = self._where_calc(domain_move_in_todo)
        from_clause, where_clause, params = query.get_sql()
        query_str = """
                SELECT stock_move.id, product_id, product_qty, purchase_line_id, product_uom_qty, product_uom
                FROM {}
                WHERE {}
        """.format(from_clause, where_clause)
        self.env.cr.execute(query_str, params)
        return self.env.cr.dictfetchall()

    def get_quantity_done_from_move_lines(self, moves_dict, move_ids, uom_dict, product_uom_dict):
        if move_ids:
            self.env.cr.execute(""" 
                                SELECT id, move_id, product_uom_id, qty_done 
                                FROM stock_move_line 
                                WHERE move_id in %s""", (tuple(move_ids),))

            for line_item in self.env.cr.dictfetchall():
                move_id = line_item['move_id']
                line_id = line_item['id']
                move_item = moves_dict.get(move_id)

                if move_item:
                    # Convert the move quantity from the pol UoM to the standard uom of product
                    product_id = move_item['product_id']
                    product_uom_factor = uom_dict.get(product_uom_dict.get(product_id), {}).get('factor')
                    line_uom_factor = uom_dict.get(line_item['product_uom_id'], {}).get('factor')
                    if line_uom_factor and product_uom_factor:
                        move_item['quantity_done'] += line_item['qty_done'] / line_uom_factor * product_uom_factor
                    else:
                        _logger.warning("Missing the UoM factor of product %s(%s) and move line %s(%s)",
                                        product_id, product_uom_factor, move_id, line_uom_factor)
                else:
                    _logger.warning('Missing move %s with the line %s', move_id, line_id)

    def _get_purchase_location_domain(self, warehouse_id):
        """ The function return the domain that define the considering condition for
        the source and destination locations

        :return list[tuple]: location domain
        """
        company_id = self.env.user.company_id.id
        warehouse = self.env['stock.warehouse'].browse(warehouse_id)
        view_location_id = warehouse.view_location_id
        return [('company_id', '=', company_id),
                ('location_id.usage', '=', 'supplier'),
                ('location_dest_id.id', 'child_of', view_location_id.ids)]

    def get_move_qty_dict(self, move_ids):
        """ Function return the dictionary contain quantity move done and reserved availability quantity

        :type move_ids: list[int]
        :return:
        {
            move_id: {
                'product_uom': product_uom,
                'reserved_availability': Total of product_qty of all stock_move's lines,

            }
        }
        """
        move_qty_dict = {}
        if move_ids:

            # Step 1: Generate the dictionary contain the move quantity
            self._cr.execute("""
                            SELECT move_id, SUM(product_qty) as sum_product_qty
                            FROM stock_move_line 
                            WHERE move_id IN %s 
                            GROUP BY move_id""", (tuple(move_ids),))
            result = {data['move_id']: data['sum_product_qty'] for data in self._cr.dictfetchall()}

            # Step 2: Generate the UoM dictionary
            uom_dict = {uom.id: uom for uom in self.env['uom.uom'].search([])}

            # Step 3: Generate the dictionary stock move and list of corresponding lines
            self._cr.execute("""
                            SELECT id, move_id, product_uom_id, qty_done FROM stock_move_line WHERE move_id IN %s
                    """, (tuple(move_ids),))

            line_dict = {}
            move_dict = {}
            for line in self._cr.dictfetchall():
                line_id = line['id']
                line_dict.setdefault(line_id, line)
                move = move_dict.setdefault(line['move_id'], [])
                move.append(line_id)

            self._cr.execute("""SELECT id, product_uom, product_id FROM stock_move WHERE id in %s""",
                             (tuple(move_ids),))
            product_ids = []
            product_move_dict = {}
            for move in self._cr.dictfetchall():
                move_id = move['id']
                lines = move_dict.get(move_id, [])
                move_uom = uom_dict.get(move['product_uom'])
                quantity_done = 0
                for line_id in lines:
                    line = line_dict[line_id]
                    quantity_done += uom_dict[line['product_uom_id']]._compute_quantity(line['qty_done'], move_uom,
                                                                                        round=False)
                product_id = move['product_id']
                product_ids.append(product_id)
                product_move_dict.setdefault(product_id, []).append((move_id, move_uom))
                move_qty_dict[move_id] = {
                    'quantity_done': quantity_done,
                    'uom_id': move.get('product_uom')
                }

            self._cr.execute("""
                            SELECT pp.id as product_id, pt.uom_id 
                            FROM product_product pp 
                                JOIN product_template pt ON pp.product_tmpl_id = pt.id 
                            WHERE pp.id in %s""", (tuple(product_ids),))
            for product_id, uom_id in self._cr.fetchall():
                for move_id, move_uom in product_move_dict.get(product_id, []):
                    reserved_availability = uom_dict[uom_id]._compute_quantity(result.get(move_id, 0.0),
                                                                               move_uom,
                                                                               rounding_method='HALF-UP')
                    move_qty_dict[move_id]['reserved_availability'] = reserved_availability

        return move_qty_dict
