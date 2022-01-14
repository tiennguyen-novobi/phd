# -*- coding: utf-8 -*-
import base64
from datetime import datetime, timedelta
from io import BytesIO

import xlsxwriter
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class SOSummary(models.TransientModel):
    _name = 'wizard.so.summary'
    _description = 'Report for SO Summary'

    date_start = fields.Date(string='Start Date', default=fields.Date.today)
    date_end = fields.Date(string='End Date')

    _sql_constraints = [
        ('date_check', 'check(date_start <= date_end)',
         'Start date must be smaller than end date'),
    ]

    def get_data(self):
        st_dt = fields.Datetime.from_string(self.date_start)
        report_data_list = []
        data_list = []
        total = 0
        domain = [
            ('confirmation_date', '>=', st_dt), ('state', '=', 'sale')]
        if self.date_end:
            end_dt = fields.Datetime.from_string(self.date_end) + timedelta(
                days=1)
            domain.append(('confirmation_date', '<', end_dt))
        sale_ids = self.env['sale.order'].search(domain)
        for sale in sale_ids:
            confirmation_date = ''
            expected_date = ''
            completed_date = ''
            if sale.confirmation_date:
                confirmation_date = datetime.strptime(
                    str(sale.confirmation_date),
                    '%Y-%m-%d %H:%M:%S').strftime('%m/%d/%Y')
            if sale.expected_date:
                expected_date = datetime.strptime(
                    str(sale.expected_date),
                    '%Y-%m-%d %H:%M:%S').strftime('%m/%d/%Y')
            if sale.x_studio_completed_date:
                completed_date = datetime.strptime(
                    str(sale.x_studio_completed_date),
                    '%Y-%m-%d').strftime('%m/%d/%Y')
            total += sale.amount_total

            report_data_list.append(
                {'so_name': sale.name, 'partner': sale.partner_id.name,
                 'po_number': sale.client_order_ref,
                 'so_date': confirmation_date,
                 'expected_date': expected_date,
                 'completed_date': completed_date,
                 'amt': self.env['sale.order']._format_amount(
                     sale.amount_total, sale.company_id.currency_id)})
        if report_data_list:
            data_list.append({
                'total': self.env['sale.order']._format_amount(
                    total, sale.company_id.currency_id),
                'data': report_data_list})
        return data_list

    @api.multi
    def print_summary_excel_report(self):
        # Method to print excel report
        fp = BytesIO()
        workbook = xlsxwriter.Workbook(fp)
        title_format = workbook.add_format(
            {'font_name': 'Calibri', 'font_size': 11, 'align': 'center'})
        row_header_format = workbook.add_format(
            {'font_name': 'Calibri', 'font_size': 11, 'bold': 1,
             'align': 'center'})
        align_right = workbook.add_format({'align': 'right'})
        font_bold = workbook.add_format({'bold': True})
        right_bold = workbook.add_format({'bold': True, 'align': 'right'})

        date_start = datetime.strptime(str(self.date_start),
                                       '%Y-%m-%d').strftime('%m/%d/%Y')
        date_end = ''
        if self.date_end:
            date_end = datetime.strptime(str(self.date_end),
                                         '%Y-%m-%d').strftime('%m/%d/%Y')

        worksheet = workbook.add_worksheet('SO Summary')
        worksheet.merge_range(
            0, 0, 0, 6, 'Sales Order Summary Report', title_format)
        worksheet.merge_range(
            'A2:G2', date_start + ' - ' + date_end, title_format)
        header_str = ['Sales Order', 'Partner', 'PO Number',
                      'Sales Order Date',
                      'Req. Date', 'Completed Date', 'Amount']

        worksheet.set_column('A:A', 15)
        worksheet.set_column('B:B', 20)
        worksheet.set_column('C:C', 20)
        worksheet.set_column('D:D', 20)
        worksheet.set_column('E:E', 20)
        worksheet.set_column('F:F', 15)
        worksheet.set_column('G:G', 15)
        row = 1
        col = 0
        data_list = self.get_data()

        if data_list:
            row += 2
            for index, header in enumerate(header_str, start=0):
                worksheet.write(row, index, header, row_header_format)
            for sale in data_list[0]['data']:
                row += 1
                worksheet.write(row, col, sale['so_name'])
                worksheet.write(row, col + 1, sale['partner'])
                if sale['po_number']:
                    worksheet.write(row, col + 2, sale['po_number'])
                worksheet.write(row, col + 3, sale['so_date'], align_right)
                worksheet.write(row, col + 4, sale['expected_date'],
                                align_right)
                worksheet.write(row, col + 5, sale['completed_date'],
                                align_right)
                worksheet.write(row, col + 6, sale['amt'], align_right)
            row += 2
            worksheet.write(row, col + 5, 'Total', font_bold)
            worksheet.write(row, col + 6, data_list[0]['total'], right_bold)

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
    def print_summary_pdf_report(self):
        # Method to print sale order summary report
        data_list = self.get_data()
        if not data_list:
            raise UserError(_('No records found'))
        else:
            return self.env.ref(
                'inventory_reporting.action_report_so_summary'
            ).report_action([])
