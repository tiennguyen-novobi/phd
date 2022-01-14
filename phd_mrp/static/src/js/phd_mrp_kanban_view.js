odoo.define('phd_mrp.mrp_kanban', function(require) {
    'use strict';

    var core = require('web.core');
    var KanbanController = require('web.KanbanController');
    var KanbanView = require('web.KanbanView');
    var viewRegistry = require('web.view_registry');
    var qweb = core.qweb;

    var MrpController = KanbanController.extend({
        _onAddRecordToColumn: function (ev) {
            var self = this;
            var record = ev.data.record;
            var recordData = record.recordData;
            var column = ev.target;
            if (column.title == "Confirmed") {
                if (recordData.state == 'planned' && recordData.date_planned_start != false && recordData.date_planned_finished != false) {
                    this._rpc({
                    model: record.modelName,
                    method: 'button_unplan',
                    args: [record.id],
                    }).then(function (result) {
                        self.reload();
                    });
                } else if (recordData.state == 'draft' && recordData.is_locked && recordData.state != 'cancel') {
                    this._rpc({
                    model: record.modelName,
                    method: 'action_confirm',
                    args: [record.id],
                    }).then(function (result) {
                        self.reload();
                    });
                }
            } else if (column.title == "To Close" && recordData.routing_id == false && recordData.is_locked && recordData.state != 'cancel') {
                 this._rpc({
                    model: record.modelName,
                    method: 'open_produce_product',
                    args: [record.id],
                    }).then(function (result) {
                        result.context = {'active_id': record.id}
                        self.do_action(result,
                        { on_close: function () {
                            self.reload();
                        }});
                    });
            } else if (column.title == "Planned" && recordData.state != 'cancel' && recordData.state == 'confirmed' && recordData.routing_id != false) {
                this._rpc({
                        model: record.modelName,
                        method: 'button_plan',
                        args: [record.id],
                    }).then(function (result) {
                        self.reload();
                });
            } else if (column.title == "In Progress" && recordData.state == 'planned') {
                this._rpc({
                        model: record.modelName,
                        method: 'mrp_in_progress',
                        args: [record.id],
                    }).then(function (result) {
                        self.reload();
                });
            } else if (column.title == "Done" && recordData.state == 'to_close' && recordData.state != 'cancel') {
                this._rpc({
                        model: record.modelName,
                        method: 'button_mark_done',
                        args: [record.id],
                    }).then(function (result) {
                        self.reload();
                });
            } else if (column.title == "Cancelled" && recordData.state != 'done' && recordData.state != 'cancel' && recordData.is_locked) {
                this._rpc({
                        model: record.modelName,
                        method: 'action_cancel',
                        args: [record.id],
                    }).then(function (result) {
                        self.reload();
                });
            }
            self.reload();
        },
    });

    var MrpOrderKanbanView = KanbanView.extend({
        config: _.extend({}, KanbanView.prototype.config, {
            Controller: MrpController,
        }),
    });

    viewRegistry.add('phd_mrp_order_kanban', MrpOrderKanbanView);
});
