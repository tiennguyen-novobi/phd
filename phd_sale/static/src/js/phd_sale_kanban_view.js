odoo.define('phd_sale.sale_kanban', function(require) {
    'use strict';

    var core = require('web.core');
    var KanbanController = require('web.KanbanController');
    var KanbanView = require('web.KanbanView');
    var viewRegistry = require('web.view_registry');
    var qweb = core.qweb;
    var Session = require('web.session');

    var SaleController = KanbanController.extend({
        _onAddRecordToColumn: function (ev) {
            var self = this;
            var record = ev.data.record;
            var recordData = record.recordData;
            var column = ev.target;
            if (column.title == "Quotation") {
                if(recordData.stage_id.data.display_name == 'Cancelled') {
                    self._rpc({
                    model: record.modelName,
                    method: 'action_draft',
                    args: [record.id],
                    }).then(function (result) {
                        self.reload();
                    });
                }
            } else if (column.title == "Quotation Sent") {
                if (recordData.stage_id.data.display_name == 'Sales Order' || recordData.stage_id.data.display_name == 'Quotation') {
                    self._rpc({
                        model: record.modelName,
                        method: 'action_quotation_send',
                        args: [record.id],
                        }).then(function (result) {
                            self.do_action(result,
                            { on_close: function () {
                                self.reload();
                            }});
                        });
                }
            } else if (column.title == "Sales Order") {
                if (recordData.stage_id.data.display_name == 'Quotation' || recordData.stage_id.data.display_name == 'Quotation Sent' ||
                (recordData.stage_id.data.display_name == 'On Hold' && recordData.previous_state.data.display_name == 'Sales Order')) {
                    self._rpc({
                        model: record.modelName,
                        method: 'action_confirm',
                        args: [record.id],
                    }).then(function (result) {
                        self.reload();
                    });
                }
            } else if (column.title == "On Hold") {
                if (recordData.stage_id.data.display_name == 'Sales Order' || recordData.stage_id.data.display_name == 'Partially Shipped') {
                    self._rpc({
                        model: record.modelName,
                        method: 'action_on_hold',
                        args: [record.id],
                    }).then(function (result) {
                        self.reload();
                    });
                }
            } else if (column.title == "Partially Shipped") {
                if (recordData.stage_id.data.display_name == 'On Hold' && recordData.previous_state.data.display_name == 'Partially Shipped') {
                    self._rpc({
                        model: record.modelName,
                        method: 'action_partially_shipped',
                        args: [record.id],
                    }).then(function (result) {
                        self.reload();
                    });
                }
            } else if (column.title == "Closed") {
                if (recordData.stage_id.data.display_name == 'Fully Shipped') {
                    self._rpc({
                        model: record.modelName,
                        method: 'action_closed',
                        args: [record.id],
                    }).then(function (result) {
                        self.reload();
                    });
                }
            } else if (column.title == "Cancelled") {
                if (['Sales Order','Closed','Quotation Sent','Quotation'].includes(recordData.stage_id.data.display_name) || (recordData.stage_id.data.display_name ='On Hold' && recordData.previous_state.data.display_name == 'Sales Order')) {
                    self._rpc({
                        model: record.modelName,
                        method: 'action_cancel',
                        args: [record.id],
                    }).then(function (result) {
                        self.reload();
                    });
                }
            }
            self.reload();
        },
    });

    var SaleOrderKanbanView = KanbanView.extend({
        config: _.extend({}, KanbanView.prototype.config, {
            Controller: SaleController,
        }),
    });

    viewRegistry.add('phd_sale_order_kanban', SaleOrderKanbanView);
});
