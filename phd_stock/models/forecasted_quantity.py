from odoo import models, fields, api, _
from odoo.tools import float_compare
import json
import lxml.html

from odoo import models, fields, api, _
from odoo.tools import config
from odoo.tools.misc import format_date
from typing import Iterable, Any, Tuple


def signal_last(it: Iterable[Any]) -> Iterable[Tuple[bool, Any]]:
    iterable = iter(it)
    ret_var = next(iterable)
    for val in iterable:
        yield False, ret_var
        ret_var = val
    yield True, ret_var


def get_my_key(obj):
    return obj['product_sku']


class ForecastedQuantityReport(models.AbstractModel):
    _inherit = "account.report"
    _name = "phd.forecasted.quantity"
    _description = "Forecasted Quantity Report"

    filter_unfold_all = False

    @api.model
    def _get_templates(self):
        templates = super(ForecastedQuantityReport, self)._get_templates()
        templates['line_template'] = 'phd_stock.line_template_forecasted_quantity'
        templates['main_template'] = 'phd_stock.forecasted_main_template'
        templates['search_template'] = 'phd_stock.search_template_forecasted'
        return templates

    @api.model
    def _get_columns_name(self, options):
        return [
            {'name': ''},
            {'name': _('Source Document'), 'style': 'text-align:center'},
            {'name': _('Reference'), 'style': 'text-align:center'},
            {'name': _('Quantity Change'), 'class': 'number'},
            {'name': _('Quantity'), 'class': 'number'},
            {'name': _('On Hand'), 'class': 'number'},
            {'name': _('Date'), 'class': 'date'},
        ]

    @api.model
    def _get_report_name(self):
        return _("Forecasted Quantity")

    @api.model
    def _get_lines(self, options, line_id=None):
        if not options.get('default_location_id', False):
            return self._get_forecasted_quantity_lines(options, line_id)
        else:
            return self._get_forecasted_quantity_lines_report(options)

    @api.model
    def _get_forecasted_quantity_lines(self, options, line_id):
        date = fields.Date.today()
        lines = []
        if self._context.get('default_location_id', False):
            location_id = self._context.get('default_location_id')
            unfolded_lines = options.get('unfold_lines', False)
            if not line_id and not options.get('unfold_lines', False):
                product_results = self._do_query_stock_quant(self._context.get('default_location_id'))
                product_in_location = []
                for product in product_results:
                    product_in_location.append(product['product_id'])
                    stock_moves = self.env['stock.move'].search(
                        [('state', 'not in', ['done', 'cancel']), ('product_id.active', '=', True),
                         ('date_planned_end', '>=', date),
                         ('product_id', '=', int(product['product_id'])),
                         '|', ('location_id', '=', location_id), ('location_dest_id', '=', location_id)],
                        order='date_planned_end asc')
                    is_print, last_quantity, last_quantity_for_negative = self._is_print_or_show_on_view(product,
                                                                                                         location_id,
                                                                                                         stock_moves,
                                                                                                         float(product[
                                                                                                                   'sum']))
                    if self._context.get('is_negative_report', False):
                        if is_print:
                            line = self._get_product_title_line(options, product, last_quantity_for_negative, date,
                                                                False)
                            if line:
                                lines.append(line)
                    else:
                        line = self._get_product_title_line(options, product, last_quantity, date, False)
                        if line:
                            lines.append(line)

                move_out_location = self.env['stock.move'].search(
                    [('state', 'not in', ['done', 'cancel']), ('product_id.active', '=', True),
                     ('product_id', 'not in', product_in_location),
                     '|', ('location_id', '=', location_id), ('location_dest_id', '=', location_id)],
                    order='date_planned_end asc')
                for product in move_out_location.product_id:
                    stock_moves = self.env['stock.move'].search(
                        [('state', 'not in', ['done', 'cancel']), ('product_id.active', '=', True),
                         ('product_id', '=', product.id),
                         '|', ('location_id', '=', location_id), ('location_dest_id', '=', location_id)],
                        order='date_planned_end asc')
                    is_print, last_quantity, last_quantity_for_negative = self._is_print_or_show_on_view(
                        {'product_id': product.id, 'sum': 0}, location_id,
                        stock_moves, 0)
                    if self._context.get('is_negative_report', False):
                        if is_print:
                            line = self._get_product_title_line(options, {'product_id': product.id, 'sum': 0},
                                                                last_quantity_for_negative, date, False, True)
                            if line:
                                lines.append(line)
                    else:
                        line = self._get_product_title_line(options, {'product_id': product.id, 'sum': 0},
                                                            last_quantity, date, False, True)
                        if line:
                            lines.append(line)
            else:
                if unfolded_lines:
                    line_ids = unfolded_lines
                elif line_id:
                    line_ids = [line_id]
                else:
                    line_ids = []

                for id in line_ids:
                    not_in_location = False
                    product = {'product_id': id.split('_')[1], 'sum': id.split('_')[2]}
                    if len(id.split('_')) == 5 and id.split('_')[3] == 'out':
                        last_quantity = id.split('_')[4]
                        line = self._get_product_title_line(options, product, last_quantity, date, True, True)
                        if line:
                            lines.append(line)
                        not_in_location = True
                    else:
                        last_quantity = id.split('_')[3]
                        line = self._get_product_title_line(options, product, last_quantity, date, True)
                        if line:
                            lines.append(line)
                    quantity = float(product['sum'])
                    if len(id.split('_')) == 5 and id.split('_')[3] == 'out':
                        stock_moves = self.env['stock.move'].search(
                            [('state', 'not in', ['done', 'cancel']), ('product_id.active', '=', True),
                             ('product_id', '=', int(product['product_id'])),
                             '|', ('location_id', '=', location_id), ('location_dest_id', '=', location_id)],
                            order='date_planned_end asc')
                    else:
                        stock_moves = self.env['stock.move'].search(
                            [('state', 'not in', ['done', 'cancel']), ('product_id.active', '=', True),
                             ('date_planned_end', '>=', date),
                             ('product_id', '=', int(product['product_id'])),
                             '|', ('location_id', '=', location_id), ('location_dest_id', '=', location_id)],
                            order='date_planned_end asc')
                    if stock_moves:
                        for move in stock_moves:
                            quantity_change = self._get_product_qty_change_result(move, location_id)
                            quantity += quantity_change
                            if self._context.get('is_negative_report', False):
                                if quantity < move.product_id.safety_stock:
                                    lines.append(
                                        self._get_aml_move_line(move, product, quantity_change, last_quantity, quantity,
                                                                not_in_location=not_in_location))
                            else:
                                lines.append(
                                    self._get_aml_move_line(move, product, quantity_change, last_quantity, quantity,
                                                            not_in_location=not_in_location))
        # lines = lines.sort(key=get_my_key)
        return sorted(lines, key=lambda i: (i['product_sku']))

    @api.model
    def _get_forecasted_quantity_lines_report(self, options):
        date = fields.Date.today()
        lines = []
        if options.get('default_location_id', False):
            location_id = options.get('default_location_id', False)
            if not options.get('filter_accounts', False):
                product_results = self._do_query_stock_quant(location_id)
                product_in_location = []
                for product in product_results:
                    product_in_location.append(product['product_id'])

                    stock_moves = self.env['stock.move'].search(
                        [('state', 'not in', ['done', 'cancel']), ('product_id.active', '=', True),
                         ('date_planned_end', '>=', date),
                         ('product_id', '=', int(product['product_id'])),
                         '|', ('location_id', '=', location_id), ('location_dest_id', '=', location_id)],
                        order='date_planned_end asc')
                    is_print, last_quantity, last_quantity_for_negative = self._is_print_or_show_on_view(product,
                                                                                                         location_id,
                                                                                                         stock_moves,
                                                                                                         float(product[
                                                                                                                   'sum']))
                    if options.get('is_negative_report', False):
                        if is_print:
                            line = self._get_product_title_line(options, product, last_quantity_for_negative, date,
                                                                False)
                            if line:
                                lines.append(line)
                    else:
                        line = self._get_product_title_line(options, product, last_quantity, date, False)
                        if line:
                            lines.append(line)

                    quantity = float(product['sum'])
                    if stock_moves:
                        for move in stock_moves:
                            quantity_change = self._get_product_qty_change_result(move, location_id)
                            quantity += quantity_change
                            if options.get('is_negative_report', False):
                                if quantity < move.product_id.safety_stock:
                                    lines.append(self._get_aml_move_line(move, product, quantity_change, last_quantity,
                                                                         quantity))
                            else:
                                lines.append(
                                    self._get_aml_move_line(move, product, quantity_change, last_quantity, quantity))

                move_out_location = self.env['stock.move'].search(
                    [('state', 'not in', ['done', 'cancel']), ('product_id.active', '=', True),
                     ('product_id', 'not in', product_in_location),
                     '|', ('location_id', '=', location_id), ('location_dest_id', '=', location_id)],
                    order='date_planned_end asc')
                for product in move_out_location.product_id:
                    stock_moves = self.env['stock.move'].search(
                        [('state', 'not in', ['done', 'cancel']), ('product_id.active', '=', True),
                         ('product_id', '=', product.id),
                         '|', ('location_id', '=', location_id), ('location_dest_id', '=', location_id)],
                        order='date_planned_end asc')
                    is_print, last_quantity, last_quantity_for_negative = self._is_print_or_show_on_view(
                        {'product_id': product.id, 'sum': 0}, location_id,
                        stock_moves, 0)
                    if options.get('is_negative_report', False):
                        if is_print:
                            line = self._get_product_title_line(options, {'product_id': product.id, 'sum': 0},
                                                                last_quantity_for_negative, date, False,
                                                                True)
                            if line:
                                lines.append(line)
                    else:
                        line = self._get_product_title_line(options, {'product_id': product.id, 'sum': 0},
                                                            last_quantity, date, False, True)
                        if line:
                            lines.append(line)

                    quantity = 0
                    if stock_moves:
                        for move in stock_moves:
                            quantity_change = self._get_product_qty_change_result(move, location_id)
                            quantity += quantity_change
                            if options.get('is_negative_report', False):
                                if quantity < move.product_id.safety_stock:
                                    lines.append(
                                        self._get_aml_move_line(move, {'product_id': product.id, 'sum': 0},
                                                                quantity_change, last_quantity,
                                                                quantity))
                            else:
                                lines.append(
                                    self._get_aml_move_line(move, {'product_id': product.id, 'sum': 0}, quantity_change,
                                                            last_quantity, quantity))
            else:
                line_ids = options.get('filter_accounts', False)
                for line in line_ids:
                    product = {'product_id': line.split('_')[1], 'sum': line.split('_')[2]}
                    if len(line.split('_')) == 5 and line.split('_')[3] == 'out':
                        stock_moves = self.env['stock.move'].search(
                            [('state', 'not in', ['done', 'cancel']), ('product_id.active', '=', True),
                             ('product_id', '=', int(product['product_id'])),
                             '|', ('location_id', '=', location_id), ('location_dest_id', '=', location_id)],
                            order='date_planned_end asc')
                    else:
                        stock_moves = self.env['stock.move'].search(
                            [('state', 'not in', ['done', 'cancel']), ('product_id.active', '=', True),
                             ('date_planned_end', '>=', date),
                             ('product_id', '=', int(product['product_id'])),
                             '|', ('location_id', '=', location_id), ('location_dest_id', '=', location_id)],
                            order='date_planned_end asc')
                    is_print, last_quantity, last_quantity_for_negative = self._is_print_or_show_on_view(
                        {'product_id': int(product['product_id']), 'sum': float(product['sum'])}, location_id,
                        stock_moves, float(product['sum']))
                    if options.get('is_negative_report', False):
                        if is_print:
                            lines.append(
                                self._get_product_title_line(options, product, last_quantity_for_negative, date, True))
                    else:
                        lines.append(
                            self._get_product_title_line(options, product, last_quantity, date, True))

                    quantity = float(product['sum'])
                    if stock_moves:
                        for move in stock_moves:
                            quantity_change = self._get_product_qty_change_result(move, location_id)
                            quantity += quantity_change
                            if options.get('is_negative_report', False):
                                if quantity < move.product_id.safety_stock:
                                    lines.append(self._get_aml_move_line(move, product, quantity_change, last_quantity,
                                                                         quantity))
                            else:
                                lines.append(
                                    self._get_aml_move_line(move, product, quantity_change, last_quantity, quantity))
        return sorted(lines, key=lambda i: (i['product_sku']))

    @api.model
    def _is_print_or_show_on_view(self, product, location_id, stock_moves, quantity):
        safety_stock = 0
        is_print = False
        last_quantity = 0
        last_quantity_for_negative = 0
        if stock_moves:
            for move in stock_moves:
                quantity_change = self._get_product_qty_change_result(move, location_id)
                quantity += quantity_change
                if quantity < move.product_id.safety_stock:
                    safety_stock = move.product_id.safety_stock
                    is_print = True
                    last_quantity_for_negative = quantity
            last_quantity = quantity
        else:
            if product.get('product_id', False):
                product_product = self.env['product.product'].search([('id', '=', int(product['product_id']))], limit=1)
                if product_product:
                    safety_stock = product_product.safety_stock
        if not is_print:
            if float_compare(float(product['sum']), safety_stock, precision_digits=0) == -1:
                is_print = True
        return is_print, last_quantity, last_quantity_for_negative

    @api.model
    def _get_product_qty_change_result(self, move, location):
        if move.location_id.id == location:
            return - move.product_uom_qty
        elif move.location_dest_id.id == location:
            return move.product_uom_qty
        else:
            return 0

    @api.model
    def _get_aml_move_line(self, move, product, quantity_change, last_quantity, quantity, not_in_location=False):
        # mrp_order = self.env['mrp.production'].search([('name','=',move.origin)],limit=1)
        model = False
        record_id = False
        # Start Region These variable for Show MRP on WSI Report
        mrp_production_id = False
        # end Region
        if move.origin:
            if move.purchase_line_id:
                record_id = move.purchase_line_id.order_id.id
                model = move.purchase_line_id.order_id._name
                if move.mo_id:
                    mrp_production_id = move.mo_id
            elif move.sale_line_id:
                record_id = move.sale_line_id.order_id.id
                model = move.sale_line_id.order_id._name
            elif move.raw_material_production_id:
                record_id = move.raw_material_production_id.id
                model = move.raw_material_production_id._name
            elif move.production_id:
                record_id = move.production_id.id
                model = move.production_id._name
        else:
            if move.picking_id:
                record_id = move.picking_id.id
                model = move.picking_id._name
            elif move.inventory_id:
                record_id = move.inventory_id.id
                model = move.inventory_id._name
            elif move.raw_material_production_id:
                record_id = move.raw_material_production_id.id
                model = move.raw_material_production_id._name
            elif move.production_id:
                record_id = move.production_id.id
                model = move.production_id._name
        return {
            'id': move.id,
            'parent_id': 'product_%s_%s_out_%s' % (
            str(product['product_id']), str(product['sum']), last_quantity) if not_in_location
            else 'product_%s_%s_%s' % (str(product['product_id']), str(product['sum']), last_quantity),
            'name': '',
            'is_reference': True if record_id else False,
            'record_id': record_id,
            'model': model,
            # Start Region Show MRP on Report
            'is_show_mrp': True if mrp_production_id else False,
            'mrp_record_id': mrp_production_id.id if mrp_production_id else False,
            'mrp_name': "(%s)" % mrp_production_id.name if mrp_production_id else '',
            'mrp_model': 'mrp.production',
            # End Region
            'product_sku': move.product_id.default_code if move.product_id.default_code else '',
            'columns': [
                {'name': move.origin or move.reference, 'title': move.origin or move.reference,
                 'class': 'whitespace_print'},
                {'name': move.reference, 'title': move.reference, 'class': 'whitespace_print'},
                {'name': quantity_change, 'class': 'number'},
                {'name': quantity, 'class': 'number'},
                {'name': '', 'class': 'number'},
                {'name': format_date(self.env, move.date_planned_end), 'class': 'date'},
            ],
            'level': 4,
        }

    @api.model
    def _do_query_stock_quant(self, location_id):
        query = '''
                    SELECT product_id, sum(quantity) FROM stock_quant where location_id = '%s' GROUP BY product_id
                ''' % location_id
        self._cr.execute(query)
        return self._cr.dictfetchall()

    @api.model
    def _get_product_title_line(self, options, product, last_quantity, date, unfolded, not_in_location=False):
        product_info = self.env['product.product'].search([('id', '=', product['product_id'])])
        if product_info:
            if product_info.default_code:
                name = '[%s] %s' % (product_info.default_code, product_info.name)
            else:
                name = product_info.name
            if len(name) > 40 and not self._context.get('print_mode'):
                name = name[:40] + '...'
            return {
                'id': 'product_%s_%s_%s' % (str(product_info.id), str(product['sum']),
                                            last_quantity) if not not_in_location else 'product_%s_%s_%s_%s' % (
                str(product_info.id), str(product['sum']), 'out', last_quantity),
                'name': name,
                'title_hover': name,
                'product_sku': product_info.default_code if product_info.default_code else '',
                'columns': [
                    {'name': last_quantity, 'class': 'number'},
                    {'name': product['sum'], 'class': 'number'},
                    {'name': format_date(self.env, date), 'class': 'date'},
                ],
                'level': 2,
                'unfoldable': True,
                'unfolded': unfolded,
                'colspan': 4,
            }
        else:
            return False

    def _get_reports_buttons(self):
        return [
            {'name': _('Print Report'), 'sequence': 4, 'action': 'print_pdf', 'file_export_type': _('PDF')},
            {'name': _('Export (XLSX)'), 'sequence': 2, 'action': 'print_xlsx', 'file_export_type': _('XLSX')},
            {'name': _('Save'), 'sequence': 10, 'action': 'open_report_export_wizard'},
        ]

    def execute_action(self, options, params=None):
        record_id = params.get('recordId', False)
        if record_id and params.get('recordModel', False):
            return {
                'type': 'ir.actions.act_window',
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': params.get('recordModel', False),
                'res_id': record_id,
                'views': [(False, 'form')],
                'target': 'current',
            }

    def print_pdf(self, options):
        res = super(ForecastedQuantityReport, self).print_pdf(options)
        if (self._context.get('default_location_id', False)):
            res['data']['options'] = res['data']['options'][0:-1] + ',"default_location_id": %s}' % self._context.get(
                'default_location_id', False)
        if (self._context.get('is_negative_report', False)):
            res['data']['options'] = res['data']['options'][0:-1] + ',"is_negative_report": "%s"}' % self._context.get(
                'is_negative_report', False)
        return res

    def print_xlsx(self, options):
        res = super(ForecastedQuantityReport, self).print_xlsx(options)
        if (self._context.get('default_location_id', False)):
            res['data']['options'] = res['data']['options'][0:-1] + ',"default_location_id": %s}' % self._context.get(
                'default_location_id', False)
        if (self._context.get('is_negative_report', False)):
            res['data']['options'] = res['data']['options'][0:-1] + ',"is_negative_report": "%s"}' % self._context.get(
                'is_negative_report', False)
        return res

    def get_html(self, options, line_id=None, additional_context=None):
        if additional_context is None:
            additional_context = {}
        if options.get('default_location_id', False):
            location = self.env['stock.location'].search([('id', '=', options.get('default_location_id', False))],
                                                         limit=1)
            if location:
                additional_context.update({
                    'location': location.display_name
                })
        return super(ForecastedQuantityReport, self).get_html(options, line_id=line_id,
                                                              additional_context=additional_context)

    def get_pdf(self, options, minimal_layout=True):
        if options.get('default_location_id', False):
            report = self.env.ref('phd_stock.phd_negative_report')
        else:
            report = self.env.ref('phd_stock.phd_forecasted_quantity_report')
        if not report:
            report = self.env['ir.actions.report']
        if not config['test_enable']:
            self = self.with_context(commit_assetsbundle=True)

        base_url = self.env['ir.config_parameter'].sudo().get_param('report.url') or self.env[
            'ir.config_parameter'].sudo().get_param('web.base.url')
        rcontext = {
            'mode': 'print',
            'base_url': base_url,
            'company': self.env.company,
        }

        body = self.env['ir.ui.view'].render_template(
            "account_reports.print_template",
            values=dict(rcontext),
        )
        body_html = self.with_context(print_mode=True).get_html(options)

        body = body.replace(b'<body class="o_account_reports_body_print">',
                            b'<body class="o_account_reports_body_print">' + body_html)
        if minimal_layout:
            header = ''
            footer = report.render_template("phd_stock.forecasted_footer", values=rcontext)
            footer = report.render_template("web.minimal_layout", values=dict(rcontext, subst=True, body=footer))
        else:
            rcontext.update({
                'css': '',
                'o': self.env.user,
                'res_company': self.env.company,
            })
            header = report.render_template("web.external_layout", values=rcontext)
            header = header.decode('utf-8')
            # Default header and footer in case the user customized web.external_layout and removed the header/footer
            headers = header.encode()
            footer = b''
            # parse header as new header contains header, body and footer
            try:
                root = lxml.html.fromstring(header)
                match_klass = "//div[contains(concat(' ', normalize-space(@class), ' '), ' {} ')]"

                for node in root.xpath(match_klass.format('header')):
                    headers = lxml.html.tostring(node)
                    headers = report.render_template("web.minimal_layout",
                                                     values=dict(rcontext, subst=True,
                                                                 body=headers))

                for node in root.xpath(match_klass.format('footer')):
                    footer = lxml.html.tostring(node)
                    footer = report.render_template("web.minimal_layout",
                                                    values=dict(rcontext, subst=True,
                                                                body=footer))

            except lxml.etree.XMLSyntaxError:
                headers = header.encode()
                footer = b''
            header = headers

        landscape = False
        if len(self.with_context(print_mode=True).get_header(options)[-1]) > 5:
            landscape = True

        return report._run_wkhtmltopdf(
            [body],
            header=header, footer=footer,
            landscape=landscape,
        )

    @api.model
    def _get_options(self, previous_options=None):
        rslt = super(ForecastedQuantityReport, self)._get_options(previous_options)
        if previous_options and not previous_options.get('unfold_lines', False):
            rslt.update({'unfold_lines': []})
        elif previous_options:
            rslt.update({'unfold_lines': previous_options.get('unfold_lines')})
        return rslt
