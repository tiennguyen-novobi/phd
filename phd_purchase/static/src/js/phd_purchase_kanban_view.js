odoo.define('phd_purchase.purchase_kanban', function(require) {
    'use strict';

    var core = require('web.core');
    var KanbanController = require('web.KanbanController');
    var KanbanView = require('web.KanbanView');
    var viewRegistry = require('web.view_registry');
    var qweb = core.qweb;
    var session = require('web.session');

    var PurchaseController = KanbanController.extend({
        _onAddRecordToColumn: function (ev) {
            var self = this;
            var record = ev.data.record;
            var data = record.recordData;
            var column = ev.target;
            if (column.title == "RFQ") {
                if (data.stage_id.data.display_name == 'Cancelled') {
                    this._rpc({
                    model: record.modelName,
                    method: 'button_draft',
                    args: [record.id],
                    }).then(function (result) {
                        self.reload();
                    });
                }
            } else if (column.title == "RFQ Sent") {
                if (data.stage_id.data.display_name == 'Closed' || data.stage_id.data.display_name == 'Purchase Order') {
                    this._rpc({
                    model: record.modelName,
                    method: 'action_rfq_send',
                    args: [record.id],
                    }).then(function (result) {
                        self.do_action(result,
                        { on_close: function () {
                            self.reload();
                        }});
                    });
                }
            } else if (column.title == "To Approve") {
                 if (data.stage_id.data.display_name == 'RFQ' || data.stage_id.data.display_name == 'RFQ Sent') {
                    this._rpc({
                        model: record.modelName,
                        method: 'button_confirm',
                        args: [record.id],
                    }).then(function (result) {
                        self.reload();
                    });
                 }
            } else if (column.title == "Purchase Order") {
               if (data.stage_id.data.display_name == 'RFQ' || data.stage_id.data.display_name == 'RFQ Sent') {
                    this._rpc({
                            model: record.modelName,
                            method: 'button_confirm',
                            args: [record.id],
                        }).then(function (result) {
                            self.reload();
                    });
               } else if (data.stage_id.data.display_name == 'To Approve') {
                   session.user_has_group('purchase.group_purchase_manager').then(function(has_group_manager) {
                        if (has_group_manager) {
                            this._rpc({
                                model: record.modelName,
                                method: 'button_approve',
                                args: [record.id],
                            }).then(function (result) {
                                self.reload();
                            });
                        }
                    });
               } else if (data.stage_id.data.display_name == 'On Hold' && data.previous_state.data.display_name == 'Purchase Order') {
                    this._rpc({
                            model: record.modelName,
                            method: 'action_continue',
                            args: [record.id],
                        }).then(function (result) {
                            self.reload();
                    });
               }
            }
            else if (column.title == "On Hold") {
                if (data.stage_id.data.display_name == 'Closed' ||
                data.stage_id.data.display_name == 'Purchase Order' ||
                data.stage_id.data.display_name == 'Ready to Pickup') {
                    self._rpc({
                        model: record.modelName,
                        method: 'action_on_hold',
                        args: [record.id],
                    }).then(function (result) {
                        self.reload();
                    });
                }
            } else if (column.title == "Closed") {
                if (data.stage_id.data.display_name == 'Purchase Order' || data.stage_id.data.display_name == 'Shipped') {
                        this._rpc({
                        model: record.modelName,
                        method: 'button_done',
                        args: [record.id],
                        }).then(function (result) {
                            self.reload();
                        });
                }
            } else if (column.title == "Cancelled" && data.current_stage != 'Ready to Pickup') {
                if(data.stage_id.data.display_name == 'RFQ Sent') {
                    if(record.recordData.is_subcontracting) {
                        this._rpc({
                        model: record.modelName,
                        method: 'button_cancel',
                        args: [record.id],
                        }).then(function (result) {
                            self.reload();
                        });
                    }
                } else {
                    this._rpc({
                        model: record.modelName,
                        method: 'button_cancel',
                        args: [record.id],
                        }).then(function (result) {
                            self.reload();
                        });
                }
            }  else if (column.title == "Ready to Pickup") {
                if (data.stage_id.data.display_name == 'Purchase Order' && !data.is_subcontracting) {
                    this._rpc({
                            model: record.modelName,
                            method: 'action_ready_to_pickup',
                            args: [record.id],
                            }).then(function (result) {
                                self.reload();
                            });
                } else if (data.stage_id.data.display_name == 'On Hold' && data.previous_state.data.display_name == 'Ready to Pickup') {
                    this._rpc({
                            model: record.modelName,
                            method: 'action_continue',
                            args: [record.id],
                        }).then(function (result) {
                            self.reload();
                    });
                }
            } else if (column.title == "Shipped") {
                if (data.stage_id.data.display_name == 'Ready to Pickup' && !data.is_subcontracting) {
                    this._rpc({
                            model: record.modelName,
                            method: 'action_shipped',
                            args: [record.id],
                            }).then(function (result) {
                                self.reload();
                            });
                }
            }
            self.reload();
        },
    });

    var PurchaseOrderKanbanView = KanbanView.extend({
        config: _.extend({}, KanbanView.prototype.config, {
            Controller: PurchaseController,
        }),
    });

    viewRegistry.add('phd_purchase_order_kanban', PurchaseOrderKanbanView);
});
