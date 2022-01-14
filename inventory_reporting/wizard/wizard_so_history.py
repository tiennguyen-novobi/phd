# -*- coding: utf-8 -*-
import base64
from datetime import datetime, timedelta
from io import BytesIO

import xlsxwriter
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class SOHistory(models.TransientModel):
    _name = 'wizard.so.history'
    _description = 'Report for SO History'

    date_start = fields.Date(string='Start Date', default=fields.Date.today)
    date_end = fields.Date(string='End Date')
    state_all = fields.Boolean(string='All')
    state_draft = fields.Boolean(string='Quotation')
    state_sent = fields.Boolean(string='Quotation Sent')
    state_sale = fields.Boolean(string='Sale Order')
    state_done = fields.Boolean(string='Locked')
    state_cancel = fields.Boolean(string='Cancelled')

    _sql_constraints = [
        ('date_check', 'check(date_start <= date_end)',
         'Start date must be smaller than end date'),
    ]

    @api.onchange('state_all')
    def _onchange_state_all(self):
        if self.state_all:
            self.state_draft = True
            self.state_sent = True
            self.state_sale = True
            self.state_done = True
            self.state_cancel = True
        if not  self.state_all:
            self.state_draft = False
            self.state_sent = False
            self.state_sale = False
            self.state_done = False
            self.state_cancel = False

    @api.onchange('state_draft', 'state_sent', 'state_sale',
                  'state_done', 'state_cancel')
    def _onchange_state(self):
        if not self.state_draft or not self.state_sent or not self.state_sale \
                or not self.state_done or not self.state_cancel:
            self.state_all = False

    def get_data(self):
        st_dt = fields.Datetime.from_string(self.date_start)
        data_list = []
        states = []
        domain = [('commitment_date', '>=', st_dt)]
        if self.date_end:
            end_dt = fields.Datetime.from_string(self.date_end) + timedelta(
                days=1)
            domain.append(('commitment_date', '<', end_dt))
        if self.state_draft:
            states.append('draft')
        if self.state_sent:
            states.append('sent')
        if self.state_sale:
            states.append('sale')
        if self.state_done:
            states.append('done')
        if self.state_cancel:
            states.append('cancel')
        if self.state_draft or self.state_sent or self.state_sale or \
                self.state_done or self.state_cancel:
            domain.append(('state', 'in', states))

        order_ids = self.env['sale.order'].search(domain)
        for order in order_ids:
            report_data_list = []
            for line in order.order_line:
                open_qty = line.product_uom_qty - line.qty_delivered
                expected_date = ''
                if line.order_id.commitment_date:
                    expected_date = datetime.strptime(
                        str(line.order_id.commitment_date),
                        '%Y-%m-%d %H:%M:%S').strftime('%m/%d/%Y')
                report_data_list.append(
                    {'order': line.order_id, 'name': line.product_id,
                     'description': line.name, 'req_date': expected_date,
                     'order_qty': line.product_uom_qty,
                     'ship_qty': line.qty_delivered,
                     'on_hand': line.product_id.qty_available,
                     'open_qty': open_qty,
                     'rate': line.order_id.currency_rate,
                     'total': self.env['sale.order']._format_amount(
                         line.price_subtotal,
                         line.order_id.company_id.currency_id)
                     })
            data_list.append({'order': order, 'lines': report_data_list})
        return data_list

    @api.multi
    def print_history_excel_report(self):
        # Method to print excel report
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
        row_format = workbook.add_format(
            {'font_size': 10})
        row_format.set_text_wrap()
        align_right = workbook.add_format({'font_size': 10, 'align': 'right'})

        date_start = datetime.strptime(str(self.date_start),
                                       '%Y-%m-%d').strftime('%m/%d/%Y')
        date_end = ''
        if self.date_end:
            date_end = datetime.strptime(str(self.date_end),
                                         '%Y-%m-%d').strftime('%m/%d/%Y')

        worksheet = workbook.add_worksheet('SO Summary')
        worksheet.merge_range(
            0, 0, 0, 6, 'Sales Order History Report', title_format)
        worksheet.merge_range(
            'A2:G2', date_start + ' - ' + date_end, title_format)
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

        row = 1
        col = 0
        data_list = self.get_data()

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
            filename = 'SO Summary'
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
    def print_history_pdf_report(self):
        # Method to print sale order history report
        data_list = self.get_data()
        if not data_list:
            raise UserError(_('No records found'))
        else:
            return self.env.ref(
                'inventory_reporting.action_report_so_history'
            ).report_action([])
