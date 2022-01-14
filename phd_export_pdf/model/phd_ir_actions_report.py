
from odoo import api, fields, models, tools, SUPERUSER_ID, _

class PHDIrActionsReport(models.Model):
    _inherit = 'ir.actions.report'

    @api.model
    def _get_report_from_name(self, report_name):
        res = super(PHDIrActionsReport, self)._get_report_from_name(report_name)
        if not res:
            report_obj = self.env['ir.actions.report']
            conditions = [('id', '=', report_name)]
            context = self.env['res.users'].context_get()

            res = report_obj.with_context(context).search(conditions, limit=1)
        return res