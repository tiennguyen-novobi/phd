# -*- coding: utf-8 -*-
from odoo import api, fields, models

class InvActivityComponentReport(models.TransientModel):
    _name = 'wizard.activity.component'
    _inherit = 'wizard.inv.activity.reports'
    _description = 'Report for Inventory Activity Component Report'

    def print_inv_pdf_report_component(self):
        # Method to print component pdf report
        self.ensure_one()
        data = {}
        data['ids'] = self.env.context.get('active_ids', [])
        data['form'] = self.read(['date_start', 'date_end', 'product_id',
                                  'item_categ'])[0]
        return self.env.ref(
            'inventory_reporting.action_report_inv_activity_comp_report'
        ).report_action(self, data=data)
