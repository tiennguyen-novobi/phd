odoo.define('phd_tool.date_range_export_report_list_view', function(require) {
    'use strict';
    var SumAvgListRenderer = require('phd_tools.sum.avg.ListRenderer');
    var ListView = require('phd_tools.web.export.pdf');
    var ControlPanelView = require('phd_tool.ControlPanelView');
    var viewRegistry = require('web.view_registry');

    var ReportView = ListView.extend({
        config: _.extend({}, ListView.prototype.config, {
                Renderer: SumAvgListRenderer,
        }),
        searchMenuTypes: ['filter', 'groupBy', 'favorite', 'dateRange'],

        _createControlPanel: function (parent) {
            var self = this;
            var controlPanelView = new ControlPanelView(this.controlPanelParams);
            return controlPanelView.getController(parent).then(function (controlPanel) {
                self.controllerParams.controlPanel = controlPanel;
                return controlPanel.appendTo(document.createDocumentFragment()).then(function () {
                    self._updateMVCParams(controlPanel.getSearchQuery());
                    return controlPanel;
                });
            });
        },
    });

    viewRegistry.add('phd_date_range_export_report_list_view', ReportView);
});