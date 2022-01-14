from odoo import models, fields, api, _
from odoo.tools.misc import format_date
import json

class NegativeReport(models.AbstractModel):
    _inherit = "phd.forecasted.quantity"
    _name = "phd.negative.report"
    _description = "Negative Report"

    @api.model
    def _get_columns_name(self, options):
        return [
            {'name': ''},
            {'name': _('Order ID'), 'style': 'text-align:center'},
            {'name': _('Reference'), 'style': 'text-align:center'},
            {'name': _('Transaction Quantity'), 'class': 'number'},
            {'name': _('Forecasted Quantity'), 'class': 'number'},
            {'name': _('On Hand'), 'class': 'number'},
            {'name': _('Date'), 'class': 'date'},
        ]

    @api.model
    def _get_report_name(self):
        return _("Negative Inventory Report")