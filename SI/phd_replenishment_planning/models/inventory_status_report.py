# Copyright © 2021 Novobi, LLC
# See LICENSE file for full copyright and licensing details.

from odoo import models


class InventoryStatusReportModel(models.Model):
    _inherit = 'stock.status.report.line'

    def render_replenishment_report(self):
        res = self.env.ref('me_replenishment_planning.action_replenishment_planning').read()[0]
        res['context'] = {
            'model': 'report.replenishment_planning_report',
            'product_ids': self.mapped('product_id').ids
        }
        return res
