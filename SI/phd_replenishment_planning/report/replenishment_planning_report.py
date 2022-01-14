# Copyright © 2021 Novobi, LLC
# See LICENSE file for full copyright and licensing details.

import logging
from odoo import api, fields, models, _
from pytz import timezone
from datetime import datetime
from dateutil.relativedelta import relativedelta
from random import choice
from string import ascii_letters

_logger = logging.getLogger(__name__)


class ReplenishmentPlanningReport(models.AbstractModel):
    _inherit = 'report.replenishment_planning_report'

    @api.model
    def _get_report_data(self, product_ids, warehouse_id):
        res = super()._get_report_data(product_ids, warehouse_id)
        self._update_raw_response(res, res.get('lines', []))
        return res

    @api.model
    def _update_raw_response(self, res, lines):
        res['raw'] = []
        for line in lines:
            self._update_raw_response_line(res, line)

    @api.model
    def _update_raw_response_line(self, res, line):
        res['raw'].append(
            {
                'key': line.get('key'),
                'product_id': line.get('product').id,
                'parent_id': line.get('parent_id', -1),
                'vendor_domain': line.get('vendor'),
                'bom_domain': line.get('bom_domain'),
                'default_bom_id': line.get('bom').id,
                'default_bom_name': line.get('bom').display_name
            }
        )

    def _update_product_info(self, data, warehouse, parent_product_id=-1):
        super()._update_product_info(data, warehouse, parent_product_id)
        self._update_product_info_from_stock_status(data)

    def _update_product_info_from_stock_status(self, data):
        currency = self.env.company.currency_id.name or 'USD'
        extend_key = {
            'forecasted_date': False,
            'free_qty': False,
            'product_cost': 0,
            'currency': currency,
        }
        start_date = datetime.now(timezone(self.env.user.tz or 'UTC')).date()
        product_ids = tuple(map(lambda rec: rec.get('product') and rec['product'].id or -1, data))
        stock_status_fields = ['product_id', 'forecasted_date']
        stock_status_lines = self.env['stock.status.report.line'].search_read([('product_id', 'in', product_ids)],
                                                                              stock_status_fields)
        stock_status_lines_dict = {line['product_id'][0]: line for line in stock_status_lines}
        products = self.env['product.product'].search_read([('id', 'in', product_ids)],
                                                           ['free_qty', 'qty_available', 'standard_price'])
        products_dict = {line['id']: line for line in products}
        group_unique = f"{str(datetime.now().microsecond)}-{''.join([choice(ascii_letters) for _ in range(5)])}"

        for index in range(len(data)):
            data[index].update(extend_key)
            is_root = data[index]['is_root']
            product_id = data[index]['product'].id
            stock_status_line = stock_status_lines_dict.get(product_id, False)
            product_line = products_dict.get(product_id, False)
            forcasted_date = stock_status_line and ('forecasted_date' in stock_status_line) and stock_status_line[
                'forecasted_date'].strftime("%m/%d/%Y") or '01/01/0001'
            end_date = datetime.strptime(forcasted_date, "%m/%d/%Y").date()
            if stock_status_line and is_root:
                    data[index]['forecasted_date'] = forcasted_date
            if product_line:
                data[index]['free_qty'] = product_line.get('free_qty', 0)
                data[index]['product_cost'] = product_line.get('standard_price', 0)
                data[index]['vendor'] = self._get_vendor_domain(data[index]['product'], data[index]['bom'])
                data[index]['bom_domain'] = self._get_bom_domain(data[index]['boms_info'])
                data[index]['qty_available'] = product_line.get('qty_available', 0)
                data[index]['key'] = f"{index}{group_unique}"
            data[index]['open_po'] = self.env['stock.status.report.line'].calculate_incoming_qty(product_id, start_date,
                                                                                                 end_date)
            active_pol_vals = self.env['stock.status.report.line'].calculate_incoming_data(product_id, start_date,
                                                                                           end_date, catch='both')
            detail_transactions = self._create_detail_po_transactions(active_pol_vals)
            data[index]['detail_transaction_ids'] = detail_transactions.ids

    def _get_bom_domain(self, boms):
        domain = False
        if boms:
            satisfy_boms = boms.filtered(lambda r: r.type in ['normal', 'subcontract'])
            if satisfy_boms:
                domain = [('id', 'in', satisfy_boms.ids)]
        return domain

    def _get_vendor_domain(self, product_id, bom_id=False):
        if bom_id:
            if bom_id.type == 'normal':
                domain = self._get_vendor_manufacture_domain(bom_id, product_id)
            elif bom_id.type == 'subcontract':
                domain = self._get_vendor_subcontract_domain(bom_id, product_id)
            else:
                domain = self._get_vendor_default_domain(bom_id, product_id)
        else:
            domain = self._get_vendor_default_domain(bom_id, product_id)
        return domain

    def _get_vendor_default_domain(self, bom_id, product_id):
        subcontractor_boms = self.env['mrp.bom'].search(
            [('type', '=', 'subcontract'), ('product_tmpl_id', '=', product_id.product_tmpl_id.id)])
        vendor_ids = set()
        for bom in subcontractor_boms:
            vendor_ids.update(bom.subcontractor_ids.ids)
        satisfy_partner_ids = self.env['res.partner'].search([('parent_id', 'in', list(vendor_ids))])
        return [('id', 'not in', list(vendor_ids) + satisfy_partner_ids.ids)]

    def _get_vendor_manufacture_domain(self, bom_id, product_id):
        return False

    def _get_vendor_subcontract_domain(self, bom_id, product_id):
        return [('id', 'in', bom_id.subcontractor_ids.ids)]

    @api.model
    def get_vendor_dependent(self, product_id, vendor_id):
        res = dict()
        res['leadTime'] = self.get_vendor_lead_time(product_id, vendor_id)
        return res

    @api.model
    def get_vendor_lead_time(self, product_id, vendor_id):
        if not vendor_id or not product_id:
            return 0
        partner_id = self.env['res.partner'].browse(vendor_id)
        product = self.env['product.product'].browse(product_id)
        maximum_of_minimum = max(product.seller_ids.mapped('min_qty'))
        existed_vendor = product._select_seller(partner_id=partner_id,
                                                quantity=maximum_of_minimum+1)
        lead_time = (existed_vendor and existed_vendor[0].delay or 0)
        return lead_time

    @api.model
    def get_child_bom(self, warehouse_id=None, parent_product_id=-1, bom_id=False, product_id=False,
                      requested_quantity=False, line_id=False, level=False, bom_ids=False, parent_bom_id=False,
                      is_root=False):
        """
        Function return components in BOM structure when change the BOM on the selection field
        """
        res = self.get_data_child_bom(warehouse_id, parent_product_id, bom_id, product_id, requested_quantity,
                                      line_id, level, bom_ids, parent_bom_id, is_root)
        company = self.env.user.company_id
        is_multi_wh = company.user_has_groups("stock.group_stock_multi_warehouses")

        res['data'] = self.env.ref('me_replenishment_planning.report_replenishment_planning_line').render({
            'data': res.get('data', []),
            'is_multi_wh': is_multi_wh
        })
        return res

    def get_data_child_bom(self, warehouse_id=None, parent_product_id=-1, bom_id=False, product_id=False,
                           requested_quantity=False, line_id=False, level=False, bom_ids=False, parent_bom_id=False,
                           is_root=False):
        res = dict()
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
        if components:
            components[0].update({
                'parent_id': parent_bom_id,
                'line_id': line_id,
            })
        res['data'] = components

        self._update_raw_response(res, res.get('data'))
        return res

    def get_default_requested_quantity(self, product, warehouse):
        # TODO: Should handle warehouse for multi-warehouse company
        if product:
            stock_status_lines = self.env['stock.status.report.line'].search_read([('product_id', '=', product.id)],
                                                                                  ['forecasted_demand'])
            return stock_status_lines and stock_status_lines[0].get('forecasted_demand', 0) or 0
        return 0

    def _create_detail_po_transactions(self, active_pol_vals):
        detail_vals = []
        if active_pol_vals:
            for pol_val in active_pol_vals:
                order_line_id = pol_val.get('id', -1)
                order_qty = pol_val.get('qty', 0)
                pol = self.env['purchase.order.line'].browse(order_line_id)
                if pol:
                    detail_vals.append({
                        'purchase_order_id': pol.order_id.id,
                        'product_qty': order_qty,
                        'date_to_complete': pol.date_planned or False,
                    })
        detail_transactions = self.env['detail.transaction'].create(detail_vals)
        return detail_transactions
