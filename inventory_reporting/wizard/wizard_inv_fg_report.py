# -*- coding: utf-8 -*-
from odoo import api, fields, models


class InvActivityFGReport(models.TransientModel):
    _name = 'wizard.activity.finish.goods'
    _inherit = 'wizard.inv.activity.reports'
    _description = 'Report for Inventory Activity Finish Goods Report'

    def print_inv_pdf_report(self):
        # Method to print pdf report of Finish Goods
        self.ensure_one()
        data = {}
        data['ids'] = self.env.context.get('active_ids', [])
        data['form'] = self.read(['date_start', 'date_end', 'product_id',
                                  'item_categ'])[0]
        return self.env.ref(
            'inventory_reporting.action_report_inv_activity_fg_report'
        ).report_action(self, data=data)
