odoo.define('phd_tools.web.DataExport', function (require) {
"use strict";

    var DataExport = require('web.DataExport');
    var config = require('web.config');
    var core = require('web.core');
    var Dialog = require('web.Dialog');
    var data = require('web.data');
    var framework = require('web.framework');
    var pyUtils = require('web.py_utils');

    var QWeb = core.qweb;
    var _t = core._t;

    var PHDDataExport = DataExport.extend({
    _exportData(exportedFields, exportFormat, idsToExport) {
                if (_.isEmpty(exportedFields)) {
                    Dialog.alert(this, _t("Please select fields to export..."));
                    return;
                }
                if (this.isCompatibleMode) {
                    exportedFields.unshift({ name: 'id', label: _t('External ID') });
                }

                framework.blockUI();
                this.getSession().get_file({
                    url: '/phd/web/export/' + exportFormat,
                    data: {
                        data: JSON.stringify({
                            model: this.record.model,
                            fields: exportedFields,
                            ids: idsToExport,
                            domain: this.domain,
                            groupby: this.groupby,
                            context: pyUtils.eval('contexts', [this.record.getContext()]),
                            import_compat: this.isCompatibleMode,
                        })
                    },
                    complete: framework.unblockUI,
                    error: (error) => this.call('crash_manager', 'rpc_error', error),
                });
            },
        });

    return PHDDataExport;
});