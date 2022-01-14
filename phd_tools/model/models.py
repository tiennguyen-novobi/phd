import collections
from odoo import models
from odoo.models import fix_import_export_id_paths
import datetime
from odoo import fields as fl
import re
from odoo.tools.misc import formatLang

def format_value(self, amount, currency=False, blank_if_zero=False):
    currency_id = currency or self.env.company.currency_id
    if currency_id.is_zero(amount):
        if blank_if_zero:
            return ''
        # don't print -0.0 in reports
        amount = abs(amount)

    if self.env.context.get('no_format'):
        return amount
    return formatLang(self.env, amount, currency_obj=currency_id)

class BaseModel(models.AbstractModel):
    _inherit = 'base'

    def _phd_export_rows(self, fields, *, _is_toplevel_call=True):
        """ Export fields of the records in ``self``.

            :param fields: list of lists of fields to traverse
            :param bool _is_toplevel_call:
                used when recursing, avoid using when calling from outside
            :return: list of lists of corresponding values
        """
        import_compatible = self.env.context.get('import_compat', True)
        lines = []

        def splittor(rs):
            """ Splits the self recordset in batches of 1000 (to avoid
            entire-recordset-prefetch-effects) & removes the previous batch
            from the cache after it's been iterated in full
            """
            for idx in range(0, len(rs), 1000):
                sub = rs[idx:idx + 1000]
                for rec in sub:
                    yield rec
                rs.invalidate_cache(ids=sub.ids)

        if not _is_toplevel_call:
            splittor = lambda rs: rs

        # memory stable but ends up prefetching 275 fields (???)
        for record in splittor(self):
            # main line of record, initially empty
            current = [''] * len(fields)
            lines.append(current)

            # list of primary fields followed by secondary field(s)
            primary_done = []

            # process column by column
            for i, path in enumerate(fields):
                if not path:
                    continue

                name = path[0]
                if name in primary_done:
                    continue

                if name == '.id':
                    current[i] = str(record.id)
                elif name == 'id':
                    current[i] = (record._name, record.id)
                else:
                    field = record._fields[name]
                    value = record[name]

                    # this part could be simpler, but it has to be done this way
                    # in order to reproduce the former behavior
                    if not isinstance(value, BaseModel):
                        if field.type == 'datetime':
                            current[i] = fl.Date.convert_to_export(fl.Date, value.date() if isinstance(value, datetime.datetime) else value, record)
                        else:
                            current[i] = field.convert_to_export(value, record)
                    else:
                        primary_done.append(name)

                        # in import_compat mode, m2m should always be exported as
                        # a comma-separated list of xids in a single cell
                        if import_compatible and field.type == 'many2many' and len(path) > 1 and path[1] == 'id':
                            xml_ids = [xid for _, xid in value.__ensure_xml_id()]
                            current[i] = ','.join(xml_ids) or False
                            continue

                        # recursively export the fields that follow name; use
                        # 'display_name' where no subfield is exported
                        fields2 = [(p[1:] or ['display_name'] if p and p[0] == name else [])
                                   for p in fields]
                        lines2 = value._export_rows(fields2, _is_toplevel_call=False)
                        if lines2:
                            # merge first line with record's main line
                            for j, val in enumerate(lines2[0]):
                                if val or isinstance(val, bool):
                                    current[j] = val
                            # append the other lines at the end
                            lines += lines2[1:]
                        else:
                            current[i] = False

        # if any xid should be exported, only do so at toplevel
        if _is_toplevel_call and any(f[-1] == 'id' for f in fields):
            bymodels = collections.defaultdict(set)
            xidmap = collections.defaultdict(list)
            # collect all the tuples in "lines" (along with their coordinates)
            for i, line in enumerate(lines):
                for j, cell in enumerate(line):
                    if type(cell) is tuple:
                        bymodels[cell[0]].add(cell[1])
                        xidmap[cell].append((i, j))
            # for each model, xid-export everything and inject in matrix
            for model, ids in bymodels.items():
                for record, xid in self.env[model].browse(ids).__ensure_xml_id():
                    for i, j in xidmap.pop((record._name, record.id)):
                        lines[i][j] = xid
            assert not xidmap, "failed to export xids for %s" % ', '.join('{}:{}' % it for it in xidmap.items())

        return lines

    def phd_export_data(self, fields_to_export):
        """ Export fields for selected objects

            :param fields_to_export: list of fields
            :param raw_data: True to return value in native Python type
            :rtype: dictionary with a *datas* matrix

            This method is used when exporting data via client menu
        """

        fields_to_export = [fix_import_export_id_paths(f) for f in fields_to_export]
        return {'datas': self._phd_export_rows(fields_to_export)}
