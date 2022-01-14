# -*- coding: utf-8 -*-
import io
import json
import xlsxwriter
import pytz

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import datetime
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT

from psycopg2._psycopg import AsIs

PICKING_TYPE_OUTGOING_CODE = 'outgoing'
PICKING_TYPE_INCOMING_CODE = 'incoming'

EXPORT_COLUMNS_NAME = {
    "client_order_ref": "PO #",
    "partner_name": "DC #",
    "so_name": "RETAIL ORDER",
    "partner_street": "ADDRESS",
    "partner_street2": "ADDRESS2",
    "partner_city": "CITY",
    "partner_state": "STATE",
    "partner_e1_ship_to": "E1 SHIP TO",
    "partner_zip": "ZIP",
    "product_sku": "SKU",
    "product_partner_name": "RETAILER ITEM#",
    "product_description_1": "DESC1",
    "product_description_2": "DESC2",
    "product_uom_qty": "QTY",
    "cases": "Cases",
    "weight": "Weight",
    "cube": "Cube",
    "cpd_ref": "CPD Ref#",
    "arn": "ARN",
    "carrier": "Carrier",
    "pro": "PRO #",
    "asn": "ASN",
    "expiry": "Expiry",
    "lot_name": "LOT",
    "pallets": "Pallets"
}

AMAZON_EXPORT_COLUMNS = [
    "client_order_ref",
    "so_name",
    "partner_name",
    "partner_street",
    "partner_street2",
    "partner_city",
    "partner_state",
    "partner_zip",
    "partner_e1_ship_to",
    "product_sku",
    "product_description_1",
    "product_description_2",
    "product_partner_name",
    "product_uom_qty",
    "lot_name",
    "cases",
    "weight",
    "cube",
    "cpd_ref",
    "arn",
    "carrier",
    "pro",
    "asn",
]

NON_AMAZON_EXPORT_COLUMNS = [
    "client_order_ref",
    "so_name",
    "partner_name",
    "partner_street",
    "partner_street2",
    "partner_city",
    "partner_state",
    "partner_zip",
    "partner_e1_ship_to",
    "product_sku",
    "product_description_1",
    "product_description_2",
    "product_partner_name",
    "product_uom_qty",
    "lot_name",
    "pallets",
    "cases",
    "weight",
    "expiry"
]

PICKING_TYPE_OUTGOING_CODE = 'outgoing'


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    ###################################
    # PUBLIC FUNCTIONS
    ###################################
    hide_add_line_detailed_operation = fields.Boolean(compute='_compute_hide_add_line_detailed_operation', store=False)
    hide_add_line_in_do = fields.Boolean()

    def action_export_picking_list(self):
        """
        Action to download report
        :param options:
        :type options: dict
        :return: an action to send request for download report process.
        """
        options = {}
        options['picking_ids'] = self.ids
        return {
            'type': 'ir_actions_report_download',
            'data': {'model': 'stock.picking',
                     'options': json.dumps(options),
                     'output_format': 'xlsx'
                     }
        }

    def get_xlsx(self, options):
        """
       Write data to xlsx file
       :param options:
       :type options: dict
       :param response:
       :return:
       :rtype: None
       """
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True,
                                                'remove_timezone': True,
                                                'default_date_format': 'mm/dd/yy hh:mm:ss'
                                                })

        export_data = self.query_data(options)

        amazon_data = list(filter(lambda x: x['is_amazon_distribution_center'], export_data))
        non_amazon_data = list(filter(lambda x: not x['is_amazon_distribution_center'], export_data))

        if amazon_data:
            amazon_sheet = workbook.add_worksheet(_('Amazon Picking List'))
            amazon_sheet_data = self.get_sheet_data(AMAZON_EXPORT_COLUMNS, amazon_data)
            for row, col, rec in amazon_sheet_data:
                amazon_sheet.write(row, col, rec)

        if non_amazon_data:
            non_amazon_sheet = workbook.add_worksheet(_('Other than Amazon Picking List'))
            non_amazon_sheet_data = self.get_sheet_data(NON_AMAZON_EXPORT_COLUMNS, non_amazon_data)
            for row, col, rec in non_amazon_sheet_data:
                non_amazon_sheet.write(row, col, rec)

        workbook.close()
        output.seek(0)
        generated_file = output.read()
        output.close()
        return generated_file

    def get_sheet_data(self, columns, data):
        sheet_data = []
        for col, field in enumerate(columns):
            sheet_data.append((0, col, EXPORT_COLUMNS_NAME.get(field)))
            for row, record in enumerate(data, 1):
                rec = record.get(field)
                if rec is None:
                    rec = ''
                elif type(rec) is list:
                    rec = ', '.join(map(str, rec)) if rec[0] else ''
                sheet_data.append((row, col, rec))
        return sheet_data

    def button_validate(self):
        is_need_to_check_lot = self._check_if_need_to_check_lot()

        if is_need_to_check_lot:
            # Buffer to store qty of each stock move line by lot number
            product_qty_to_move_by_lot = {}
            # Buffer to store available qty of Lot
            available_product_qty_by_lot = {}

            for move_line in self.move_line_ids:
                lot_id = move_line.lot_id
                # Dont need to check Lot if stock move line doesn't set Lot
                if not lot_id:
                    continue
                src_location_id = move_line.location_id
                lot_and_location_key = (lot_id.id, src_location_id.id)
                # Get available qty of that Lot
                if not available_product_qty_by_lot.get(lot_and_location_key):
                    quants = lot_id.quant_ids.filtered(lambda q: q.location_id == src_location_id)
                    available_product_qty_by_lot[lot_and_location_key] = sum(quants.mapped('quantity'))

                # Get need to reserve qty of each Lot and check with available qty of that Lot
                move_qty_done = move_line.qty_done
                if not product_qty_to_move_by_lot.get(lot_and_location_key):
                    product_qty_to_move_by_lot[lot_and_location_key] = move_qty_done
                else:
                    product_qty_to_move_by_lot[lot_and_location_key] += move_qty_done

                if product_qty_to_move_by_lot[lot_and_location_key] > available_product_qty_by_lot[
                    lot_and_location_key]:
                    raise ValidationError(
                        _('Lot %s in %s can only serve %s more products') % (
                            lot_id.name, src_location_id.name, available_product_qty_by_lot[lot_and_location_key]))
        res = super(StockPicking, self).button_validate()

        return res

    def action_update_done_date(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Update Date',
            'res_model': 'phd.update.date',
            'target': 'new',
            'view_id': self.env.ref('phd_inventory.phd_update_date_form_view').id,
            'view_mode': 'form',
            'context': {
                'default_date_time': self.date_done if self.date_done else False,
                'default_res_id': self.id,
                'default_field': 'date_done',
                'default_is_update': True,
                'default_model': self._name,
                'default_update_action_name': 'update_date_model_related',
            }
        }

    def action_done(self):
        res = super(StockPicking, self).action_done()
        if res and self._context.get('default_date_time', False):
            self.update_date_model_related(self._context.get('default_date_time'), 'date_done')
        return res

    def phd_button_validate(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Validate',
            'res_model': 'phd.update.date',
            'target': 'new',
            'view_id': self.env.ref('phd_inventory.phd_update_date_form_view').id,
            'view_mode': 'form',
            'context': {
                'default_date_time': self.date_done if self.date_done else fields.Datetime.now(),
                'default_res_id': self.id,
                'default_field': 'date_done',
                'default_is_update': False,
                'default_model': self._name,
                'default_action_name': 'button_validate',
                'default_update_action_name': 'update_date_model_related',
            }
        }

    def update_date_model_related(self, date, field=None):
        self.ensure_one()
        if isinstance(date, str):
            date = datetime.strptime(date, DEFAULT_SERVER_DATETIME_FORMAT)
        if field:
            self.write({field: date})
        self.move_lines.write({'date': date})
        self.move_line_ids.write({'date': date})
        stock_valuation_ids = self.env['stock.valuation.layer'].search(
            [('stock_move_id.id', 'in', self.move_lines.ids)])
        if stock_valuation_ids:
            sql_query = """
                UPDATE stock_valuation_layer SET create_date = '{date_time}' WHERE id {operator} {ids}
            """.format(date_time=date,
                       ids=tuple([record_id for record_id in stock_valuation_ids.ids]) if len(
                           stock_valuation_ids) >= 2 else stock_valuation_ids.id,
                       operator='in' if len(stock_valuation_ids) >= 2 else '=')
            self.env.cr.execute(sql_query, [])
            # Update Accounting
            timezone = pytz.timezone(self._context.get('tz') or self.env.user.tz or 'UTC')
            only_date = date.astimezone(timezone).date()
            stock_valuation_ids.account_move_id.write({'date': only_date})
            stock_valuation_ids.account_move_id.invoice_line_ids.write({'date': only_date})

    ###################################
    # HELPER FUNCTIONS
    ###################################

    def _check_if_need_to_check_lot(self):
        # Only check validate Lot qty for SO and Subcontracting PO
        picking_type_code = self.picking_type_id.code

        is_need_to_check_lot = (picking_type_code == PICKING_TYPE_OUTGOING_CODE) or \
                               (picking_type_code == PICKING_TYPE_INCOMING_CODE
                                and bool(self.purchase_id and self.purchase_id.production_ids))
        return is_need_to_check_lot

    def _select(self):
        select_query = """
                       SELECT so.client_order_ref                                             AS client_order_ref,
                           so.name                                                            AS so_name,
                           so.name                                                            AS cpd_ref,
                           partner.name                                                       AS partner_name,
                           partner.street                                                     AS partner_street,
                           partner.street2                                                    AS partner_street2,
                           partner.city                                                       AS partner_city,
                           partner.zip                                                        as partner_zip,
                           state.name                                                         AS partner_state,
                           partner.e1_ship_to                                                 AS partner_e1_ship_to,
                           product.default_code                                               AS product_sku,
                           product.description_1                                              as product_description_1,
                           product.description_2                                              as product_description_2,
                           move_line.qty_done                                                 as product_uom_qty,
                           production_lot.name                                                as lot_name,
                           product.unit_per_case,
                           product.weight,
                           product.case_length,
                           product.case_height,
                           product.case_width,
                           product.unit_per_pallet,
                           partner.is_amazon_distribution_center                              as is_amazon_distribution_center,
                           product_customerinfo.product_name                                  as product_partner_name,
                           CEIL(move_line.qty_done / NULLIF(product.unit_per_case, 0))        as cases,
                           (product.weight * move_line.qty_done)                              as weight,
                           CEIL(product.case_length * product.case_height * product.case_width
                               * CEIL(move_line.qty_done / NULLIF(product.unit_per_case, 0))) as cube,
                           CEIL(move_line.qty_done / NULLIF(product.unit_per_pallet, 0))      as pallets 
        """
        return select_query

    def _form(self, options):
        picking_ids = ','.join(str(x) for x in options['picking_ids'])
        form_query = """
                        FROM stock_picking picking
                             LEFT JOIN sale_order so ON picking.sale_id = so.id
                             JOIN res_partner partner ON picking.partner_id = partner.id AND picking.id in (%(picking_ids)s)
                             LEFT JOIN res_country_state state ON partner.state_id = state.id
                             JOIN stock_move_line move_line ON move_line.picking_id = picking.id
                             JOIN product_product product ON move_line.product_id = product.id
                             LEFT JOIN product_customerinfo ON move_line.product_id = product_customerinfo.product_id
                                                                AND product_customerinfo.partner_id = partner.parent_id
                             LEFT JOIN stock_production_lot production_lot on move_line.lot_id = production_lot.id
        """

        form_query_params = {'picking_ids': AsIs(picking_ids)}

        return form_query, form_query_params

    def _where(self, options):
        where_query = """
                    WHERE move_line.qty_done > 0
        """
        where_params = {}
        return where_query, where_params

    def _order_by(self):
        order_by_query = """
                        ORDER BY so.name
        """
        return order_by_query

    def query_data(self, options):
        select_query = self._select()
        from_query, from_params = self._form(options)
        where_query, where_params = self._where(options)
        order_by_query = self._order_by()
        sql_query = """
                %(select_query)s
                %(from_query)s
                %(where_query)s
                %(order_by_query)s
        """ % {
            'select_query': select_query,
            'from_query': from_query,
            'where_query': where_query,
            'order_by_query': order_by_query
        }
        self.env.cr.execute(sql_query, dict(**from_params, **where_params))
        results = self.env.cr.dictfetchall()
        return results

    def get_report_filename(self, options):
        tz_info = pytz.timezone(self._context.get('tz') or 'UTC')
        date_now = datetime.now(tz_info)
        filename = 'phd_picking_list_%s' % date_now.date()
        options['filename'] = filename
        return filename

    @api.depends('picking_type_id', 'partner_id')
    def _compute_hide_add_line_detailed_operation(self):
        self.ensure_one()
        self.hide_add_line_detailed_operation = False
        if self.partner_id.is_subcontractor and self.picking_type_id and self.picking_type_id.code == 'incoming':
            self.hide_add_line_detailed_operation = True
        if self.picking_type_id and self.picking_type_id.code == 'outgoing':
            self.hide_add_line_detailed_operation = True
