import logging
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo import api, fields, models, SUPERUSER_ID, _
from odoo.tools import float_compare, float_is_zero
import pytz
from datetime import datetime

_logger = logging.getLogger(__name__)


class InheritStockInventory(models.Model):
    _inherit = 'stock.inventory'

    def _action_done(self):
        res = super(InheritStockInventory, self)._action_done()
        if res:
            accouting_date = self.accounting_date
            date = datetime.now()
            if accouting_date:
                date = date.replace(day=accouting_date.day, month=accouting_date.month, year=accouting_date.year)
                timezone = pytz.timezone(self._context.get('tz') or self.env.user.tz or 'UTC')
                date = date.astimezone(timezone).strftime(DEFAULT_SERVER_DATETIME_FORMAT)
            for move_id in self.move_ids:
                move_id.write({'date': date, 'date_expected': date})
                move_id.move_line_ids.write({'date': date})
                if move_id.stock_valuation_layer_ids:
                    sql_query = """
                                                   UPDATE stock_valuation_layer SET create_date = '{date_time}' WHERE id {operator} {ids}
                                               """.format(date_time=date,
                                                          ids=tuple([record_id for record_id in
                                                                     move_id.stock_valuation_layer_ids.ids]) if len(
                                                              move_id.stock_valuation_layer_ids) >= 2 else move_id.stock_valuation_layer_ids.id,
                                                          operator='in' if len(
                                                              move_id.stock_valuation_layer_ids) >= 2 else '=')
                    self.env.cr.execute(sql_query, [])
        return res
