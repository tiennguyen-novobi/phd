# Copyright © 2021 Novobi, LLC
# See LICENSE file for full copyright and licensing details.

import logging

from odoo import api, fields, models, _

_logger = logging.getLogger(__name__)


class ReplenishmentPlanningReport(models.AbstractModel):
    _name = 'report.replenishment_planning_report'
    _description = 'Replenishment Planning Report'

    @api.model
    def get_html(self, product_ids=False, warehouse_id=False, append_content=False):
        """
        Get the html to render the Replenishment Planning Report
        """
        res = {}
        company = self.env.user.company_id
        is_multi_wh = company.user_has_groups("stock.group_stock_multi_warehouses")
        if product_ids:
            res = self._get_report_data(product_ids, warehouse_id)

        values = dict(data=res.get('lines', False), is_multi_wh=is_multi_wh)
        if append_content:
            res['extend_lines'] = self.env.ref('me_replenishment_planning.report_replenishment_planning_line').render(values)
            res['lines'] = False
        else:
            res['lines'] = self.env.ref('me_replenishment_planning.report_replenishment_planning').render(values)
            res['extend_lines'] = False
        return res

    @api.model
    def _get_report_data(self, product_ids, warehouse_id):
        precision_env = self.env['decimal.precision']
        bom_env = self.env['mrp.bom']
        bom_line_env = self.env['mrp.bom.line']
        product_env = self.env['product.product']
        warehouse_env = self.env['stock.warehouse']
        qty_precision = precision_env.precision_get('Product Unit of Measure')
        percentage_precision = precision_env.precision_get('Adjust Percentage')

        company = self.env.company
        warehouse = warehouse_env.browse(warehouse_id) or self.get_default_warehouse()
        products_info_dict = self._context.get('product_info', {})

        lines = []
        products = product_ids and product_env.browse(product_ids) or []
        for product in products:
            product_data = products_info_dict.get(str(product.id), {})

            # If there's no requested_quantity in the product info context,
            # get the reordering rule value as requested quantity
            requested_quantity = product_data.get('requested_quantity', -1)
            if requested_quantity < 0:
                requested_quantity = self.get_default_requested_quantity(product, warehouse)

            boms = product.get_acceptable_boms(warehouse, company)
            default_bom = self.get_default_bom(boms)
            lines += (self._get_bom(
                warehouse=warehouse,
                bom_id=default_bom and default_bom.id or False,
                product_id=product.id,
                requested_quantity=requested_quantity,
                level=0,
                bom_ids=boms and boms.ids or False,
                qty_precision=qty_precision,
                percentage_precision=percentage_precision,
                is_root=True,
                bom_env=bom_env,
                bom_line_env=bom_line_env,
                product_env=product_env,
            ))
        self._update_product_info(lines, warehouse)
        return {
            'lines': lines,
        }

    def _get_bom(self, warehouse=False, bom_id=False, product_id=False, requested_quantity=0, line_id=False, level=0,
                 bom_ids=False, qty_precision=None, percentage_precision=None, is_root=False, bom_env=None,
                 bom_line_env=None, product_env=None):
        # Initial the value for the missing parameter
        precision_env = self.env['decimal.precision']
        bom_env = bom_env or self.env['mrp.bom']
        bom_line_env = bom_line_env or self.env['mrp.bom.line']
        product_env = product_env or self.env['product.product']

        qty_precision = qty_precision is None and precision_env.precision_get('Product Unit of Measure') or qty_precision
        percentage_precision = percentage_precision is None and precision_env.precision_get('Adjust Percentage') or percentage_precision
        bom = bom_env.browse(bom_id)
        requested_quantity = requested_quantity or 0.0

        if line_id and line_id > 0:
            current_line = bom_line_env.browse(int(line_id))
            requested_quantity = current_line.product_uom_id._compute_quantity(requested_quantity, bom.product_uom_id)

        # Display bom components for current selected product variant
        if product_id:
            product = product_env.browse(int(product_id))
        elif bom:
            product = bom.product_id or bom.product_tmpl_id.product_variant_id

        allow_adjust_po_perc = product.manufacturing and product.purchase_ok
        po_perc = product.po_perc


        lines = {
            'is_root': is_root,
            'bom': bom,
            'boms_info': bom_env.browse(bom_ids),
            'product': product,
            'prod_description': product.name,
            'required_qty': requested_quantity,
            'allow_adjust_po_perc': allow_adjust_po_perc,
            'po_perc': po_perc,
            'warehouse_id': warehouse.id,
            'warehouse_name': warehouse.name,
            'level': level or 0,
            'qty_precision': qty_precision,
            'percentage_precision': percentage_precision,
        }

        components = self._get_bom_lines(warehouse=warehouse,
                                         bom=bom,
                                         requested_quantity=requested_quantity,
                                         level=level + 1,
                                         bom_env=bom_env,
                                         qty_precision=qty_precision,
                                         percentage_precision=percentage_precision)

        return [lines] + components

    def _get_bom_lines(self, warehouse, bom, requested_quantity, level,
                       bom_env=None, qty_precision=None, percentage_precision=None):
        # If there's no BoM, return
        if not bom:
            return []

        precision_env = self.env['decimal.precision']
        product_env = self.env['product.product']
        bom_env = bom_env or self.env['mrp.bom']
        qty_precision = qty_precision is None and precision_env.precision_get('Product Unit of Measure') or qty_precision
        percentage_precision = percentage_precision is None and precision_env.precision_get('Adjust Percentage') or percentage_precision
        company = self.env.company

        components = []
        for line in bom.bom_line_ids:
            required_qty = (requested_quantity / (bom.product_qty or 1.0)) * line.product_qty

            # The material factor -> use to calculate the line_qty in the update_product_info function
            line_std_qty = line.product_qty / line.product_uom_id.factor

            material = line.product_id
            boms_child_info = material.get_acceptable_boms(warehouse, company)
            child_bom = self.get_default_bom(boms_child_info)

            allow_adjust_po_perc = material.manufacturing and material.purchase_ok
            po_perc = material.po_perc

            components.append({
                'is_root': False,
                'bom': child_bom,
                'required_qty': required_qty,
                'product': material,
                'allow_adjust_po_perc': allow_adjust_po_perc,
                'prod_description': material.name,
                'parent_id': bom.id,
                'line_id': line.id,
                'line_std_qty': line_std_qty,
                'level': level or 0,
                'boms_info': boms_child_info or False,
                'qty_precision': qty_precision,
                'percentage_precision': percentage_precision,
                'hide': level >= 2,
                'po_perc': po_perc,
                'warehouse_id': warehouse.id,
                'warehouse_name': warehouse.name
            })

            sub_components = self._get_bom_lines(warehouse=warehouse,
                                                 bom=child_bom,
                                                 requested_quantity=required_qty,
                                                 level=level + 1,
                                                 bom_env=bom_env,
                                                 qty_precision=qty_precision,
                                                 percentage_precision=percentage_precision)

            components += sub_components

        return components

    @api.model
    def get_child_bom(self, warehouse_id=None, parent_product_id=-1, bom_id=False, product_id=False,
                      requested_quantity=False, line_id=False, level=False,  bom_ids=False, parent_bom_id=False, is_root=False):
        """
        Function return components in BOM structure when change the BOM on the selection field
        """
        warehouse = self.env['stock.warehouse'].browse(warehouse_id) or self.get_default_warehouse()
        components = self._get_bom(
            warehouse=warehouse,
            bom_id=bom_id,
            product_id=product_id,
            requested_quantity=requested_quantity,
            line_id=line_id,
            level=level,
            bom_ids=bom_ids,
            is_root=is_root,
        )

        self._update_product_info(components, warehouse, parent_product_id)

        company = self.env.user.company_id
        is_multi_wh = company.user_has_groups("stock.group_stock_multi_warehouses")

        if components:
            components[0].update({
                'parent_id': parent_bom_id,
                'line_id': line_id,
            })

        return self.env.ref('me_replenishment_planning.report_replenishment_planning_line')\
            .render({
                'data': components,
                'is_multi_wh': is_multi_wh
            })

    def _update_product_info(self, data, warehouse, parent_product_id=-1):
        products = self.env['product.product']
        for line in data:
            products |= line['product']
        products = products.with_context(warehouse=warehouse.id)

        actual_available_qty_dict = products.get_actual_available_qty_dict()
        rfq_qty_dict = products.get_rfq_qty_dict()
        receive_qty_dict = products.get_active_receive_qty_dict()
        open_mo_info_dict = products.get_active_mrp_qty_dict()
        po_perc_dict = products.get_po_perc_dict()
        uom_dict = self.env['uom.uom'].get_uom_dict()
        product_uom_dict = products.get_product_uom_dict()
        lacking_quantity_dict, total_lacking_material_dict = products.get_lacking_material_quantity_dict()

        level_stack = [0]
        parent_product_id_stack = [parent_product_id]

        for line in data:
            product_id = line['product'].id

            line['qty_available'] = actual_available_qty_dict.get(product_id, 0)
            line['open_po'] = rfq_qty_dict.get(product_id, {}).get('rfq_qty', 0) + \
                              receive_qty_dict.get(product_id, {}).get('receive_qty', 0)
            line['open_mo'] = open_mo_info_dict.get(product_id, {}).get('open_mo_qty', 0)
            line['po_perc'] = po_perc_dict.get(product_id) or 0

            product_uom = uom_dict.get(product_uom_dict.get(product_id))
            line['precision_rounding'] = product_uom['rounding']
            line_qty = 1
            if line.get('line_id') and line.get('line_std_qty'):
                line_qty = line.get('line_std_qty') * product_uom['factor']
            line['line_qty'] = line_qty

            bom = line['bom']
            line['bom_qty'] = bom.product_qty / bom.product_uom_id.factor * product_uom['factor'] if bom else 1

            # Get lacking quantity from lacking_quantity_dict using Stack
            while level_stack and level_stack[len(level_stack) - 1] >= line.get('level', 0):
                level_stack.pop()
                parent_product_id_stack.pop()
            parent_product_id = parent_product_id_stack[len(parent_product_id_stack) - 1] \
                if parent_product_id_stack \
                else 0
            level_stack.append(line.get('level', -1))
            parent_product_id_stack.append(line.get('product').id)

            line['lacking_quantity'] = lacking_quantity_dict.setdefault((product_id, parent_product_id), 0)
            line['total_lacking_quantity'] = total_lacking_material_dict.get(product_id, 0)

            active_productions = open_mo_info_dict.get(product_id, {}).get('open_mo', False)
            active_pol_ids = rfq_qty_dict.get(product_id, {}).get('pol_ids', []) + \
                             receive_qty_dict.get(product_id, {}).get('active_po_lines', [])
            detail_transactions = self._create_detail_transactions(active_pol_ids, active_productions)
            line['detail_transaction_ids'] = detail_transactions.ids


    ###############################
    # HELPER FUNCTIONS
    ###############################
    def get_default_warehouse_id(self):
        return self.get_default_warehouse().id

    def get_default_warehouse(self):
        """
        Get the default warehouse when opening the Replenishment Planning Report.
        """
        company = self.env.company
        if company.default_warehouse:
            default_warehouse = company.default_warehouse
        else:
            default_warehouse = self.env["stock.warehouse"].search([('company_id', '=', company.id)], limit=1)

        return default_warehouse

    def get_default_bom(self, boms):
        default_bom = self.env['mrp.bom']
        for bom in boms:
            if not default_bom:
                default_bom = bom
            # get the BOM has smallest sequence and biggest id
            elif default_bom.sequence > bom.sequence or (default_bom.sequence == default_bom.sequence and default_bom.id < bom.id):
                default_bom = bom
        return default_bom

    def get_default_requested_quantity(self, product, warehouse):
        """
        Get the default value of the Requested Quantity in the Replenishment Planning Report:
            Requested Quantity = Max Qty in the Reordering Rules (if existed)
        """
        default_requested_qty = 0
        if product and warehouse:
            # If there's any reordering rule, get the product_max_qty
            reordering_rule = self.env['stock.warehouse.orderpoint'].search([
                ('product_id', '=', product.id),
                ('warehouse_id', '=', warehouse.id)
            ], limit=1)
            if reordering_rule:
                default_requested_qty = reordering_rule.product_max_qty
        return default_requested_qty

    def _create_detail_transactions(self, active_pol_ids, active_productions):
        detail_vals = []
        if active_productions:
            for production in active_productions:
                detail_vals.append({
                    'production_id': production.id,
                    'product_qty': production.product_qty,
                    'date_to_complete': production.date_planned_finished or False,
                })
        if active_pol_ids:
            active_pols = self.env['purchase.order.line'].browse(active_pol_ids)
            for pol in active_pols:
                detail_vals.append({
                    'purchase_order_id': pol.order_id.id,
                    'product_qty': pol.product_qty,
                    'date_to_complete': pol.date_planned or False,
                })

        detail_transactions = self.env['detail.transaction'].create(detail_vals)
        return detail_transactions
