# Copyright © 2021 Novobi, LLC
# See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from dateutil.relativedelta import relativedelta
from odoo.exceptions import UserError
import pytz
from datetime import datetime, date
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, float_round
from math import log10
from ..utils.data_util import format_report_data, format_header_data, format_body_data, \
    format_quantity_description_data, format_table_data, format_header_cell, format_content_cell, format_datetime, \
    format_float_number
from ..utils import graph_config as graph
from ..utils import color_util as color


class DemandForecastReport(models.AbstractModel):
    _name = 'demand.forecast.report'
    _description = "Forecasted Demand Report"

    open_mos_data = {}
    open_sos_data = {}
    forecasted_demand = {}
    product_id = False
    factor = 0
    float_format = (lambda number: f'{number:,.2f}')
    labels = []

    def init(self):
        create_actual_demand_stmt = """
           CREATE TABLE IF NOT EXISTS actual_sales_demand (
                            week_end_date date,
                            product_id int,
                            partner_id int,
                            sale_qty float,
                            sale_uom_id int
           );
           CREATE INDEX IF NOT EXISTS actual_sales_demand_date_index ON actual_sales_demand (week_end_date, product_id, partner_id);
        """
        create_daily_demand_stmt = """
           CREATE TABLE IF NOT EXISTS actual_daily_sales_demand (
                            date_order date,
                            product_id int,
                            partner_id int,
                            sale_qty float,
                            sale_uom_id int
           );
           CREATE INDEX IF NOT EXISTS actual_daily_sales_demand_date_index ON actual_daily_sales_demand (date_order, product_id);
        """
        create_table_stmt =  create_actual_demand_stmt + create_daily_demand_stmt
        self.env.cr.execute(create_table_stmt)

    @api.model
    def get_last_updated_time(self):
        last_updated = self.env['ir.config_parameter'].sudo().get_param('phd_demand_forecast.last_updated')
        try:
            last_updated = last_updated and fields.datetime.strptime(last_updated, DEFAULT_SERVER_DATETIME_FORMAT) or ''
            return last_updated
        except ValueError:
            return ''

    @api.model
    def compute_sales_demand_data(self):
        params = self.env['ir.config_parameter'].sudo()
        has_intialize_data = params.get_param('phd_demand_forecast.has_initialized_data') == 'True'
        where_stmt = ""
        where_order_stmt = ""
        week_start_offset = 8 - int(self.env['res.lang']._lang_get(self.env.user.lang).week_start)
        daily_where_stmt = ""
        daily_order_stmt = ""
        if has_intialize_data:
            start_date, end_date = self.get_period_dates(demand_type='recompute')
            where_stmt = "WHERE week_end_date >= '{}' AND week_end_date <= '{}'".format(start_date, end_date)
            daily_where_stmt = "WHERE date_order >= (CURRENT_DATE - interval '30 days')::date AND date_order <= CURRENT_DATE"
            where_order_stmt = "AND date_order::date >= '{}' AND date_order::date <= '{}'".format(start_date, end_date)
            daily_order_stmt = "AND date_order::date >= (CURRENT_DATE - interval '30 days')::date AND date_order::date <= CURRENT_DATE"
        query_actual_demand_stmt = """
            DELETE FROM actual_sales_demand {where_stmt};
            INSERT INTO actual_sales_demand (week_end_date, product_id, partner_id, sale_qty, sale_uom_id)
            SELECT (date_trunc('week', date_order + {interval})::date - {interval} + interval '6 days')::date as week_end_date,
                product_id, partner_id, SUM(sale_qty) as sale_qty, sale_uom_id
            FROM actual_daily_sales_demand demand
            GROUP BY date_trunc('week', date_order + {interval})::date - {interval}, product_id, partner_id, sale_uom_id
            ORDER BY week_end_date desc;
        """.format(where_stmt=where_stmt, interval=week_start_offset, where_order_stmt=where_order_stmt)

        query_daily_demand_stmt = """
            DELETE FROM actual_daily_sales_demand {where_stmt};
            INSERT INTO actual_daily_sales_demand (date_order, product_id, partner_id, sale_qty, sale_uom_id)
            SELECT so.date_order::date as date_order,
                sol.product_id, so.partner_id, SUM(sol.product_uom_qty) as sale_qty, suom.id as sale_uom_id
            FROM sale_order_line sol
            JOIN (
                SELECT id, date_order, partner_id
                FROM sale_order
                WHERE state IN ('sale', 'done') {where_order_stmt}
            ) so ON sol.order_id = so.id
            JOIN uom_uom suom ON sol.product_uom = suom.id
            GROUP BY so.date_order::date, sol.product_id, so.partner_id, suom.id
            ORDER BY date_order desc;
        """.format(where_stmt=daily_where_stmt, where_order_stmt=daily_order_stmt)

        query_stmt = query_daily_demand_stmt + query_actual_demand_stmt
        self.env.cr.execute(query_stmt)
        # Update parameter
        if not has_intialize_data:
            params.set_param('phd_demand_forecast.has_initialized_data', 'True')
        params.set_param('phd_demand_forecast.last_updated',
                         datetime.now(pytz.utc).strftime(DEFAULT_SERVER_DATETIME_FORMAT))

    @api.model
    def get_sales_demand_query_stmt(self, product_id, demand_type='actual'):
        if not product_id:
            raise UserError(_("Product ID is invalid."))
        start_date, end_date = self.get_period_dates(demand_type)
        query_stmt = """
            SELECT ts.week_end_date, COALESCE(demand_qty, 0) as demand_qty
            FROM (
                SELECT ts::date as week_end_date
                FROM generate_series('{start_date}', '{end_date}', '7 day'::interval) ts) ts
            LEFT JOIN (
                SELECT week_end_date, ROUND(COALESCE(SUM(demand_qty), 0)::numeric, rounding::int) as demand_qty
                FROM
                    (SELECT week_end_date,
                         (CASE WHEN suom.factor = 0 OR suom.factor IS NULL
                            THEN demand.sale_qty
                            ELSE (demand.sale_qty * COALESCE(puom.factor, 1) / suom.factor) END) as demand_qty,
                        -log(puom.rounding) as rounding
                    FROM (
                        SELECT *
                        FROM actual_sales_demand
                        WHERE product_id = {product_id}
                            AND week_end_date >= '{start_date}' AND week_end_date <= '{end_date}') demand
                        JOIN product_product pp ON demand.product_id = pp.id
                        JOIN product_template pt ON pp.product_tmpl_id = pt.id
                        JOIN uom_uom puom ON pt.uom_id = puom.id
                        JOIN uom_uom suom ON demand.sale_uom_id = suom.id
                    WHERE puom.category_id = suom.category_id) t
                GROUP BY week_end_date, rounding
            ) actual_demand ON ts.week_end_date = actual_demand.week_end_date
            ORDER BY week_end_date ASC;
        """.format(start_date=start_date, end_date=end_date, product_id=product_id)
        return query_stmt

    @api.model
    def get_sales_demand(self, product_id, demand_type='actual'):
        """
        Get sales demand of product in the past
        :param product_id: id of product which will be forecasted
        :param demand_type: `actual` or `historical`
        :return: a dictionary contains the data for sales demand
        """
        query_stmt = self.get_sales_demand_query_stmt(product_id, demand_type)
        self.env.cr.execute(query_stmt)
        result = self.env.cr.dictfetchall()
        week_numbers = [i for i in range(-4, 13) if i != 0]
        week_index = 0
        for period in result:
            period['week'] = week_numbers[week_index]
            week_index += 1
        return result

    @api.model
    def get_forecasted_demand_query_stmt(self, product_id):
        if not product_id:
            raise UserError(_("Product ID is invalid."))
        start_date, end_date = self.get_period_dates(demand_type='forecast')
        # Query data
        query_stmt = """
            SELECT ts.week_end_date, COALESCE(demand_qty, 0) as forecasted_demand_qty
            FROM (
                SELECT ts::date as week_end_date
                FROM generate_series('{start_date}', '{end_date}', '7 day'::interval) ts) ts
            LEFT JOIN (
                SELECT week_end_date, sum(demand_qty) as demand_qty
                FROM demand_forecast_item
                WHERE product_id = {product_id} AND week_end_date >= '{start_date}' AND week_end_date <= '{end_date}'
                GROUP BY week_end_date
            ) demand ON ts.week_end_date = demand.week_end_date
            ORDER BY week_end_date asc;
        """.format(product_id=product_id, start_date=start_date, end_date=end_date)
        return query_stmt

    @api.model
    def get_forecasted_demand(self, product_id):
        """
        Get imported forecasted demand data
        :param product_id: id of product which will be forecasted
        :return: Dictionary contains forecasted demand data for 16 week from week #-4 to week #12
        """
        query_stmt = self.get_forecasted_demand_query_stmt(product_id)
        self.env.cr.execute(query_stmt)
        result = self.env.cr.dictfetchall()
        week_numbers = [i for i in range(-4, 13) if i != 0]
        week_index = 0
        for period in result:
            period['week'] = week_numbers[week_index]
            week_index += 1
        return result

    @api.model
    def get_period_dates(self, demand_type='actual'):
        today = datetime.now(pytz.utc).date()
        week_start_offset = 8 - int(self.env['res.lang']._lang_get(self.env.user.lang).week_start)
        base_date = today + relativedelta(days=week_start_offset)
        # The end date of last week
        last_week_end_date = base_date - relativedelta(days=base_date.weekday() + week_start_offset + 1)
        if demand_type == 'actual':
            # Last 4 weeks
            start_date = last_week_end_date - relativedelta(weeks=3)
            end_date = last_week_end_date
        elif demand_type == 'historical':
            # Retrieve 16 weeks of last year with the same week number of forecasted demand in this year
            first_start_date = last_week_end_date - relativedelta(weeks=3)
            week_number = first_start_date.isocalendar()[1]
            year_number = first_start_date.isocalendar()[0]
            last_start_date = datetime.strptime('{} {} 1'.format(year_number - 1, week_number, 1), '%G %V %u').date()
            last_base_date = last_start_date + relativedelta(days=week_start_offset)
            start_date = last_base_date - relativedelta(days=last_base_date.weekday() + week_start_offset - 6)
            end_date = start_date + relativedelta(weeks=15)
        elif demand_type == 'forecast':
            # Retrieve 16 weeks of this year in the chart
            start_date = last_week_end_date - relativedelta(weeks=3)
            end_date = start_date + relativedelta(weeks=15)
        else:
            end_date = last_week_end_date
            start_date = end_date - relativedelta(weeks=4, days=-1)
        return start_date, end_date

    @api.model
    def get_open_mo_query_stmt(self, product_id):
        query_stmt = """
            SELECT mo.id, product_id, mo.name, mo.date_planned_finished,
                ROUND((CASE WHEN muom.factor = 0 OR muom.factor IS NULL
                          THEN mo.product_qty
                          ELSE (mo.product_qty * COALESCE(puom.factor, 1) / muom.factor) END)::numeric, -log(puom.rounding)::int) as quantity
            FROM (
                SELECT id, name, product_id, product_qty, product_uom_id, date_planned_finished
                FROM mrp_production
                WHERE product_id={} AND state not in ('done', 'cancel')
            ) mo JOIN product_product pp ON mo.product_id = pp.id
            JOIN product_template pt ON pp.product_tmpl_id = pt.id
            JOIN uom_uom puom ON pt.uom_id = puom.id
            JOIN uom_uom muom ON mo.product_uom_id = muom.id
            ORDER BY mo.date_planned_finished asc
        """.format(product_id)
        return query_stmt

    @api.model
    def get_open_manufacturing_orders(self, product_id):
        if not product_id:
            return {}
        query_stmt = self.get_open_mo_query_stmt(product_id)
        self.env.cr.execute(query_stmt)
        result = self.env.cr.dictfetchall()
        return result

    @api.model
    def get_open_so_query_stmt(self, product_id):
        query_stmt = """
            SELECT so.id, so.name, osol.product_id, so.partner_id, rp.name as partner_name, so.commitment_date, osol.quantity
            FROM (
                SELECT sol.order_id, sol.product_id,
                   SUM(ROUND((CASE WHEN suom.factor = 0 OR suom.factor IS NULL
                               THEN move.product_uom_qty
                               ELSE (move.product_uom_qty * COALESCE(puom.factor, 1) / suom.factor) END)::numeric, -log(puom.rounding)::int)) as quantity
                FROM (
                    SELECT sm.product_uom_qty, sm.product_uom, sm.sale_line_id
                    FROM (
                        SELECT product_uom_qty, product_uom, sale_line_id, picking_type_id
                        FROM stock_move
                        WHERE sale_line_id IS NOT NULL
                            AND state not in ('cancel', 'done')
                            AND product_id = {product_id}) sm
                    JOIN (
                        SELECT id
                        FROM stock_picking_type
                        WHERE code='outgoing'
                    ) spt ON sm.picking_type_id = spt.id
                ) move
                    JOIN (
                        SELECT id, order_id, product_id
                        FROM sale_order_line
                        WHERE state NOT IN ('draft', 'sent', 'cancel')
                            AND product_id = {product_id}
                    ) sol ON move.sale_line_id = sol.id
                    JOIN product_product pp ON sol.product_id = pp.id
                    JOIN product_template pt ON pp.product_tmpl_id = pt.id
                    JOIN uom_uom puom ON pt.uom_id = puom.id
                    JOIN uom_uom suom ON move.product_uom = suom.id
                GROUP BY sol.order_id, sol.product_id
            ) osol 
            JOIN sale_order so ON osol.order_id = so.id
            JOIN res_partner rp ON rp.id = so.partner_id
            ORDER BY so.commitment_date asc
        """.format(product_id=product_id)
        return query_stmt

    @api.model
    def get_open_sale_orders(self, product_id):
        if not product_id:
            return {}
        query_stmt = self.get_open_so_query_stmt(product_id)
        self.env.cr.execute(query_stmt)
        result = self.env.cr.dictfetchall()
        return result

    def __get_quantity_on_hand(self):
        return self.float_format(self.product_id.qty_available)

    def __get_quantity_available(self):
        return self.float_format(self.product_id.free_qty)

    def __get_quantity_in_open_mos(self):
        open_mos_data = self.open_mos_data or {}
        if not len(open_mos_data):
            open_mos_data = self.get_open_manufacturing_orders(self.product_id.id)
        open_mos = [row.get('quantity', 0) for row in open_mos_data]
        return self.float_format(sum(open_mos))

    def __get_quantity_in_open_sos(self):
        open_sos_data = self.open_sos_data or {}
        if not len(open_sos_data):
            open_sos_data = self.get_open_manufacturing_orders(self.product_id.id)
        open_sos = [row.get('quantity', 0) for row in open_sos_data]
        return self.float_format(sum(open_sos))

    def get_quantity_description(self):
        res_lst = list()
        if self.product_id.type == 'product':
            res_lst.append(format_quantity_description_data("On Hand", self.__get_quantity_on_hand()))
            res_lst.append(format_quantity_description_data("Available", self.__get_quantity_available()))
        res_lst.append(format_quantity_description_data("Under Production", self.__get_quantity_in_open_mos()))
        res_lst.append(format_quantity_description_data("In Sales", self.__get_quantity_in_open_sos()))
        return res_lst

    def _get_header_content(self):
        quantity_description = self.get_quantity_description()
        product_id = self.product_id
        return format_header_data(product_id.id, product_id._name, product_id.display_name, quantity_description,
                                  self.get_last_updated_time(), product_id.uom_id.name)

    def _get_chart_content(self):
        product_id = self.product_id.id
        actual_demand = self.get_sales_demand(product_id, 'actual')
        historical_demand = self.get_sales_demand(product_id, 'historical')
        forecasted_demand = self.get_forecasted_demand(product_id)
        labels, tooltip_extend_labels = [], []
        if len(actual_demand) != 0 and len(historical_demand) != 0 and len(forecasted_demand) != 0:
            max_week = max(actual_demand[-1].get('week'), historical_demand[-1].get('week'),
                           forecasted_demand[-1].get('week'))
            min_week = max(actual_demand[0].get('week'), historical_demand[0].get('week'),
                           forecasted_demand[0].get('week'))
            labels = list(map(lambda x: f'Week {x if x < 0 else x + 1}', range(min_week, max_week)))
            tooltip_extend_labels = [format_datetime(x['week_end_date']) for x in forecasted_demand]

        self.forecasted_demand = forecasted_demand
        self.labels = labels
        chart_type = 'line'
        element_config = [
            graph.get_chart_element_config('Actual',
                                           list(map(lambda x: (x.get('demand_qty')), actual_demand)),
                                           color.ACTUAL_DEMAND_COLOR, fill=False, chart_type=chart_type),
            graph.get_chart_element_config('Forecasted',
                                           list(map(lambda x: (x.get('forecasted_demand_qty')),
                                                    forecasted_demand)),
                                           color.FORECASTED_DEMAND_COLOR, fill=False, chart_type=chart_type),
            graph.get_chart_element_config('Historical', list(
                map(lambda x: (x.get('demand_qty')), historical_demand)),
                                           color.HISTORICAL_DEMAND_COLOR, fill=False, chart_type=chart_type),
        ]
        title_config = graph.get_chart_title_config("Forecasted Demand Chart", fontColor='#FFB800', display=False)
        legend_config = graph.get_chart_legend_config(position='top')
        tooltip_config = graph.get_chart_tooltip_config(display_mode='index')
        x_axis = graph.get_chart_axis_config(stacked=False)
        y_axis = graph.get_chart_axis_config(stacked=False)
        chart_config = graph.get_chart_config_from(chart_type='line', element_configs=element_config,
                                                   title_config=title_config, legend_config=legend_config,
                                                   tooltip_config=tooltip_config, axis_labels=labels,
                                                   tooltip_extend_labels=tooltip_extend_labels,
                                                   x_axis_configs=x_axis, y_axis_configs=y_axis)

        return format_body_data(chart_config)

    def _get_table_contents(self):
        table_lst = list()
        table_lst.append(self._get_forecasted_table_content())
        table_lst.append(self._get_mos_table_content())
        table_lst.append(self._get_sos_table_content())
        return table_lst

    def _get_forecasted_table_content(self, ):
        # Extract Header
        week_key, forecasted_date_key, forecasted_demand_key = 'week_key', 'forecasted_date', 'forecasted_demand'
        headers = {
            **format_header_cell(week_key, 'Week #', sequence=1),
            **format_header_cell(forecasted_date_key, 'Date', sequence=2),
            **format_header_cell(forecasted_demand_key, 'Forecasted Demand', is_number=True, sequence=3)
        }

        forecasted_demand = self.forecasted_demand or {}
        if not len(forecasted_demand):
            forecasted_demand = self.get_sales_demand(self.product_id.id, 'historical')
        # Extract Content
        labels = self.labels
        if not labels:
            labels = ['' for _ in range(len(forecasted_demand))]
        content = [{
            week_key: format_content_cell(label),
            forecasted_date_key: format_content_cell(format_datetime(row.get('week_end_date'))),
            forecasted_demand_key: format_content_cell(self.float_format(row.get('forecasted_demand_qty')))
        } for row, label in zip(forecasted_demand, labels)] or {}
        return format_table_data("Forecasted Demand", "None", headers, content, size=4)

    def _get_mos_table_content(self):
        # Extract Header
        mo_nbr, mo_qty, mo_ready_date = 'mo_number', 'mo_qty', 'mo_ready_date'
        headers = dict()
        headers = {**headers,
                   **format_header_cell(mo_nbr, 'MO#', is_clickable=True, sequence=1),
                   **format_header_cell(mo_qty, 'Quantity', is_number=True, sequence=2),
                   **format_header_cell(mo_ready_date, 'Ready Date', sequence=3)
                   }
        # Extract Content
        open_mos_data = self.get_open_manufacturing_orders(self.product_id.id)
        self.open_mos_data = open_mos_data
        content = [{
            mo_nbr: format_content_cell(row.get('name'), row.get('id')),
            mo_qty: format_content_cell(self.float_format(row.get('quantity'))),
            mo_ready_date: format_content_cell(format_datetime(row.get('date_planned_finished')))
        } for row in open_mos_data] or {}
        return format_table_data("Open MOs", "mrp.production", headers, content, size=4)

    def _get_sos_table_content(self):
        # Extract Header
        customer_key, so_nbr_key, so_qty_key, so_confirmed_key = 'customer', 'so_number', 'so_qty', 'so_confirmed_date'
        headers = dict()
        headers = {**headers,
                   **format_header_cell(customer_key, 'Customer', is_clickable=True, sequence=2),
                   **format_header_cell(so_nbr_key, 'SO#', is_clickable=True, sequence=1),
                   **format_header_cell(so_qty_key, 'Quantity', is_number=True, sequence=3),
                   **format_header_cell(so_confirmed_key, 'Commitment Date', sequence=4)
                   }
        # Extract Content
        open_sos_data = self.get_open_sale_orders(self.product_id.id)
        self.open_sos_data = open_sos_data
        content = [{
            customer_key: format_content_cell(row.get('partner_name'), row.get('partner_id'),
                                              **{'model': 'res.partner'}),
            so_nbr_key: format_content_cell(row.get('name'), row.get('id')),
            so_qty_key: format_content_cell(self.float_format(row.get('quantity'))),
            so_confirmed_key: format_content_cell(format_datetime(row.get('commitment_date')))
        } for row in open_sos_data] or {}
        return format_table_data("Open SOs", "sale.order", headers, content, size=4)

    def get_initial_request_data(self):
        if self._context.get('report_product_id', False):
            self.product_id = self.env['product.product'].browse(self._context.get('report_product_id', -1))
            # self.factor = int(abs(log10(self.product_id.uom_id.rounding)))
            self.float_format = lambda number: f'{number:,.{self.factor}f}'
        else:
            raise UserError(_('Please provide specific product!'))

    @api.model
    def get_forecasted_report_data(self):
        self.get_initial_request_data()
        body = self._get_chart_content()
        footer = self._get_table_contents()
        header = self._get_header_content()

        config = format_report_data(header, body, footer)
        config['formatFactor'] = self.factor
        return config
