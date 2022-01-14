# -*- coding: utf-8 -*-
import base64
from datetime import datetime
from io import BytesIO

import xlsxwriter
from odoo import api, models, _
from odoo.exceptions import UserError


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def _format_amount(self, amount, currency):
        fmt = "%.{0}f".format(currency.decimal_places)
        lang = self.env['res.lang']._lang_get(self.env.context.get('lang') or 'en_US')
        res =  lang.format(fmt, currency.round(amount), grouping=True, monetary=True)\
            .replace(r' ', u'\N{NO-BREAK SPACE}').replace(r'-', u'-\N{ZERO WIDTH NO-BREAK SPACE}')

        if currency and currency.symbol:
            if currency.position == 'after':
                res = '%s %s' % (res, currency.symbol)
            elif currency and currency.position == 'before':
                res = '%s %s' % (currency.symbol, res)
        return res

    def get_open_order(self):
        # Returns dictionary of sale order data
        data_list = []
        order_ids = self.search([('state', '=', 'sale')])
        for order in order_ids:
            report_data_list = []
            for line in order.order_line:
                open_qty = line.product_uom_qty - line.qty_delivered
                expected_date = ''
                confirmation_date = ''
                if line.order_id.confirmation_date:
                    confirmation_date = datetime.strptime(
                        str(line.order_id.confirmation_date),
                        '%Y-%m-%d %H:%M:%S').strftime('%m/%d/%Y')
                if line.order_id.commitment_date:
                    expected_date = datetime.strptime(
                        str(line.order_id.commitment_date),
                        '%Y-%m-%d %H:%M:%S').strftime('%m/%d/%Y')
                report_data_list.append(
                    {'order': line.order_id, 'name': line.product_id,
                     'description': line.name, 'req_date': expected_date,
                     'order_date': confirmation_date,
                     'unit_price': self._format_amount(
                         line.price_unit,
                         line.order_id.company_id.currency_id),
                     'discount': line.discount,
                     'product_uom': line.product_uom.name,
                     'order_qty': line.product_uom_qty,
                     'ship_qty': line.qty_delivered,
                     'on_hand': line.product_id.qty_available,
                     'open_qty': open_qty,
                     'rate': line.order_id.currency_rate,
                     'total': self._format_amount(
                         line.price_subtotal,
                         line.order_id.company_id.currency_id)})
            data_list.append({'order': order, 'lines': report_data_list})
        return data_list

    @api.multi
    def print_report(self):
        # Method to print sale order open order report
        sale_ids = self.search([('state', '=', 'sale')], limit=1)
        if not sale_ids:
            raise UserError(_('No records found'))
        else:
            return self.env.ref(
                'inventory_reporting.action_report_so_open_order'
            ).report_action(sale_ids)

    @api.multi
    def print_excel_report(self):
        # Method to print sale order open order excel report
        fp = BytesIO()
        workbook = xlsxwriter.Workbook(fp)
        title_format = workbook.add_format(
            {'font_name': 'Calibri', 'font_size': 11, 'align': 'center'})
        header_format = workbook.add_format(
            {'font_name': 'Calibri', 'font_size': 12, 'bold': 1,
             'align': 'center'})
        header_format.set_text_wrap()
        row_header_format = workbook.add_format(
            {'font_name': 'Calibri', 'font_size': 11, 'bold': 1,
             'align': 'center'})
        align_right = workbook.add_format(
            {'align': 'right', 'font_size': 10})
        row_format = workbook.add_format(
            {'font_size': 10})
        row_format.set_text_wrap()

        worksheet = workbook.add_worksheet('SO - Open Order')
        worksheet.merge_range(
            0, 0, 0, 7, 'Open Sale Order Report',
            title_format)
        header_str = [
            'Product', 'Description', 'Req. Date', 'Ordered Qty',
            'Ship Qty', 'Onhand Qty', 'Open Qty', 'Rate', 'Total']

        worksheet.set_column('A:A', 30)
        worksheet.set_column('B:B', 30)
        worksheet.set_column('C:C', 30)
        worksheet.set_column('D:D', 12)
        worksheet.set_column('E:E', 12)
        worksheet.set_column('F:F', 12)
        worksheet.set_column('G:G', 12)
        worksheet.set_column('H:H', 12)
        worksheet.set_column('I:I', 12)
        worksheet.set_column('J:J', 12)
        row = 0
        col = 0

        data_list = self.get_open_order()
        if data_list:
            for data in data_list:
                row += 2
                worksheet.set_row(row, 28)
                worksheet.write(
                    row, col, 'Sale Order Number - ' + data['order'].name,
                    header_format)
                po_number = ''
                if data['order'].client_order_ref:
                    po_number = data['order'].client_order_ref
                worksheet.write(row, col + 1, 'PO Number - ' +
                                po_number, header_format)
                worksheet.write(row, col + 2,
                                'Customer - ' + data['order'].partner_id.name,
                                header_format)
                row += 1
                for index, header in enumerate(header_str, start=0):
                    worksheet.write(row, index, header, row_header_format)

                for lines in data['lines']:
                    row += 1
                    worksheet.set_row(row, 35)
                    worksheet.write(row, col, lines.get('name').default_code,
                                    row_format)
                    worksheet.write(row, col + 1, lines.get('description'),
                                    row_format)
                    worksheet.write(row, col + 2, lines.get('req_date'),
                                    align_right)
                    worksheet.write(row, col + 3, lines.get('order_qty'),
                                    align_right)
                    worksheet.write(row, col + 4, lines.get('ship_qty'),
                                    align_right)
                    worksheet.write(row, col + 5, lines.get('on_hand'),
                                    align_right)
                    worksheet.write(row, col + 6, lines.get('open_qty'),
                                    align_right)
                    worksheet.write(row, col + 7, lines.get('rate'),
                                    align_right)
                    worksheet.write(row, col + 8, lines.get('total'),
                                    align_right)

            workbook.close()
            fp.seek(0)
            result = base64.b64encode(fp.read())
            attachment_obj = self.env['ir.attachment']
            filename = 'Open Sale Order Report'

            attachment_id = attachment_obj.create(
                {'name': filename,
                 'datas_fname': filename,
                 'datas': result})

            download_url = '/web/content/' + \
                           str(attachment_id.id) + '?download=True'
            base_url = self.env['ir.config_parameter'].sudo(
            ).get_param('web.base.url')
            return {
                "type": "ir.actions.act_url",
                "url": str(base_url) + str(download_url),
                "target": "new",
                'nodestroy': False,
            }
        else:
            raise UserError(_('No records found'))

    @api.multi
    def print_line_item_report(self):
        # Method to print sale order line item report
        sale_ids = self.search([('state', '=', 'sale')], limit=1)
        if not sale_ids:
            raise UserError(_('No records found'))
        else:
            return self.env.ref(
                'inventory_reporting.action_report_so_line_item'
            ).report_action(sale_ids)

    @api.multi
    def print_line_item_excel_report(self):
        # Method to print sale order line item excel report
        fp = BytesIO()
        workbook = xlsxwriter.Workbook(fp)
        title_format = workbook.add_format(
            {'font_name': 'Calibri', 'font_size': 11, 'align': 'center'})
        row_header_format = workbook.add_format(
            {'font_name': 'Calibri', 'font_size': 11, 'bold': 1,
             'align': 'center'})
        align_right = workbook.add_format(
            {'align': 'right'})
        row_format = workbook.add_format(
            {'font_size': 11})
        row_format.set_text_wrap()

        worksheet = workbook.add_worksheet('SO - Line Item')
        worksheet.merge_range(
            0, 0, 0, 8, 'Sale Order Line Item Report',
            title_format)
        header_str = [
            'SO#', 'Customer', 'Order Date', 'Item', 'UOM', 'Ordered Qty',
            'Unit Price', 'Discount', 'Net Price']

        worksheet.set_column('A:A', 20)
        worksheet.set_column('B:B', 30)
        worksheet.set_column('C:C', 15)
        worksheet.set_column('D:D', 15)
        worksheet.set_column('G:G', 15)
        worksheet.set_column('I:I', 15)
        worksheet.set_column('F:F', 15)
        row = 0
        col = 0

        data_list = self.get_open_order()
        if data_list:
            row += 2
            for index, header in enumerate(header_str, start=0):
                worksheet.write(row, index, header, row_header_format)
            for data in data_list:
                for lines in data['lines']:
                    row += 1
                    worksheet.set_row(row, 30)
                    worksheet.write(row, col, lines.get('order').name)
                    worksheet.write(row, col + 1,
                                    lines.get('order').partner_id.name)
                    worksheet.write(row, col + 2, lines.get('order_date'),
                                    align_right)
                    worksheet.write(row, col + 3, lines.get('name').name,
                                    row_format)
                    worksheet.write(row, col + 4, lines.get('product_uom'))
                    worksheet.write(row, col + 5, lines.get('order_qty'),
                                    align_right)
                    worksheet.write(row, col + 6, lines.get('unit_price'),
                                    align_right)
                    worksheet.write(row, col + 7, lines.get('discount'),
                                    align_right)
                    worksheet.write(row, col + 8, lines.get('total'),
                                    align_right)

            workbook.close()
            fp.seek(0)
            result = base64.b64encode(fp.read())
            attachment_obj = self.env['ir.attachment']
            filename = 'Sale Order Line Item Report'

            attachment_id = attachment_obj.create(
                {'name': filename,
                 'datas_fname': filename,
                 'datas': result})

            download_url = '/web/content/' + \
                           str(attachment_id.id) + '?download=True'
            base_url = self.env['ir.config_parameter'].sudo(
            ).get_param('web.base.url')
            return {
                "type": "ir.actions.act_url",
                "url": str(base_url) + str(download_url),
                "target": "new",
                'nodestroy': False,
            }
        else:
            raise UserError(_('No records found'))
