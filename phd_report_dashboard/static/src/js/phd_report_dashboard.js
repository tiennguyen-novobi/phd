odoo.define('phd_report_dashboard.report_kanban', function(require) {
    'use strict';

    var core = require('web.core');
    var KanbanController = require('web.KanbanController');
    var KanbanRenderer = require('web.KanbanRenderer');
    var KanbanView = require('web.KanbanView');
    var viewRegistry = require('web.view_registry');
    var qweb = core.qweb;

    KanbanRenderer.include({
        events: _.extend({}, KanbanRenderer.prototype.events, {
            'click .o_dashboard_item_detail': '_onReportDashboardItemDetail',
        }),
        _onReportDashboardItemDetail: function (e) {
            e.preventDefault();
            var record = e.currentTarget.dataset;
            return this.do_action({
                 type: 'ir.actions.act_window',
                 name: this.string,
                 res_id: parseInt(record.recordId),
                 res_model:  record.recordModel,
                 views: [[false, 'form']],
                 target: 'current',
            });
        },
        init: function () {
            this._super.apply(this, arguments);
        },
    });
});
