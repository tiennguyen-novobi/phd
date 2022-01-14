odoo.define('phd_tools.web.export.excel', function (require) {
"use strict";

    var ListController = require('web.ListController');
    var ListView = require('web.ListView');
    var PHDDataExport = require('phd_tools.web.DataExport');
    var core = require('web.core');
    var qweb = core.qweb;
    var viewRegistry = require('web.view_registry');
    var framework = require('web.framework');
    var session = require('web.session');

    var PHDExportListController = ListController.extend({
        _getExportDialogWidget() {
            let state = this.model.get(this.handle);
            let defaultExportFields = this.renderer.columns.filter(field => field.tag === 'field').map(field => field.attrs.name);
            let groupedBy = this.renderer.state.groupedBy;
            return new PHDDataExport(this, state, defaultExportFields, groupedBy,
                this.getActiveDomain(), this.getSelectedIds());
        },
    });

    var PHDExportListView = ListView.extend({
            init: function (viewInfo, params) {
                 var self = this;
                 this._super.apply(this, arguments);
            },
            config: _.extend({}, ListView.prototype.config, {
                Controller: PHDExportListController,
            }),
     });

    viewRegistry.add('phd_tools_export_excel', PHDExportListView);

    return PHDExportListView;
});