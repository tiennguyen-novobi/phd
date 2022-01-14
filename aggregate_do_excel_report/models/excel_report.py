# -*- coding: utf-8 -*-
import io
import base64
from odoo import models, fields
from odoo.tools.misc import xlwt


class DoRelease(models.Model):
    _name = 'do.release'
    _description = 'Delivery Order Release'

    name = fields.Char(string='Name')

    def generate_excel_report(self, aggregate_order):
        workbook = xlwt.Workbook()
        worksheet = workbook.add_sheet('JYM Order Release')

        table_cell_format = xlwt.easyxf(
            "font: bold on; align: wrap on, vert centre, horiz center")

        # table_cell_format = workbook.add_format(
        #     {'bold': True, 'align': 'center', 'font_size': 10})
        worksheet.write(0, 0, 'PO #', table_cell_format)
        worksheet.write(0, 1, 'RETAILER ORDER#', table_cell_format)
        worksheet.write(0, 2, 'DC #', table_cell_format)
        worksheet.write(0, 3, 'ADDRESS', table_cell_format)
        worksheet.write(0, 4, 'ADDRESS2', table_cell_format)
        worksheet.write(0, 5, 'CITY', table_cell_format)
        worksheet.write(0, 6, 'STATE', table_cell_format)
        worksheet.write(0, 7, 'ZIP', table_cell_format)
        worksheet.write(0, 8, 'E1 SHIP TO #', table_cell_format)
        worksheet.write(0, 9, 'SKU', table_cell_format)
        worksheet.write(0, 10, 'DESC1', table_cell_format)
        worksheet.write(0, 11, 'DESC2', table_cell_format)
        worksheet.write(0, 12, 'RETAILER ITEM#', table_cell_format)
        worksheet.write(0, 13, 'QTY', table_cell_format)
        worksheet.write(0, 14, 'LOT', table_cell_format)
        worksheet.write(0, 15, 'Pallets', table_cell_format)
        worksheet.write(0, 16, 'Cases', table_cell_format)
        worksheet.write(0, 17, 'Weight', table_cell_format)
        worksheet.write(0, 18, 'Cube', table_cell_format)
        worksheet.write(0, 19, 'Shipment Weight', table_cell_format)
        worksheet.write(0, 20, 'Number of Pallets', table_cell_format)
        worksheet.write(0, 21, 'ARN', table_cell_format)
        worksheet.write(0, 22, 'Shipment Number', table_cell_format)

        row = 0
        # table_cell_format = workbook.add_format(
        #     {'bold': False, 'align': 'left', 'font_size': 10})
        table_cell_format = xlwt.easyxf("font: bold off;")

        row += 1
        for do in aggregate_order.x_studio_delivery_orders:
            so = self.env['sale.order'].search(
                [('name', '=', do.group_id.name)])

            # do_line_id = do.move_ids_without_package[0]
           
            for line in do.move_ids_without_package:
                if so.client_order_ref:
                    worksheet.write(row, 0, so.client_order_ref, table_cell_format)
                worksheet.write(row, 1, so.name, table_cell_format)
                worksheet.write(row, 2, so.partner_id.name, table_cell_format)
                worksheet.write(row, 3, so.partner_id.street,
                                table_cell_format)
                if so.partner_id.street2:
                    worksheet.write(row, 4, so.partner_id.street2,

                                table_cell_format)
                worksheet.write(row, 5, so.partner_id.city, table_cell_format)
                worksheet.write(row, 6, so.partner_id.state_id.name,
                                table_cell_format)
                worksheet.write(row, 7, so.partner_id.zip, table_cell_format)

                if so.partner_id.ref:
                    worksheet.write(row, 8, so.partner_id.ref, table_cell_format)

                product = line.product_id
                if product.default_code:
                    worksheet.write(row, 9, product.default_code,
                                table_cell_format)
                worksheet.write(row, 10, product.name,
                                table_cell_format)
                if product.description:
                    worksheet.write(row, 11,

                                product.description,
                                table_cell_format)

                part_number = \
                    product.x_studio_customer_part_number.filtered(
                        lambda s: s.x_studio_customer == so.partner_id).mapped(
                        'x_studio_part_number')
                worksheet.write(row, 12, part_number, table_cell_format)
                worksheet.write(row, 13, line.product_uom_qty,
                                table_cell_format)

                if line.active_move_line_ids and line.active_move_line_ids.lot_id.name:
                    worksheet.write(row, 14, line.active_move_line_ids and

                                line.active_move_line_ids.lot_id.name,
                                table_cell_format)

                # aggregate_do = line.x_aggregate_delivery_order
                aggregate_do = line
                worksheet.write(row, 15, aggregate_do.x_studio_pallet_1,
                                table_cell_format)
                worksheet.write(row, 16, aggregate_do.x_studio_cases,
                                table_cell_format)

                weight = line.product_uom_qty * product.x_studio_weight_lb
                worksheet.write(row, 17, weight, table_cell_format)

                worksheet.write(row, 18,
                                aggregate_order.x_studio_cubic_feet_calculated,
                                table_cell_format)
                worksheet.write(row, 19, aggregate_order.x_studio_weight,
                                table_cell_format)
                worksheet.write(row, 20, aggregate_order.x_studio_nb_of_pallets,
                                table_cell_format)
                if aggregate_order.x_studio_arn:
                    worksheet.write(row, 21, aggregate_order.x_studio_arn,

                                table_cell_format)
                worksheet.write(row, 22, aggregate_order.x_name,
                                table_cell_format)
                row += 1

        report_name = 'Order Release'
        filename = report_name + ".xls"
        fp = io.BytesIO()
        workbook.save(fp)
        wiz_pool = self.env['excel.report.wizard']
        wiz = wiz_pool.create({
            'data': base64.encodestring(fp.getvalue()),
            'file_name': filename
        })
        workbook.close()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'excel.report.wizard',
            'view_mode': 'form',
            'view_type': 'form',
            'res_id': wiz.id,
            'views': [(False, 'form')],
            'target': 'new'
        }
