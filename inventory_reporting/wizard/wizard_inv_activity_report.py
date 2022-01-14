# -*- coding: utf-8 -*-
import base64
from datetime import datetime, timedelta
from io import BytesIO

import xlsxwriter
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class InvActivityReport(models.TransientModel):
    _name = 'wizard.inv.activity.reports'
    _description = 'Report for Inventory Activity Report'

    date_start = fields.Date(string='Start Date', default=fields.Date.today)
    date_end = fields.Date(string='End Date')
    product_id = fields.Many2one('product.product', string='SKU')
    item_categ = fields.Many2one('product.category', string='Item Category')

    _sql_constraints = [
        ('date_check', 'check(date_start <= date_end)',
         'Start date must be smaller than end date'),
    ]

    def get_data_dict(self, product_id, date_start, date_end, report_context):
        # Method to get dictionary of sale order, purchase order and
        # manufacturing order
        if report_context == 'finish_goods':
            st_dt = fields.Datetime.from_string(date_start)
            domain = [('product_id', '=', product_id.id),
                      ('order_id.state', '=', 'sale'),
                      ('order_id.commitment_date', '>=', st_dt)]
            if date_end:
                end_dt = fields.Datetime.from_string(date_end) + timedelta(
                    days=1)
                domain.append(('order_id.commitment_date', '<', end_dt))
            order_ids = self.env['sale.order.line'].search(domain).mapped(
                'order_id').ids
        else:
            domain = [('product_id', '=', product_id.id),
                      ('order_id.state', '=', 'purchase'),
                      ('order_id.x_studio_requested_ship_date', '>=',
                       date_start)]
            if date_end:
                domain.append(
                    ('order_id.x_studio_requested_ship_date', '<=', date_end))
            order_ids = self.env['purchase.order.line'].search(
                domain).mapped('order_id').ids
        domain = [('product_id', '=', product_id.id),
                  ('state', '!=', 'cancel'),
                  ('date_planned_start', '>=', date_start)]
        if date_end:
            domain.append(
                ('date_planned_start', '<=', date_end))
        mrp_ids = self.env['mrp.production'].search(domain).ids
        if not order_ids:
            order_ids = [0]
        if not mrp_ids:
            mrp_ids = [0]

        if report_context == 'finish_goods':
            sql_query = """
                        SELECT mrp.id, mrp.name as name, 
                        mrp.date_planned_start as expected_date 
                        from mrp_production as mrp 
                        where id in %s
                        UNION
                        SELECT ord.id, ord.name as name, 
                        ord.commitment_date as expected_date 
                        from sale_order as ord
                        where id in %s
                        order by expected_date"""
        else:
            sql_query = """
                        SELECT mrp.id, mrp.name as name, 
                        mrp.date_planned_start as expected_date 
                        from mrp_production as mrp 
                        where id in %s
                        UNION
                        SELECT ord.id, ord.name as name, 
                        ord.x_studio_requested_ship_date as expected_date 
                        from purchase_order as ord
                        where id in %s
                        order by expected_date"""

        param = (tuple(mrp_ids), tuple(order_ids))
        self.env.cr.execute(sql_query, param)
        query_rec = self.env.cr.dictfetchall()

        report_data_list = []
        cnt = 1
        expected_date = ''

        for rec in query_rec:
            mrp_id = self.env['mrp.production'].search(
                [('name', '=', rec.get('name'))])
            if report_context == 'finish_goods':
                sale_id = self.env['sale.order'].search(
                    [('name', '=', rec.get('name'))])
                if mrp_id:
                    if cnt == 1:
                        total = product_id.qty_available + mrp_id.product_qty
                    else:
                        total += mrp_id.product_qty
                    if mrp_id.date_planned_start:
                        expected_date = datetime.strptime(
                            str(mrp_id.date_planned_start.date()),
                            '%Y-%m-%d').strftime('%m/%d/%Y')
                    report_data_list.append(
                        {'mo_name': mrp_id.name, 'so_name': '', 'so_date': '',
                         'expected_date': expected_date,
                         'qty_in': mrp_id.product_qty,
                         'qty_out': '', 'avail_inv': total,
                         'partner_name': ''})
                else:
                    for line in sale_id.order_line:
                        if line.product_id == product_id:
                            if cnt == 1:
                                total = product_id.qty_available - \
                                        line.product_uom_qty
                            else:
                                total -= line.product_uom_qty
                            confirmation_date = ''
                            if line.order_id.confirmation_date:
                                confirmation_date = datetime.strptime(
                                    str(line.order_id.confirmation_date),
                                    '%Y-%m-%d %H:%M:%S').strftime('%m/%d/%Y')
                            if line.order_id.commitment_date:
                                expected_date = datetime.strptime(
                                    str(line.order_id.commitment_date),
                                    '%Y-%m-%d %H:%M:%S').strftime('%m/%d/%Y')
                            report_data_list.append({
                                'mo_name': '', 'so_name': line.order_id.name,
                                'so_date': confirmation_date,
                                'expected_date': expected_date,
                                'qty_in': '', 'qty_out': line.product_uom_qty,
                                'avail_inv': total,
                                'partner_name': line.order_id.partner_id.name})
            else:
                purchase_id = self.env['purchase.order'].search(
                    [('name', '=', rec.get('name'))])
                if mrp_id:
                    if cnt == 1:
                        total = product_id.qty_available - mrp_id.product_qty
                    else:
                        total -= mrp_id.product_qty
                    if mrp_id.date_planned_start:
                        expected_date = datetime.strptime(
                            str(mrp_id.date_planned_start.date()),
                            '%Y-%m-%d').strftime('%m/%d/%Y')
                    report_data_list.append(
                        {'mo_name': mrp_id.name, 'po_name': '', 'po_date': '',
                         'expected_date': expected_date,
                         'qty_in': '',
                         'qty_out': mrp_id.product_qty, 'avail_inv': total,
                         'partner_name': ''})
                else:
                    for line in purchase_id.order_line:
                        if line.product_id == product_id:
                            if cnt == 1:
                                total = product_id.qty_available + \
                                        line.product_qty
                            else:
                                total += line.product_qty
                            date_order = ''
                            if line.order_id.date_order:
                                date_order = datetime.strptime(
                                    str(line.order_id.date_order),
                                    '%Y-%m-%d %H:%M:%S').strftime('%m/%d/%Y')
                            if line.order_id.x_studio_requested_ship_date:
                                expected_date = datetime.strptime(str(
                                    line.order_id.x_studio_requested_ship_date
                                ), '%Y-%m-%d').strftime('%m/%d/%Y')
                            report_data_list.append({
                                'mo_name': '', 'po_name': line.order_id.name,
                                'po_date': date_order,
                                'expected_date': expected_date,
                                'qty_in': line.product_qty, 'qty_out': '',
                                'avail_inv': total,
                                'partner_name': line.order_id.partner_id.name})
            cnt += 1
        return report_data_list

    @api.multi
    def print_excel_report(self):
        # Method to print excel report

        fp = BytesIO()
        workbook = xlsxwriter.Workbook(fp)
        title_format = workbook.add_format(
            {'font_name': 'Calibri', 'font_size': 11, 'align': 'center'})
        header_format = workbook.add_format(
            {'font_name': 'Calibri', 'font_size': 12, 'bold': 1,
             'align': 'center'})
        row_header_format = workbook.add_format(
            {'font_name': 'Calibri', 'font_size': 11, 'bold': 1,
             'align': 'center'})
        align_right = workbook.add_format(
            {'align': 'right'})
        red = workbook.add_format(
            {'font_color': 'red', 'align': 'right'})

        date_start = datetime.strptime(str(self.date_start),
            '%Y-%m-%d').strftime('%m/%d/%Y')
        date_end = ''
        if self.date_end:
            date_end = datetime.strptime(str(self.date_end),
                '%Y-%m-%d').strftime('%m/%d/%Y')

        report_context = self.env.context.get('report_context')
        if report_context == 'finish_goods':
            worksheet = workbook.add_worksheet('Inv - Activity FG')
            worksheet.merge_range(
                0, 0, 0, 7, 'Inventory Activity Report - Finished Goods',
                title_format)
            worksheet.merge_range(
                'A2:H2', date_start + ' - ' + date_end, title_format)
            header_str = [
                'Manufacturing Order', 'Sales Order', 'Sales Order Date',
                'Expected Date', 'Qty In', 'Qty Out', 'Available Inventory',
                'Partner']
        else:
            worksheet = workbook.add_worksheet('Inv - Activity Component')
            worksheet.merge_range(
                0, 0, 0, 7, 'Inventory Activity Report - Components',
                title_format)
            worksheet.merge_range(
                'A2:H2', date_start + ' - ' + date_end, title_format)
            header_str = [
                'Purchase Order', 'Manufacturing Order', 'PO Date',
                'Expected Date', 'Qty In', 'Qty Out', 'Available Inventory',
                'Partner']

        worksheet.set_column('A:A', 20)
        worksheet.set_column('B:B', 20)
        worksheet.set_column('C:C', 20)
        worksheet.set_column('D:D', 15)
        worksheet.set_column('G:G', 20)
        worksheet.set_column('H:H', 15)
        row = 1
        col = 0

        data_dict = {}
        if self.product_id:
            if self.item_categ and \
                    self.product_id.categ_id.id != self.item_categ.id:
                raise UserError(_(
                    'The selected product category does not match with the '
                    'selected category.'))
            rec = self.get_data_dict(
                self.product_id, self.date_start, self.date_end,
                report_context)
            if rec:
                data_dict.update({self.product_id: rec})
            else:
                raise UserError(_('No records found'))
        elif self.item_categ:
            product_ids = self.env['product.product'].search(
                [('categ_id', '=', self.item_categ.id)])
            for product in product_ids:
                rec = self.get_data_dict(
                    product, self.date_start, self.date_end, report_context)
                if rec:
                    data_dict.update({product: rec})
            if not data_dict:
                raise UserError(_('No records found'))
        else:
            category_ids = self.env['product.category'].search([])
            for categ_id in category_ids:
                product_ids = self.env['product.product'].search(
                    [('categ_id', '=', categ_id.id)])
                for product in product_ids:
                    rec = self.get_data_dict(
                        product, self.date_start, self.date_end,
                        report_context)
                    if rec:
                        data_dict.update({product: rec})
            if not data_dict:
                raise UserError(_('No records found'))
        for product_id in data_dict:
            row += 2
            worksheet.set_row(row, 20)
            worksheet.write(row, col, 'Item Number', header_format)
            worksheet.write(row, col + 1, product_id.default_code,
                            header_format)
            row += 1
            for index, header in enumerate(header_str, start=0):
                worksheet.write(row, index, header, row_header_format)
            row += 1
            if product_id.qty_available < 0:
                qty = '(' + str(abs(product_id.qty_available)) + ')'
                worksheet.write(row, col + 6, qty, red)
            else:
                worksheet.write(row, col + 6, product_id.qty_available)

            for data in data_dict[product_id]:
                row += 1

                if report_context == 'finish_goods':
                    worksheet.write(row, col, data.get('mo_name'))
                    worksheet.write(row, col + 1, data.get('so_name'))
                    worksheet.write(row, col + 2, data.get('so_date'),
                                    align_right)
                else:
                    worksheet.write(row, col, data.get('po_name'))
                    worksheet.write(row, col + 1, data.get('mo_name'))
                    worksheet.write(row, col + 2, data.get('po_date'),
                                    align_right)
                worksheet.write(row, col + 3, data.get('expected_date'),
                                align_right)
                worksheet.write(row, col + 4, data.get('qty_in'))
                worksheet.write(row, col + 5, data.get('qty_out'))
                if data.get('avail_inv') < 0:
                    worksheet.write(row, col + 6, '(' + str(
                        abs(data.get('avail_inv'))) + ')', red)
                else:
                    worksheet.write(row, col + 6, data.get('avail_inv'))
                worksheet.write(row, col + 7, data.get('partner_name'))

        workbook.close()
        fp.seek(0)
        result = base64.b64encode(fp.read())
        attachment_obj = self.env['ir.attachment']

        if report_context == 'finish_goods':
            filename = 'Inventory Activity FG'
        else:
            filename = 'Inventory Activity Component'

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
