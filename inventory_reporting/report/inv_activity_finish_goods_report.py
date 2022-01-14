# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class ReportInvActivityFGReports(models.AbstractModel):
    _name = 'report.inventory_reporting.report_finish_goods_reports'

    @api.model
    def _get_report_values(self, docids, data=None):
        data_dict = {}

        if data['form']['product_id']:
            product_id = self.env['product.product'].browse(
                data['form']['product_id'][0])

            if data['form']['item_categ'] and product_id.categ_id.id != \
                    data['form']['item_categ'][0]:
                raise UserError(_(
                    'The category of the selected product does not match '
                    'with the selected category.'))
            rec = self.env['wizard.inv.activity.reports'].get_data_dict(
                product_id, data['form']['date_start'],
                data['form']['date_end'],
                data.get('context').get('report_context'))
            if rec:
                data_dict.update({product_id: rec})
            else:
                raise UserError(_('No records found'))
        elif data['form']['item_categ']:
            product_ids = self.env['product.product'].search(
                [('categ_id', '=', data['form']['item_categ'][0])])
            for product in product_ids:
                rec = self.env['wizard.inv.activity.reports'].get_data_dict(
                    product, data['form']['date_start'],
                    data['form']['date_end'],
                    data.get('context').get('report_context'))
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
                    rec = self.env[
                        'wizard.inv.activity.reports'].get_data_dict(
                        product, data['form']['date_start'],
                        data['form']['date_end'],
                        data.get('context').get('report_context'))
                    if rec:
                        data_dict.update({product: rec})
            if not data_dict:
                raise UserError(_('No records found'))
        data.update({'inv_data': data_dict})
        return {
            'doc_ids': docids,
            'doc_model': 'wizard.inv.activity.reports',
            'docs': self.env['wizard.inv.activity.reports'].browse(docids),
            'data': data
        }
