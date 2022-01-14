odoo.define('phd_tools.web.export.pdf', function (require) {
"use strict";

    var ListController = require('web.ListController');
    var ListView = require('web.ListView');
    var PHDDataExport = require('phd_tools.web.DataExport');
    var core = require('web.core');
    var qweb = core.qweb;
    var viewRegistry = require('web.view_registry');
    var framework = require('web.framework');
    var session = require('web.session');

    var PHDExportPDFListController = ListController.extend({
        _getExportDialogWidget() {
            let state = this.model.get(this.handle);
            let defaultExportFields = this.renderer.columns.filter(field => field.tag === 'field').map(field => field.attrs.name);
            let groupedBy = this.renderer.state.groupedBy;
            return new PHDDataExport(this, state, defaultExportFields, groupedBy,
                this.getActiveDomain(), this.getSelectedIds());
        },

        _serializeSort: function (orderBy) {
            return _.map(orderBy, function (order) {
                return order.name + (order.asc !== false ? ' ASC' : ' DESC');
            }).join(', ');
        },
        _onExportReportPDF: function (ev) {
            var self = this;
            framework.blockUI();
            if (this.initialState.context.list_view_report_id != undefined) {
                var domain = this.model.get(this.handle).getDomain();
                var modelName = this.modelName;
                var report_id = this.initialState.context.list_view_report_id;
                var date_range_field = this.initialState.context.date_range || false;
                var group_by = this.model.get(this.handle).groupedBy;
                var orderedByLine = this._serializeSort(this.model.get(this.handle).orderedBy);
                //Order Group
                var groupByField = group_by[0];
                var rawGroupBy = groupByField != undefined ? groupByField.split(':')[0] : [];
                var fields = _.uniq(this.initialState.getFieldNames().concat(rawGroupBy));
                var orderedByGroup = this._serializeSort(_.filter(this.model.get(this.handle).orderedBy, function (order) {
                    return order.name === rawGroupBy || self.initialState.fields[order.name].group_operator !== undefined;
                }));
                var default_location_id = this.initialState.context.default_location_id || -1
                var defaultExportFields = this.renderer.columns.filter(field=>field.tag === 'field').map(field => ({
                   name: field.attrs.name,
                   label: field.attrs.string || this.initialState.fields[field.attrs.name].string,
                   sum: field.attrs.sum != undefined ? field.attrs.sum : false,
                   avg: field.attrs.avg != undefined ? field.attrs.avg : false,
                   widget: field.attrs.widget || false,
                   class: field.attrs.class != undefined ? field.attrs.class : 'text-center',
                }));
                framework.blockUI();
                return new Promise(function (resolve, reject) {
                    var type = 'qweb-pdf';
                    var blocked = !session.get_file({
                        url: '/report/download/pdf',
                        data: {
                            data: JSON.stringify([type, domain, modelName, report_id, defaultExportFields, group_by, date_range_field, orderedByLine, default_location_id, orderedByGroup]),
                            context: JSON.stringify(session.user_context),
                        },
                        success: resolve,
                        error: (error) => {
                            self.call('crash_manager', 'rpc_error', error);
                            reject();
                        },
                        complete: framework.unblockUI,
                    });
                    if (blocked) {
                        var message = _t('A popup window with your report was blocked. You ' +
                                         'may need to change your browser settings to allow ' +
                                         'popup windows for this page.');
                        self.do_warn(_t('Warning'), message, true);
                    }
                });
            }
            framework.unblockUI;
        },
        renderButtons: function ($node) {
            this._super.apply(this, arguments);
            if (!this.noLeaf && this.hasButtons) {
                this.$buttons.on('click', '.o_list_export_report_pdf', this._onExportReportPDF.bind(this));
            }
        },
    });

    var PHDExportPDFListView = ListView.extend({
            init: function (viewInfo, params) {
                 var self = this;
                 this._super.apply(this, arguments);
                 this.controllerParams.activeActions.export_report_pdf = true;
            },
            config: _.extend({}, ListView.prototype.config, {
                Controller: PHDExportPDFListController,
            }),
     });

    viewRegistry.add('phd_tools_export_pdf', PHDExportPDFListView);

    return PHDExportPDFListView;
});