from odoo import api, fields, models, _
from datetime import datetime, date, timedelta
from odoo.addons.l10n_custom_dashboard.utils.graph_setting import get_chartjs_setting, get_linechart_format, \
    get_barchart_format, get_info_data, get_chart_json
from odoo.addons.account_dashboard.utils.graph_utils import get_json_render, get_json_data_for_selection, \
    get_data_for_graph, append_data_fetch_to_list
from odoo.addons.account_dashboard.utils.time_utils import get_list_period_by_type, get_start_end_date_value, BY_DAY, \
    BY_WEEK, BY_MONTH, BY_QUARTER, BY_YEAR, BY_FISCAL_YEAR
from odoo.addons.account_dashboard.utils.utils import get_list_companies_child
import json
import pytz
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, float_compare
from dateutil.relativedelta import relativedelta
from ..utils.utils import format_percentage, format_currency, get_short_currency_amount
import pytz

PRIMARY_GREEN = "#00A09D"
PRIMARY_PURPLE = "#875a7b"
PRIMARY_ORANGE = "#f19848"
PRIMARY_BLUE = "#649ce7"

COLOR_SALE_PAST = PRIMARY_PURPLE
COLOR_SALE_FUTURE = PRIMARY_GREEN
SALE_ORDER = 'sale_order'
PURCHASE_ORDER = 'purchase_order'
BANK = 'bank'
UPCOMING_NEXT_WEEK = 'upcoming_next_week'

GRAPH_CONFIG = {
    SALE_ORDER: {'type': 'line', 'function': 'retrieve_sale_order'},
    BANK: {'type': 'horizontalBar', 'function': ''},
    UPCOMING_NEXT_WEEK: {'type': 'horizontalBar', 'function': ''},
    PURCHASE_ORDER: {'type': 'line', 'function': 'retrieve_purchase_order'},
}


class PHDReportDashboard(models.Model):
    _name = "phd.report.dashboard"
    _inherit = "usa.journal"
    _description = "PHD Dashboard Management"

    type_element = [
        (SALE_ORDER, _('Sale Orders')),
        (BANK, _('Bank')),
        (UPCOMING_NEXT_WEEK, _('Upcomings Next Week')),
        (PURCHASE_ORDER, _('Purchase Orders')),
    ]

    # Upcoming
    number_upcomming_mo_ids = fields.Integer('Number of Absent Employees today', compute='_compute_number_upcomming_mo')
    number_upcomming_po_ids = fields.Integer('Number of Absent Employees today', compute='_compute_number_upcomming_po')
    upcoming_mo = fields.Html(string='Upcoming MOs', sanitize=False, compute='_compute_upcoming_mo')
    upcoming_po = fields.Html(string='Upcoming POs', sanitize=False, compute='_compute_upcoming_po')


    def _compute_number_upcomming_mo(self):
        date_form = fields.datetime.today()
        date_to = date_form + timedelta(days=7)
        mo_ids = self.env['mrp.production'].search(
            [('state', 'not in', ['done', 'cancel']), ('date_planned_finished', '>=', date_form),
             ('date_planned_finished', '<=', date_to)], order="date_planned_finished desc")
        number = len(mo_ids)
        for record in self:
            record.number_upcomming_mo_ids = number

    def _compute_number_upcomming_po(self):
        date_form = fields.datetime.today()
        date_to = date_form + timedelta(days=7)
        po_ids = self.env['purchase.order'].search(
            [('state', 'not in', ['done', 'cancel']), ('date_planned', '>=', date_form),
             ('date_planned', '<=', date_to)], order="date_planned desc")
        number = len(po_ids)
        for record in self:
            record.number_upcomming_po_ids = number

    def button_see_all_upcoming_mo(self):
        self.ensure_one()
        date_form = fields.datetime.today()
        date_to = date_form + timedelta(days=7)
        action = {
            'name': 'Manufacturing Orders',
            'res_model': 'mrp.production',
            'type': 'ir.actions.act_window',
            'view_mode': 'tree',
            'view_id': self.env.ref('phd_report_dashboard.phd_mrp_production_tree_view_inherit').id,
            'target': 'current',
            'domain': [('state', 'not in', ['done', 'cancel']),('date_planned_finished', '>=', date_form),
             ('date_planned_finished', '<=', date_to)],
        }
        return action

    def button_see_all_upcoming_po(self):
        self.ensure_one()
        date_form = fields.datetime.today()
        date_to = date_form + timedelta(days=7)
        action = {
            'name': 'Purchase Orders',
            'res_model': 'purchase.order',
            'type': 'ir.actions.act_window',
            'view_mode': 'tree',
            'view_id': self.env.ref('phd_report_dashboard.phd_purchase_order_tree_inherit').id,
            'target': 'current',
            'domain': [('state', 'not in', ['done', 'cancel']), ('date_planned', '>=', date_form),
             ('date_planned', '<=', date_to)],
        }
        return action

    def _compute_upcoming_mo(self):
        date_form = fields.datetime.today()
        date_to = date_form + timedelta(days=7)
        mo_ids = self.env['mrp.production'].search(
            [('state', 'not in', ['done', 'cancel']), ('date_planned_finished', '>=', date_form),
             ('date_planned_finished', '<=', date_to)], order="date_planned_finished desc")
        if mo_ids:
            html_template = """
                                        <div class="upcoming-date border-item o_dashboard_item_detail"
                                            data-record-id={id} data-record-model='mrp.production'>
                                           <div class="date-container">
                                               <div class="date">
                                                   <div class="month">{month}</div>
                                                   <div class="day">{day}</div>
                                               </div>
                                           </div>
                                           <div class="name">
                                                <span class="bold-text">{name}</span>
                                                <br>
                                                <span>{default_code}</span>         
                                                <span style='float:right;'>{quantity} {unit}</span>                                                
                                           </div>
                                       </div>
                                   """

            html = '<div class="list-box">'
            for mo in mo_ids:
                html += html_template.format(month=mo.date_planned_finished.strftime("%b"),
                                             day=mo.date_planned_finished.day,
                                             name=mo.name,
                                             default_code=mo.product_id.default_code if mo.product_id.default_code else '',
                                             quantity=mo.product_qty, unit=mo.product_uom_id.name,id=mo.id)
            html += '</div>'
        else:
            html = '<div class="mt-3">There is no upcoming MOs.</div>'

        for record in self:
            record.upcoming_mo = html

    def _compute_upcoming_po(self):
        date_form = fields.datetime.today()
        date_to = date_form + timedelta(days=7)
        po_ids = self.env['purchase.order'].search(
            [('state', 'not in', ['done', 'cancel']), ('date_planned', '>=', date_form),
             ('date_planned', '<=', date_to)], order="date_planned desc")
        if po_ids:
            html_template = """     
            
                                                <div class="upcoming-date border-item o_dashboard_item_detail" style="cursor: pointer;" 
                                                        data-record-id={id} data-record-model='purchase.order'>
                                                   <div class="date-container">
                                                       <div class="date">
                                                           <div class="month">{month}</div>
                                                           <div class="day">{day}</div>
                                                       </div>
                                                   </div>
                                                   <div class="name">
                                                        <span class="bold-text">{name}</span>
                                                        <span style='float:right;'>{vendor}</span>
                                                   </div>
                                               </div>
                                           """

            html = '<div class="list-box">'
            for po in po_ids:
                html += html_template.format(month=po.date_planned.strftime("%b"),
                                             day=po.date_planned.day,
                                             name=po.name,vendor=po.partner_id.name,id=po.id)
            html += '</div>'
        else:
            html = '<div class="mt-3">There is no upcoming POs.</div>'

        for record in self:
            record.upcoming_po = html

    def _format_amount(self, amount, currency):
        fmt = "%.{0}f".format(currency.decimal_places)
        lang = self.env['res.lang']._lang_get(self.env.context.get('lang') or 'en_US')
        res = lang.format(fmt, currency.round(amount), grouping=True, monetary=True) \
            .replace(r' ', u'\N{NO-BREAK SPACE}').replace(r'-', u'-\N{ZERO WIDTH NO-BREAK SPACE}')

        if currency and currency.symbol:
            if currency.position == 'after':
                res = '%s %s' % (res, currency.symbol)
            elif currency and currency.position == 'before':
                res = '%s %s' % (currency.symbol, res)
        return res

    type = fields.Selection(type_element, required=True)
    kanban_bank_dashboard = fields.Text(compute='_compute_kanban_bank_dashboard', store=False)

    @api.depends()
    def compute_account_dashboard_graph(self):
        for record in self:
            graph_data = None
            extend_mode = None
            selection = []
            extra_param = []
            if record.type == SALE_ORDER:
                extend_mode, graph_data = record.get_general_kanban_section_data()
                get_json_data_for_selection(record, selection, record.period_by_complex, record.default_period_complex)

            if record.type == PURCHASE_ORDER:
                extend_mode, graph_data = record.get_general_kanban_section_data()
                get_json_data_for_selection(record, selection, record.period_by_complex, record.default_period_complex)

            if record.type == BANK:
                extend_mode, graph_data = record.get_bar_by_category_graph_data()

            if record.type == UPCOMING_NEXT_WEEK:
                extend_mode, graph_data = record.get_bar_by_category_graph_data()

            if graph_data:
                graph_type = GRAPH_CONFIG[record.type].get('type', '')
                function_retrieve = GRAPH_CONFIG[record.type].get('function', '')
                record.account_dashboard_graph_dashboard_graph = json.dumps(
                    get_json_render(graph_type, False, '', graph_data, record.type, selection, function_retrieve,
                                    extra_param))
                record.extend_data = extend_mode

    @api.model
    def retrieve_sale_order(self, date_from, date_to, period_type):
        """ API is used to response untaxed amount of all invoices in system that get
        from account_invoice.
        :param date_from: the start date to summarize data, have type is datetime
        :param date_to: the end date to summarize data, that have type is datetime
        :param period_type: is type of period to summarize data, we have 4 selections are
                ['week', 'month', 'quarter', 'year']
        :return: Json
        """
        date_from = datetime.strptime(date_from, '%Y-%m-%d')
        date_from = datetime(date_from.year, date_from.month, date_from.day, 0, 0, 0)
        date_to = datetime.strptime(date_to, '%Y-%m-%d')
        date_to = datetime(date_to.year, date_to.month, date_to.day, 23, 59, 59)
        periods = get_list_period_by_type(self, date_from, date_to, period_type)
        timezone = self.env.user.partner_id.tz or pytz.utc.zone

        currency = """
                SELECT c.id, COALESCE((
                    SELECT r.rate
                    FROM res_currency_rate r
                    WHERE r.currency_id = c.id AND r.name <= %s AND (r.company_id IS NULL OR r.company_id IN %s)
                    ORDER BY r.company_id, r.name DESC
                    LIMIT 1), 1.0) AS rate
                FROM res_currency c
            """

        transferred_currency = """
                SELECT ai.sales_order_date, c.rate * ai.price_subtotal AS amount_tran, state, company_id
                FROM sale_order_line AS ai
                    LEFT JOIN ({currency_table}) AS c ON ai.currency_id = c.id
            """.format(currency_table=currency)

        query = """ 
                SELECT date_part('year', (( aic.sales_order_date::timestamp) AT TIME ZONE 'UTC') AT TIME ZONE %s) AS year,
                    date_part(%s, (( aic.sales_order_date::timestamp) AT TIME ZONE 'UTC') AT TIME ZONE %s) AS period,
                    MIN((( aic.sales_order_date::timestamp) AT TIME ZONE 'UTC') AT TIME ZONE %s) AS date_in_period,
                    SUM(aic.amount_tran) AS amount_untaxed
                FROM ({transferred_currency_table}) AS aic
                WHERE (( aic.sales_order_date::timestamp) AT TIME ZONE 'UTC') AT TIME ZONE %s >= %s AND
                    (( aic.sales_order_date::timestamp) AT TIME ZONE 'UTC') AT TIME ZONE %s <= %s AND
                    (aic.state = 'sale' OR aic.state = 'done') AND
                    aic.company_id IN %s
                GROUP BY year, period
                ORDER BY year, date_in_period, period;
            """.format(transferred_currency_table=transferred_currency)

        company_ids = get_list_companies_child(self.env.company)
        name = fields.Date.today()
        self.env.cr.execute(query, (
        timezone, period_type, timezone, timezone, name, tuple(company_ids), timezone, date_from, timezone, date_to,
        tuple(company_ids),))
        data_fetch = self.env.cr.dictfetchall()

        data_list = [[], []]
        graph_label = []
        index = 0
        total_sales = 0

        today = date.today()
        for data in data_fetch:
            while not (periods[index][0] <= data['date_in_period'].date() <= periods[index][1]) and index < len(
                    periods):
                values = [
                    0 if periods[index][0] <= today else 'NaN',
                    0 if periods[index][1] >= today else 'NaN'
                ]
                append_data_fetch_to_list(data_list, graph_label, periods, period_type, index, values=values)
                index += 1

            if index < len(periods):
                value = data.get('amount_untaxed', False)
                values = [
                    value if not isinstance(value, bool) and periods[index][0] <= today else 'NaN',
                    value if not isinstance(value, bool) and periods[index][1] >= today else 'NaN'
                ]
                total_sales += value if value else 0
                append_data_fetch_to_list(data_list, graph_label, periods, period_type, index, values=values)
                index += 1

        while index < len(periods):
            values = [
                0 if periods[index][0] <= today else 'NaN',
                0 if periods[index][1] >= today else 'NaN'
            ]
            append_data_fetch_to_list(data_list, graph_label, periods, period_type, index, values=values)
            index += 1

        graph_data = [
            get_linechart_format(data=data_list[0], label=_('Sales'), color=COLOR_SALE_PAST),
            get_linechart_format(data=data_list[1], label=_('Future'), color=COLOR_SALE_FUTURE),
        ]

        info_data = [get_info_data(self, _('Total Amount'), total_sales)]

        return get_chart_json(graph_data, graph_label, get_chartjs_setting(chart_type='line'), info_data)

    @api.model
    def retrieve_purchase_order(self, date_from, date_to, period_type):
        """ API is used to response untaxed amount of all invoices in system that get
        from account_invoice.
        :param date_from: the start date to summarize data, have type is datetime
        :param date_to: the end date to summarize data, that have type is datetime
        :param period_type: is type of period to summarize data, we have 4 selections are
                ['week', 'month', 'quarter', 'year']
        :return: Json
        """
        date_from = datetime.strptime(date_from, '%Y-%m-%d')
        date_from = datetime(date_from.year, date_from.month, date_from.day, 0, 0, 0)
        date_to = datetime.strptime(date_to, '%Y-%m-%d')
        date_to = datetime(date_to.year, date_to.month, date_to.day, 23, 59, 59)
        periods = get_list_period_by_type(self, date_from, date_to, period_type)
        timezone = self.env.user.partner_id.tz or pytz.utc.zone

        currency = """
                    SELECT c.id, COALESCE((
                        SELECT r.rate
                        FROM res_currency_rate r
                        WHERE r.currency_id = c.id AND r.name <= %s AND (r.company_id IS NULL OR r.company_id IN %s)
                        ORDER BY r.company_id, r.name DESC
                        LIMIT 1), 1.0) AS rate
                    FROM res_currency c
                """

        transferred_currency = """
                    SELECT ai.order_date_approve, c.rate * ai.price_subtotal AS amount_tran, state, company_id
                    FROM purchase_order_line AS ai
                        LEFT JOIN ({currency_table}) AS c ON ai.currency_id = c.id
                """.format(currency_table=currency)

        query = """
                    SELECT date_part('year', (( aic.order_date_approve::timestamp) AT TIME ZONE 'UTC') AT TIME ZONE %s) AS year,
                        date_part(%s, (( aic.order_date_approve::timestamp) AT TIME ZONE 'UTC') AT TIME ZONE %s) AS period,
                        MIN((( aic.order_date_approve::timestamp) AT TIME ZONE 'UTC') AT TIME ZONE %s) AS date_in_period,
                        SUM(aic.amount_tran) AS amount_untaxed
                    FROM ({transferred_currency_table}) AS aic
                    WHERE (( aic.order_date_approve::timestamp) AT TIME ZONE 'UTC') AT TIME ZONE %s >= %s AND
                        (( aic.order_date_approve::timestamp) AT TIME ZONE 'UTC') AT TIME ZONE %s <= %s AND
                        (aic.state = 'purchase' OR aic.state = 'done') AND
                        aic.company_id IN %s
                    GROUP BY year, period
                    ORDER BY year, date_in_period, period;
                """.format(transferred_currency_table=transferred_currency)

        company_ids = get_list_companies_child(self.env.company)
        name = fields.Date.today()
        self.env.cr.execute(query, (
        timezone, period_type, timezone, timezone, name, tuple(company_ids), timezone, date_from, timezone, date_to,
        tuple(company_ids),))
        data_fetch = self.env.cr.dictfetchall()

        data_list = [[], []]
        graph_label = []
        index = 0
        total_sales = 0

        today = date.today()
        for data in data_fetch:
            while not (periods[index][0] <= data['date_in_period'].date() <= periods[index][1]) and index < len(
                    periods):
                values = [
                    0 if periods[index][0] <= today else 'NaN',
                    0 if periods[index][1] >= today else 'NaN'
                ]
                append_data_fetch_to_list(data_list, graph_label, periods, period_type, index, values=values)
                index += 1

            if index < len(periods):
                value = data.get('amount_untaxed', False)
                values = [
                    value if not isinstance(value, bool) and periods[index][0] <= today else 'NaN',
                    value if not isinstance(value, bool) and periods[index][1] >= today else 'NaN'
                ]
                total_sales += value if value else 0
                append_data_fetch_to_list(data_list, graph_label, periods, period_type, index, values=values)
                index += 1

        while index < len(periods):
            values = [
                0 if periods[index][0] <= today else 'NaN',
                0 if periods[index][1] >= today else 'NaN'
            ]
            append_data_fetch_to_list(data_list, graph_label, periods, period_type, index, values=values)
            index += 1

        graph_data = [
            get_linechart_format(data=data_list[0], label=_('Purchases'), color=COLOR_SALE_PAST),
            get_linechart_format(data=data_list[1], label=_('Future'), color=COLOR_SALE_FUTURE),
        ]

        info_data = [get_info_data(self, _('Total Amount'), total_sales)]

        return get_chart_json(graph_data, graph_label, get_chartjs_setting(chart_type='line'), info_data)

    def _compute_kanban_bank_dashboard(self):
        kanban_bank = []
        for record in self:
            if record.type == BANK:
                account_journals = self.env['account.journal'].search([('type', '=', 'bank')])
                if account_journals:
                    for account in account_journals:
                        cash_per_book = self._format_amount(account.get_balance_per_book(), self.company_id.currency_id)
                        kanban_bank.append({
                            'cash_per_book': cash_per_book,
                            'bank_name': account.name,
                        })
                    record.kanban_bank_dashboard = json.dumps(kanban_bank)
                else:
                    record.kanban_bank_dashboard = False
            else:
                record.kanban_bank_dashboard = False

    @api.model
    def phd_report_dashboard_header_render(self, new_user=True):
        kpi_json = {
            'kpi_data': []
        }
        date_to = fields.Datetime.now()
        date_from = date_to - relativedelta(years=1)
        #inventory valuation
        stock_valuation = self._get_stock_valuation(date_to, date_from)
        kpi_json['kpi_data'].append(stock_valuation)
        #Current A/R
        aged_receiable = self._get_aged_receivable(date_to, date_from)
        kpi_json['kpi_data'].append(aged_receiable)
        # Current A/P
        aged_payable = self._get_aged_payable(date_to, date_from)
        kpi_json['kpi_data'].append(aged_payable)
        return kpi_json

    def _get_stock_valuation(self, date_to, date_form):
        current_value = 0
        last_value = 0
        query = '''
                                    select sum(value) from stock_valuation_layer where account_move_id is not NULL and create_date <= '{date}'
                                '''.format(date=date_to.astimezone(pytz.utc).strftime(DEFAULT_SERVER_DATETIME_FORMAT))
        self._cr.execute(query)
        current_inventory_valuation = self._cr.dictfetchall()
        if current_inventory_valuation[0].get('sum', None) != None:
            current_value = current_inventory_valuation[0].get('sum')
        query = '''
                                    select sum(value) from stock_valuation_layer where account_move_id is not NULL and create_date <= '{date}'
                                '''.format(date=date_form.astimezone(pytz.utc).strftime(DEFAULT_SERVER_DATETIME_FORMAT))
        self._cr.execute(query)
        last_inventory_valuation = self._cr.dictfetchall()
        if last_inventory_valuation[0].get('sum', None) != None:
            last_value = last_inventory_valuation[0].get('sum')

        return self._get_data(date_to, date_form, current_value, last_value, label='Current Inventory Value',
                              main_icon='inventory_value')

    def _get_aged_receivable(self, date_to, date_form):
        current_value = 0
        last_value = 0
        results, current_total, amls = self.env['report.account.report_agedpartnerbalance']._get_partner_move_lines(
            ['receivable'], date_to, 'posted', 30)
        results, last_total, amls = self.env['report.account.report_agedpartnerbalance']._get_partner_move_lines(
            'receivable', date_form, 'posted', 30)
        if current_total:
            current_value = current_total[5]

        if last_total:
            last_value = last_total[5]

        return self._get_data(date_to, date_form, current_value, last_value, label='Current A/R', main_icon='current_ar')

    def _get_aged_payable(self, date_to, date_form):
        current_value = 0
        last_value = 0
        results, current_total, amls = self.env['report.account.report_agedpartnerbalance']._get_partner_move_lines(
            ['payable'], date_to, 'posted', 30)
        results, last_total, amls = self.env['report.account.report_agedpartnerbalance']._get_partner_move_lines(
            'payable', date_form, 'posted', 30)
        if current_total:
            current_value = abs(current_total[5])

        if last_total:
            last_value = abs(last_total[5])

        return self._get_data(date_to, date_form, current_value, last_value, label='Current A/P', main_icon='current_ap')


    def _get_data(self, date_to, date_form, current_value, last_value, label, main_icon):
        icon = 'no_change'
        current_formated = format_currency(self, current_value)
        minus_value = current_value - last_value
        if float_compare(minus_value, 0, precision_rounding=2) > 0:
            icon = 'up_green'
        elif float_compare(minus_value, 0, precision_rounding=2) < 0:
            icon = 'down_red'

        return {
            'label': '{label}'.format(label=label),
            'period_type': '{date_form} - {date_to}'.format(date_form=date_form.strftime('%m/%d/%Y'),
                                                            date_to=date_to.strftime('%m/%d/%Y')),
            'value': current_formated,
            'short_title': get_short_currency_amount(current_value, self.env.company.currency_id),
            'comparison': '{value} vs prior period'.format(
                value=get_short_currency_amount(abs(minus_value), self.env.company.currency_id)),
            'comparison_title': '{value} vs prior period'.format(value=format_currency(self, abs(minus_value))),
            'icon': '/phd_report_dashboard/static/src/img/{main_icon}.png'.format(main_icon=main_icon),
            'trend': '/phd_report_dashboard/static/src/img/{icon}.png'.format(icon=icon)
        }