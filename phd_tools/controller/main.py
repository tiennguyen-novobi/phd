import json
import operator
import logging
from odoo.tools import html_escape
from odoo import http, tools
from odoo.http import content_disposition, request, serialize_exception as _serialize_exception
from odoo.addons.web.controllers.main import ReportController
from odoo.addons.web.controllers.main import DataSet
from odoo.addons.web.controllers.main import ExcelExport
from odoo.addons.web.controllers.main import ExportFormat
from odoo.addons.web.controllers.main import serialize_exception
from odoo.addons.web.controllers.main import GroupsTreeNode
import json
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
_logger = logging.getLogger(__name__)

class PHDExport(ReportController):
    def _infinity_loop(self,data, model_name, domain, fields, grouped_by, level, export_fields,orderbyLine, orderbyGroup, expand=True):
        if len(grouped_by) > 0:
            groups = request.env[model_name].web_read_group(domain=domain, fields=fields,orderby=orderbyGroup, groupby=grouped_by, expand=expand)['groups']
            if groups:
                for x in range(0, len(groups)):
                    group_for_query = []
                    group_for_query.extend(grouped_by)
                    group_for_query.pop(0)

                    data.append(
                        {'group_name': 'Undefined' if not groups[x][grouped_by[0]] else groups[x][
                            grouped_by[0]] if isinstance(groups[x][grouped_by[0]], str)
                        else groups[x][grouped_by[0]][1]._value, 'level': level, 'group_data': groups[x]})
                    if groups[x].get('__data', False):
                        records = DataSet.do_search_read(self=self,model=model_name, fields=fields, offset=0, limit=9999999999999, domain=groups[x].get('__domain', None), sort=orderbyLine)
                        data.append({'records': records.get('records', False), 'belong_level': level})
                    # for y in range(1, len(grouped_by)):
                    if len(grouped_by) >= 2:
                        self._infinity_loop(level=level + 1, data=data, model_name=model_name, domain=groups[x]['__domain'],
                                            fields=fields,
                                            grouped_by=group_for_query, export_fields=export_fields, orderbyLine=orderbyLine, orderbyGroup=orderbyGroup)

                    if level == 1:
                        has_sum = False
                        has_avg = False
                        # Total Line
                        total_line = {
                            'total_title': 'Total %s' % (
                                'Undefined' if not groups[x][grouped_by[0]] else groups[x][grouped_by[0]] if isinstance(
                                    groups[x][grouped_by[0]], str)
                                else groups[x][grouped_by[0]][1]._value),
                        }
                        avg_line = {
                            'avg_title': 'Avg %s' % (
                                'Undefined' if not groups[x][grouped_by[0]] else groups[x][grouped_by[0]] if isinstance(
                                    groups[x][grouped_by[0]], str)
                                else groups[x][grouped_by[0]][1]._value),
                        }
                        for field in export_fields:
                            records = False
                            total = 0
                            if field.get('sum', False) or field.get('avg', False):
                                records = data[-1].get('records', False)
                                if records:
                                    total = sum(record[field['name']] for record in records)
                            if field.get('sum', False):
                                has_sum = True
                                widget = field.get('widget', False)
                                is_createtine = False
                                if not widget:
                                    try:
                                        attr_sum = json.loads(field.get('sum'))
                                        widget = attr_sum.get('widget', False)
                                        is_createtine = attr_sum.get('is_createtine_in_dollar', False)
                                    except ValueError:
                                        widget = False
                                if is_createtine:
                                    createtine = request.env['product.product'].search([('is_creatine','=', True)], limit=1)
                                    if createtine:
                                        total_createtine_in_dollar = total * createtine.standard_price
                                        is_createtine.update({'total_createtine_in_dollar': total_createtine_in_dollar})
                                        total_line.update({field['name']: {'total': total,
                                                                           'widget': widget,
                                                                           'is_createtine': is_createtine}})
                                else:
                                    total_line.update({field['name']: {'total': total,
                                                                   'widget': widget}})
                            if field.get('avg',False):
                                has_avg = True
                                avg = 0
                                if records and len(records) > 0:
                                    avg = total / len(records)
                                widget = field.get('widget', False)
                                if not widget:
                                    try:
                                        attr_avg = json.loads(field.get('avg'))
                                        widget = attr_avg.get('widget', False)
                                    except ValueError:
                                        widget = False
                                avg_line.update({field['name']: {'total': round(avg,2),
                                                                   'widget': widget}})
                        if has_sum:
                            data.append(total_line)
                        if has_avg:
                            data.append(avg_line)

    def _get_date_ranges(self,field, domain):
        list_date = []
        for element in domain:
            if element[0] == field:
                list_date.append(element[2])
        if len(list_date) >= 2:
            date_ranges = {
                'start_date': min(date for date in list_date),
                'end_date': max(date for date in list_date)
            }
            if date_ranges['start_date'] != date_ranges['end_date']:
                return date_ranges
        return False

    @http.route(['/report/download/pdf'], type='http', auth="user")
    def report_download_pdf(self, data, token, context=None):
        requestcontent = json.loads(data)
        type, domain, model_name, report_id, defaultExportFields, grouped_by, orderbyLine, orderbyGroup = requestcontent[0], requestcontent[1] , requestcontent[2], requestcontent[3], requestcontent[4], requestcontent[5], requestcontent[7], requestcontent[9]
        try:
            report = request.env['ir.actions.report']._get_report_from_name(report_id)
            Context = dict(request.context)
            Context.update({
                'domain': domain,
                # 'default_export_fields': defaultExportFields,
                'currency': request.env['res.users'].browse(request._uid).company_id.currency_id,
                'grouped_by': grouped_by,
                'default_location_id': requestcontent[8],
                'hasattr':hasattr,
            })
            request.context = Context
            if len(requestcontent) > 7 and requestcontent[6]:
                date_ranges = self._get_date_ranges(requestcontent[6],domain)
                if date_ranges:
                    Context.update({
                        'date_ranges': date_ranges
                    })
            if report:
                Context.update({
                    'report_title': report.name,
                })
            if len(grouped_by) > 0:
                data_after_grouping = []
                level = 1
                fields = [field['name'] for field in defaultExportFields]
                self._infinity_loop(level=level,
                                    data=data_after_grouping,
                                    model_name=model_name,
                                    domain=domain,
                                    fields=fields,
                                    grouped_by=grouped_by, export_fields=defaultExportFields, orderbyLine=orderbyLine, orderbyGroup=orderbyGroup)
                if len(data_after_grouping) > 0:
                    Context.update({
                        'default_export_fields': defaultExportFields,
                        'data_after_grouping': data_after_grouping,
                    })
            else:
                for i in range(0, len(defaultExportFields)):
                    if defaultExportFields[i].get('sum', False) and defaultExportFields[i].get('avg', False):
                        try:
                            attr_sum = json.loads(defaultExportFields[i].get('sum', False))
                            attr_avg = json.loads(defaultExportFields[i].get('avg', False))
                            if attr_sum.get('is_createtine_in_dollar', False):
                                createtine = request.env['product.product'].search([('is_creatine','=', True)], limit=1)
                                if createtine:
                                    defaultExportFields[i].update({
                                        'is_createtine': {
                                            'standard_price': createtine.standard_price,
                                            'widget': attr_sum.get('is_createtine_in_dollar').get('widget', False),
                                            'help': attr_sum.get('is_createtine_in_dollar').get('help', False),
                                        }
                                    })
                            defaultExportFields[i].update({'sum': attr_sum.get('help',''),
                                                           'avg': attr_avg.get('help',''),
                                                           'sum_widget': attr_sum.get('widget', False),
                                                           'avg_widget': attr_avg.get('widget', False),
                                                        })
                        except ValueError:
                            defaultExportFields[i].update(
                                {'sum': '', 'avg': ''})
                Context.update({
                    'default_export_fields': defaultExportFields,
                })
            request.context = Context
            if type in ['qweb-pdf', 'qweb-text']:
                converter = 'pdf'
                extension = 'pdf'
                docids = str(request.env[model_name].search(domain, order=orderbyLine).ids)[1:-1]
                if docids:
                    response = self.report_routes(report_id, docids=docids, converter=converter, context=context)
                    filename = "%s.%s" % (report.name, extension)
                    response.headers.add('Content-Disposition', content_disposition(filename))
                    response.set_cookie('fileToken', token)
                    return response
            else:
                return
        except Exception as e:
            se = _serialize_exception(e)
            error = {
                'code': 200,
                'message': "Odoo Server Error",
                'data': se
            }
            return request.make_response(html_escape(json.dumps(error)))

class PHDGroupsTreeNode(GroupsTreeNode):
    def phd_insert_leaf(self, group):
        """
        Build a leaf from `group` and insert it in the tree.
        :param group: dict as returned by `read_group(lazy=False)`
        """
        leaf_path = [group.get(groupby_field) for groupby_field in self._groupby]
        domain = group.pop('__domain')
        count = group.pop('__count')

        records = self._model.search(domain, offset=0, limit=False, order=False)

        # Follow the path from the top level group to the deepest
        # group which actually contains the records' data.
        node = self # root
        node.count += count
        for node_key in leaf_path:
            # Go down to the next node or create one if it does not exist yet.
            node = node.child(node_key)
            # Update count value and aggregated value.
            node.count += count

        node.data = records.phd_export_data(self._export_field_names).get('datas',[])

class PHDExportFormat(ExportFormat):

    def PHDbase(self, data, token):

        params = json.loads(data)
        model, fields, ids, domain, import_compat = \
            operator.itemgetter('model', 'fields', 'ids', 'domain', 'import_compat')(params)

        fields_needed_delete = False
        if params.get('context', False):
            if params.get('context').get('is_reformat_on_export_excel', False):
                fields_needed_delete = params.get('context').get('is_reformat_on_export_excel').get('delete_field', False)

        field_names = []
        for f in fields:
            if fields_needed_delete:
                if f['name'] not in fields_needed_delete:
                    field_names.append(f['name'])
            else:
                field_names.append(f['name'])

        if import_compat:
            columns_headers = field_names
        else:
            columns_headers = []
            for val in fields:
                if fields_needed_delete:
                    if val['name'] not in fields_needed_delete:
                        columns_headers.append(val['label'].strip())
                else:
                    columns_headers.append(val['label'].strip())

        Model = request.env[model].with_context(**params.get('context', {}))
        groupby = params.get('groupby')
        if not import_compat and groupby:
            groupby_type = [Model._fields[x.split(':')[0]].type for x in groupby]
            domain = [('id', 'in', ids)] if ids else domain
            groups_data = Model.read_group(domain, [x if x != '.id' else 'id' for x in field_names], groupby, lazy=False)

            # read_group(lazy=False) returns a dict only for final groups (with actual data),
            # not for intermediary groups. The full group tree must be re-constructed.
            tree = PHDGroupsTreeNode(Model, field_names, groupby, groupby_type)
            for leaf in groups_data:
                tree.phd_insert_leaf(leaf)

            response_data = self.from_group_data(fields, tree)
        else:
            Model = Model.with_context(import_compat=import_compat)
            records = Model.browse(ids) if ids else Model.search(domain, offset=0, limit=False, order=False)

            if not Model._is_an_ordinary_table():
                fields = [field for field in fields if field['name'] != 'id']

            export_data = records.phd_export_data(field_names).get('datas',[])
            response_data = self.from_data(columns_headers, export_data)
        return request.make_response(response_data,
            headers=[('Content-Disposition',
                            content_disposition(self.filename(model))),
                     ('Content-Type', self.content_type)],
            cookies={'fileToken': token})

class PHDExcelExport(ExcelExport):
    @http.route('/phd/web/export/xlsx', type='http', auth="user")
    @serialize_exception
    def phd_index(self, data, token):
        return PHDExportFormat.PHDbase(self, data, token)