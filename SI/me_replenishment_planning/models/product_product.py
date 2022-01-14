# Copyright © 2021 Novobi, LLC
# See LICENSE file for full copyright and licensing details.

import logging

from odoo import api, fields, models, _
from odoo.addons import decimal_precision as dp
from odoo.tools import float_round

_logger = logging.getLogger(__name__)


class ProductProduct(models.Model):
    _inherit = 'product.product'

    ###############################
    # FIELDS DECLARATION
    ###############################
    manufacturing = fields.Boolean(
        'Manufacturing',
        compute='_compute_manufacturing', search='_search_manufacturing',
        help="True: This product have at least one BOM and can be manufactured by it\n"
             "False: This product cannot be manufacturable.")
    actual_po_perc = fields.Float(
        _('Ordered Quantity from PO (%)'),
        digits=dp.get_precision('Adjust Percentage'), required=True,
        default=lambda self: self.env.company.po_perc)
    po_perc = fields.Float(
        _('Ordered Quantity from PO (%)'),
        compute='_compute_po_perc', inverse='_inverse_po_perc',
        digits=dp.get_precision('Adjust Percentage'))

    ###############################
    # COMPUTED FUNCTIONS
    ###############################
    @api.depends_context('warehouse')
    def _compute_manufacturing(self):
        company = self.env.company
        warehouse = self.env['stock.warehouse'].browse(self._context.get('warehouse', False)) or company.default_warehouse
        for product in self:
            product.manufacturing = product.get_acceptable_boms(warehouse, company) and True or False

    @api.depends('actual_po_perc', 'manufacturing', 'purchase_ok')
    def _compute_po_perc(self):
        """
        Set default value for percentage we will order when a product is out-of-stock.
        For example, the product is:
        - Can be purchased: percentage for Purchase Order is 100%
        - Can be manufactured: percentage for Manufacturing Order is 100%.
        So percentage for Purchase Order is 0%
        - Both: 80% for MO and 20% PO
        """
        po_perc_dict = self.get_po_perc_dict()
        for product in self:
            product_id = product.id
            product.po_perc = po_perc_dict.get(product_id, 0)

    def _search_manufacturing(self, operator, value):
        if operator not in ('=', '!='):
            raise ValueError('Invalid operator: %s' % (operator,))
        if not isinstance(value, bool):
            raise ValueError('Invalid value type: %s' % (value,))

        new_operator = 'in' if (operator == '=' and value) or (
                operator == '!=' and not value) else 'not in'
        query = """
                    SELECT product_tmpl_id
                    FROM product_template
                    JOIN mrp_bom ON product_template.id = mrp_bom.product_tmpl_id
                    GROUP BY product_tmpl_id
                """
        self.env.cr.execute(query)
        product_tmpl_ids = [product_tmpl_id for product_tmpl_id in self.env.cr.fetchall()]
        return [('product_tmpl_id', new_operator, product_tmpl_ids)]

    def _inverse_po_perc(self):
        for product in self:
            product.actual_po_perc = product.po_perc

    ###############################
    # ACTION METHODS
    ###############################
    def action_open_replenishment_planning_for_product(self):
        self.ensure_one()
        action = self.env.ref('me_replenishment_planning.action_replenishment_planning', raise_if_not_found=False).read()[0]
        context = self._context.copy()
        context.update({
            'model': 'report.replenishment_planning_report',
            'product_ids': self.ids,
            'warehouse_id': self.env['report.replenishment_planning_report'].get_default_warehouse().id,
        })
        action['context'] = context
        return action

    ###############################
    # BUSINESS METHODS
    ###############################
    def get_acceptable_boms(self, warehouse, company):
        self.ensure_one()
        boms = self.bom_ids.filtered(lambda bom:
               (not bom.company_id or bom.company_id == company) and bom.type == 'normal' and\
               (not bom.picking_type_id or bom.picking_type_id == warehouse.manu_type_id))
        return boms

    def get_po_perc_dict(self):
        """
        Set default value for percentage we will order when a product is out-of-stock.
        For example, the product is:
        - Can be purchased: percentage for Purchase Order is 100%
        - Can be manufactured: percentage for Manufacturing Order is 100%.
        So percentage for Purchase Order is 0%
        - Both: 80% for MO and 20% PO (as default)
        :rtype: dict
        """
        po_perc_dict = {}
        for product in self:
            if product.manufacturing and product.purchase_ok:
                po_perc = product.actual_po_perc
            elif product.manufacturing:
                po_perc = 0
            else:
                po_perc = 100
            po_perc_dict[product.id] = po_perc
        return po_perc_dict

    def get_product_uom_dict(self):
        """NEED TO IMPROVE"""
        product_uom_dict = {}
        if self:
            query = """
                SELECT pp.id, pt.uom_id
                FROM product_product pp
                    JOIN product_template pt
                        ON pp.product_tmpl_id = pt.id
                WHERE pp.id in %s"""
            self._cr.execute(query, (tuple(self.ids),))
            for product_uom in self._cr.dictfetchall():
                product_uom_dict[product_uom['id']] = product_uom['uom_id']
        return product_uom_dict

    def get_actual_available_qty_dict(self):
        actual_available_qty_dict = {}
        for product in self:
            actual_available_qty_dict[product.id] = product.free_qty
        return actual_available_qty_dict

    def get_rfq_qty_dict(self):
        """
        Get the RFQ quantity form the Purchase Orders that have state in ('draft', 'sent', 'to approve')
        :return: {'rfq_qty': 0.0, 'rfq_ids': PurchaseOrderLine}
        """
        rfq_qty_dict = {}
        if self:
            uom_dict = self.env['uom.uom'].get_uom_dict()
            product_uom_dict = self.get_product_uom_dict()
            warehouse = self.env['stock.warehouse'].browse(self._context.get('warehouse', False)) or self.env.company.default_warehouse
            in_type_id = warehouse.in_type_id
            self._cr.execute("""
                            SELECT l.id, l.product_id, l.product_qty, l.product_uom
                            FROM purchase_order_line l
                            LEFT JOIN purchase_order p ON l.order_id = p.id
                            WHERE l.product_id IN %s AND 
                                  l.state IN ('draft', 'sent', 'to approve') AND 
                                  p.picking_type_id = %s""", (tuple(self.ids), in_type_id.id))
            for po_line in self._cr.dictfetchall():
                product_id = po_line['product_id']
                pol_id = po_line['id']

                # Convert the pol quantity from the pol UoM to the standard uom of product
                product_uom_id = product_uom_dict.get(product_id)
                product_uom_factor = uom_dict.get(product_uom_id, {}).get('factor')
                line_uom_factor = uom_dict.get(po_line['product_uom'], {}).get('factor')
                pol_product_qty = po_line['product_qty']
                if product_uom_factor and line_uom_factor:
                    pol_product_qty = pol_product_qty / line_uom_factor * product_uom_factor
                else:
                    _logger.warning("Missing the UoM factor of product %s(%s) or POL %s(%s)",
                                    product_id, product_uom_factor, pol_id, line_uom_factor)

                rfq_item = rfq_qty_dict.setdefault(product_id, dict(rfq_qty=0.0, pol_ids=[]))
                rfq_item['rfq_qty'] += pol_product_qty
                rfq_item['pol_ids'].append(pol_id)

        return rfq_qty_dict

    def get_active_receive_qty_dict(self):
        will_receive_qty_dict = self._compute_will_receive_qty_dict(
            owner_id=self._context.get('owner_id'), warehouse_id=self._context.get('warehouse'))
        receive_qty_dict = {}
        for product in self:
            product_id = product.id
            product_data = will_receive_qty_dict.get(product_id, {})
            receive_qty_dict[product_id] = {
                'receive_qty': product_data.get('will_receive_qty', 0.0),
                'active_po_lines': product_data.get('active_po_lines', [])
            }
        return receive_qty_dict

    def _compute_will_receive_qty_dict(self, owner_id, warehouse_id):
        product_ids = self.ids
        uom_dict = self.env['uom.uom'].get_uom_dict()
        product_uom_dict = self.get_product_uom_dict()
        move_dict = self.env['stock.move']._get_move_in_dict_of_purchase_order(uom_dict, product_uom_dict, owner_id, warehouse_id, product_ids)
        moves_in_dict = {}
        for move_id, move in move_dict.items():
            product_id = move.get('product_id')
            purchase_line_id = move.get('purchase_line_id')
            product_qty = move.get('product_qty', 0.0)
            quantity_done = move.get('quantity_done', 0.0)

            moves_in_item = moves_in_dict.setdefault(product_id, dict(will_receive_qty=0.0, active_po_lines=[]))
            moves_in_item['will_receive_qty'] += product_qty - quantity_done
            moves_in_item['active_po_lines'].append(purchase_line_id)

        return moves_in_dict

    def get_active_mrp_qty_dict(self):
        """ The function return the dictionary contain the open MO information of each products in product_variants
        """
        open_mo_info_dict = {}
        will_mrp_qty_dict = self._compute_will_mrp_qty_dict(
            owner_id=self._context.get('owner_id', None), warehouse_id=self._context.get('warehouse'))
        for product in self:
            product_id = product.id
            product_data = will_mrp_qty_dict.get(product_id, {})
            open_mo_info_item = open_mo_info_dict.setdefault(product_id, {})
            if product_data:
                open_mo_info_item.update({
                    'reserved_mo_qty': product_data['be_reserved_qty'],
                    'open_mo_qty': product_data['will_receive_qty'],
                    'open_mo': product_data['open_mo']
                })

            else:
                open_mo_info_item.update({
                    'reserved_mo_qty': 0,
                    'open_mo_qty': 0,
                    'open_mo': None
                })
        return open_mo_info_dict

    def _compute_will_mrp_qty_dict(self, owner_id, warehouse_id):
        res = {}
        move_env = self.env['stock.move']
        _, domain_move_in_loc, domain_move_out_loc = self._get_domain_locations()

        product_ids = self.ids
        # self = self.sudo()
        if product_ids:
            domain_move_in = [('product_id', 'in', product_ids)] + domain_move_in_loc
            domain_move_out = domain_move_out_loc
            if owner_id is not None:
                domain_move_in += [('restrict_partner_id', '=', owner_id)]
                domain_move_out += [('restrict_partner_id', '=', owner_id)]

            # Step 1: Find the open move in for finish goods
            domain_move_in_todo = [('production_id', '!=', None),
                                   ('production_id.state', 'in', ('draft', 'confirmed', 'planned', 'progress')),
                                   ('state', 'in', ('draft', 'waiting', 'confirmed', 'assigned', 'partially_available'))] \
                                  + domain_move_in
            finish_good_move = move_env.search_read(domain_move_in_todo, ['id', 'product_id', 'product_qty', 'production_id', 'date'])
            production_ids = [i['production_id'][0] for i in finish_good_move]
            move_in_ids = [i['id'] for i in finish_good_move]
            qty_done_dict = move_env.get_move_qty_dict(move_in_ids)
            move_in_qty_dict = {i['production_id'][0]: {
                'product_qty': i['product_qty'],
                'quantity_done': qty_done_dict[i['id']],
                'date': i['date'],
            } for i in finish_good_move}

            # Step 2: Find the corresponding move out for the materials
            domain_move_out_todo = [('raw_material_production_id', 'in', production_ids), ('scrapped', '=', False)]
            query = move_env._where_calc(domain_move_out_todo)
            from_clause, where_clause, params = query.get_sql()
            query_str = """
                SELECT stock_move.id, product_id, raw_material_production_id
                FROM {}
                WHERE {}
            """.format(from_clause, where_clause)
            self.env.cr.execute(query_str, params)
            materials_moves = list(self._cr.dictfetchall())
            move_out_ids = [move['id'] for move in materials_moves]
            # The product_qty and quantity_done is in the stock_move's UoM
            move_out_qty_dict = move_env.get_move_qty_dict(move_out_ids)

            # Step 3: Create a dictionary with the format:
            # {
            #   production_id: {
            #       'bom_id': bom_id,
            #       'material': {
            #           pid_1: {
            #               'reserved_availability': 123
            #           }
            #       },
            #       'fg_id': 1
            #   }
            # }
            production_dict = {}
            for m in materials_moves:
                move_qty = move_out_qty_dict[m['id']]
                production_id = m['raw_material_production_id']
                production_item = production_dict.setdefault(production_id, {})
                if not production_item:
                    production_item['material'] = {}
                material_info = production_item['material'].setdefault(m['product_id'], {'reserved_availability': 0})
                material_info['reserved_availability'] = material_info['reserved_availability'] + move_qty['reserved_availability']

            # Step 4: embed production information to the production_dict
            product_mo_dict = {}
            if production_ids:
                productsions = self.env['mrp.production'].browse(production_ids)
                for p in productsions:
                    production_item = production_dict.setdefault(p.id, {})
                    production_item.setdefault('material', {})
                    production_item['bom_id'] = p.bom_id.id

                    product_id = p.product_id.id
                    production_item['fg_id'] = product_id
                    production_item['product_qty'] = p.product_qty

                    product_mo_dict[p.id] = p

            # Step 5:
            product_bom_dict = self.env['mrp.bom'].build_bom_dict(self)
            for production_id, value in production_dict.items():
                # The production information
                material_qty_dict = value['material']

                fg_id = value['fg_id']
                product_qty = value['product_qty']
                if fg_id in product_ids:
                    fg_item = res.setdefault(fg_id, {
                        'be_reserved_qty': 0,
                        'will_receive_qty': 0,
                        'open_mo': None
                    })

                    open_mo_item = fg_item['open_mo']
                    if open_mo_item:
                        fg_item['open_mo'] = fg_item['open_mo'] + product_mo_dict.get(production_id)
                    else:
                        fg_item['open_mo'] = product_mo_dict.get(production_id)

                    # just get the BOM Information
                    bom_id = value['bom_id']
                    bom = product_bom_dict.get(bom_id, {})

                    # get maximum reserved_fg_qty base on requested qty of the finish good in move in section
                    # fg_id = value['fg_id']
                    move_in_fg_info = move_in_qty_dict.get(production_id)
                    reserved_fg_qty = move_in_fg_info['product_qty']

                    try:
                        if bom:
                            # Loop each component in BOM structure and find the minimum reserved qty
                            bom_materials = bom.get('materials')
                            for material_id, material_data in bom_materials.items():
                                line = material_data['line']
                                product_line = material_data['product_line']
                                if line['product_qty'] and product_line['active']:
                                    material_qty = material_qty_dict.get(material_id, {}).get('reserved_availability', 0) \
                                                   / material_data['qty']

                                    # The number of BOM user requested
                                    reserved_fg_qty = min(reserved_fg_qty, material_qty)

                            # Update res
                            fg_qty_dict = bom.get('finish_good')
                            be_reserved_qty = fg_item['be_reserved_qty'] + reserved_fg_qty * fg_qty_dict['qty']
                            will_receive_qty = fg_item['will_receive_qty'] + product_qty
                            rounding = fg_qty_dict['finish_uom_rounding']

                            fg_item['be_reserved_qty'] = float_round(be_reserved_qty, precision_rounding=rounding)
                            fg_item['will_receive_qty'] = float_round(will_receive_qty, precision_rounding=rounding)

                        else:
                            rounding = 1.0
                            fg_item['be_reserved_qty'] = float_round(fg_item['be_reserved_qty'] + product_qty, precision_rounding=rounding)
                            fg_item['will_receive_qty'] = float_round(fg_item['will_receive_qty'] + product_qty, precision_rounding=rounding)

                    except ValueError:
                        continue

        return res

    def get_lacking_material_quantity_dict(self):
        """
            Return the quantity need in open MOs to produce other product using this product as material

        :return: dict((int, int), int) lacking_material_dict, dict(int, int) total_lacking_material_dict
            lacking_material_dict: {(material_product_id, produced_product_id): lacking_quantity}
            total_lacking_material_dict: {material_product_id: total_lacking_material}
        """
        lacking_material_dict, total_lacking_material_dict = {}, {}
        company = self.env.company
        warehouse = self.env['stock.warehouse'].browse(self._context.get('warehouse', False)) or company.default_warehouse

        product_ids = self.ids
        if product_ids:
            mo_ids, bom_ids, mo_dict = self.get_manufacturing_order_data(warehouse, company)
            move_ids, move_dict, lacking_material_dict = self.get_material_todo_move_data(mo_ids, mo_dict, product_ids)

            uom_dict = self.env['uom.uom'].get_uom_dict()
            product_uom_dict = self.get_product_uom_dict()

            if move_ids:
                self.env.cr.execute(""" 
                    SELECT move_id, id line_id, product_id, product_uom_id, product_qty 
                    FROM stock_move_line 
                    WHERE move_id in %s
                """, (tuple(move_ids),))

                for line in self.env.cr.dictfetchall():
                    move_id = line.get('move_id')
                    line_id = line.get('line_id')

                    move_item = move_dict.setdefault(move_id, {})
                    if move_item:
                        produced_product_id = move_item['produced_product_id']
                        material_product_id = move_item['material_product_id']
                        lacking_material = lacking_material_dict.setdefault((material_product_id, produced_product_id), 0)

                        line_uom_factor = uom_dict.get(line['product_uom_id'], {}).get('factor')
                        product_uom_id = product_uom_dict.get(material_product_id)
                        product_uom_factor = uom_dict.get(product_uom_id, {}).get('factor')
                        if line_uom_factor and product_uom_factor:
                            lacking_quantity = line['product_qty'] / line_uom_factor * product_uom_factor
                            lacking_material -= lacking_quantity
                            lacking_material_dict[(material_product_id, produced_product_id)] = lacking_material if lacking_material > 0 else 0
                        else:
                            _logger.warning("Missing the UoM factor of product %s(%s) and line %s(%s)",
                                            material_product_id, product_uom_factor, move_id, line_uom_factor)
                    else:
                        _logger.warning('Missing move %s with the line %s', move_id, line_id)

            total_lacking_material_dict = {}
            for lacking_item in lacking_material_dict.items():
                product_id = lacking_item[0][0]
                total_lacking_material = total_lacking_material_dict.setdefault(product_id, 0)
                total_lacking_material += lacking_item[1]
                total_lacking_material_dict[product_id] = total_lacking_material

        return lacking_material_dict, total_lacking_material_dict

    def get_manufacturing_order_data(self, warehouse, company):
        bom_ids = mo_ids = []
        mo_dict = {}
        self._cr.execute("""
                    SELECT id, product_id, bom_id 
                    FROM mrp_production
                    WHERE state NOT IN ('done', 'cancel')
                      AND company_id = %(company_id)s
                      AND picking_type_id = %(manu_type_id)s
                """, dict(company_id=company.id, manu_type_id=warehouse.manu_type_id.id))
        for line in self._cr.dictfetchall():
            mo_item = mo_dict.setdefault(line.get('id'), {})
            mo_item['produced_product_id'] = line.get('product_id')
            mo_item['bom_id'] = line.get('bom_id')

            mo_ids.append(line.get('id'))
            bom_ids.append(line.get('bom_id'))

        return mo_ids, bom_ids, mo_dict

    def get_material_todo_move_data(self, mo_ids, mo_dict, product_ids):
        """
        :return: list[int] move_ids, dict move_dict, dict lacking_material_dict
            move_dict:{ move_id: {material_product_id: stock_move.product_id,
                        produced_product_id: mo_item['produced_product_id'] }}
            lacking_material_dict: {(material_product_id, produced_product_id): lacking_quantity}
        """
        move_ids = []
        move_dict = {}
        lacking_material_dict = {}

        if mo_ids and product_ids:
            self._cr.execute("""
                        SELECT id move_id, raw_material_production_id mo_id, product_id, product_uom_qty
                        FROM stock_move
                        WHERE state NOT IN ('assigned', 'done', 'cancel')
                          AND raw_material_production_id IN %(raw_material_production_ids)s
                          AND product_id IN %(product_ids)s
                    """, dict(raw_material_production_ids=tuple(mo_ids), product_ids=tuple(product_ids)))

            for line in self._cr.dictfetchall():
                move_id = line.get('move_id')
                material_product_id = line.get('product_id')
                mo_item = mo_dict.setdefault(line.get('mo_id'))
                if mo_item:
                    produced_product_id = mo_item['produced_product_id']
                    move_ids.append(move_id)

                    move_item = move_dict.setdefault(move_id, {})
                    move_item['produced_product_id'] = produced_product_id
                    move_item['material_product_id'] = material_product_id

                    lacking_material = lacking_material_dict.setdefault((material_product_id, produced_product_id), 0)
                    lacking_material += line.get('product_uom_qty')
                    lacking_material_dict[(material_product_id, produced_product_id)] = lacking_material

        return move_ids, move_dict, lacking_material_dict

    def _get_product_uom_of_purchase(self, product_ids=None):
        """
        Get the factor of unit of measure of products used to create Purchase Order
        :param product_ids: List of product id to get the factor
        :type product_ids: List[int]
        :return:
        {
            <product_id>: {
                'uom_id': <int>,
                'factor': <float>
            },
            ...
        }
        :rtype: dict
        """
        result = {}
        if product_ids:
            sql_query = """
                select 
                    pp.id as product_id,
                    pt.id as template_id,
                    product_uom.id as product_uom_id,
                    product_uom.factor as product_uom_factor,
                    purchase_uom.id as purchase_uom_id,
                    purchase_uom.factor as purchase_uom_factor
                from product_product pp
                join product_template pt on pp.product_tmpl_id = pt.id
                join uom_uom product_uom on product_uom.id = pt.uom_id
                join uom_uom purchase_uom on purchase_uom.id = pt.uom_po_id
                where pp.id in %s;
            """
            sql_params = (tuple(product_ids),)
            self.env.cr.execute(sql_query, sql_params)
            records = self.env.cr.dictfetchall()
            for item in records:
                result[item.get('product_id')] = item

        return result

    def _get_product_uom_of_manufacture(self, product_ids=None):
        """
        Get the factor of unit of measure of products used to create Manufacturing Order
        :param product_ids: List of product id to get the factor
        :type product_ids: List[int]
        :return:
        {
            <product_id>: {
                'uom_id': <int>,
                'factor': <float>
            },
            ...
        }
        :rtype: dict
        """
        result = {}
        if product_ids:
            sql_query = """
                select 
                    pp.id as product_id,
                    pt.id as template_id,
                    product_uom.id as product_uom_id,
                    product_uom.factor as product_uom_factor,
                    mrp_bom.id as bom_id,
                    bom_uom.id as bom_uom_id,
                    bom_uom.factor as bom_uom_factor
                from product_product pp
                join product_template pt on pp.product_tmpl_id = pt.id
                join uom_uom product_uom on pt.uom_id = product_uom.id
                join mrp_bom on (mrp_bom.product_id = pp.id) or (mrp_bom.product_tmpl_id = pt.id and mrp_bom.product_id is NULL)
                join uom_uom bom_uom on mrp_bom.product_uom_id = bom_uom.id
                where 
                    pp.id in %s and mrp_bom.active is TRUE;
            """
            sql_params = (tuple(product_ids),)
            self.env.cr.execute(sql_query, sql_params)
            records = self.env.cr.dictfetchall()
            for item in records:
                result[item.get('product_id')] = item

        return result

    def _get_product_uom(self, product_ids=None):
        """
        Get the factor of unit of measure of products
        :param product_ids: List of product id to get the factor
        :type product_ids: List[int]
        :return:
        {
            <product_id>: {
                'uom_id': <int>,
                'factor': <float>
            },
            ...
        }
        :rtype: dict
        """
        result = {}
        if product_ids:
            sql_query = """
                select
                    pp.id as product_id,
                    pt.id as template_id,
                    pt.uom_id,
                    uu.factor
                from product_product pp
                join product_template pt on pp.product_tmpl_id = pt.id
                join uom_uom uu on uu.id = pt.uom_id
                where pp.id in %s;
            """
            sql_params = (tuple(product_ids),)
            self.env.cr.execute(sql_query, sql_params)
            records = self.env.cr.dictfetchall()
            for item in records:
                result[item.get('product_id')] = item

        return result

    ###############################
    # HELPER METHODS
    ###############################

    def with_company(self, company):
        """ with_company(company)

        Return a new version of this recordset with a modified context, such that::

            result.env.company = company
            result.env.companies = self.env.companies | company

        :param company: main company of the new environment.
        :type company: :class:`~odoo.addons.base.models.res_company` or int

        .. warning::

            When using an unauthorized company for current user,
            accessing the company(ies) on the environment may trigger
            an AccessError if not done in a sudoed environment.
        """
        if not company:
            # With company = None/False/0/[]/empty recordset: keep current environment
            return self

        company_id = int(company)
        allowed_company_ids = self.env.context.get('allowed_company_ids', [])
        if allowed_company_ids and company_id == allowed_company_ids[0]:
            return self
        # Copy the allowed_company_ids list
        # to avoid modifying the context of the current environment.
        allowed_company_ids = list(allowed_company_ids)
        if company_id in allowed_company_ids:
            allowed_company_ids.remove(company_id)
        allowed_company_ids.insert(0, company_id)

        return self.with_context(allowed_company_ids=allowed_company_ids)
