from odoo import models, fields
from odoo.tools.misc import format_datetime, format_date
import datetime
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
import pytz


class StockQuantityHistory(models.TransientModel):
    _inherit = 'stock.quantity.history'

    inventory_date = fields.Date(string='Inventory at Date', default=fields.Date.today())

    def open_at_date(self):
        active_model = self.env.context.get('active_model')
        if active_model == 'stock.valuation.layer':
            date_time = datetime.datetime(year=self.inventory_date.year, month=self.inventory_date.month,
                                          day=self.inventory_date.day, hour=23, minute=59, second=59)
            local = pytz.timezone(self.env.user.tz or 'UTC')
            local_dt = local.localize(date_time, is_dst=None)
            utc_dt = local_dt.astimezone(pytz.utc)
            action = self.env.ref('stock_account.stock_valuation_layer_action').read()[0]
            action['domain'] = [('create_date', '<=', utc_dt.strftime(DEFAULT_SERVER_DATETIME_FORMAT)),
                                ('product_id.type', '=', 'product')]
            action['display_name'] = format_date(self.env, self.inventory_date)
            return action
        return super(StockQuantityHistory, self).open_at_date()
