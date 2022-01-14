odoo.define('phd_stock.excute.action.on.change.relation.field', function (require) {
"use strict";
    var FieldRadio = require('web.relational_fields').FieldRadio;
    var registry = require('web.field_registry');
    var framework = require('web.framework');
    var BasicModel = require('web.BasicModel');

    BasicModel.include({
        _phdfetchSpecialMany2ones: function (record, fieldName, fieldInfo, fieldsToRead) {
            var field = record.fields[fieldName];
            if (field.type !== "many2one") {
                return Promise.resolve();
            }

            var context = record.getContext({fieldName: fieldName});
            context.forecasted_qty = true;
            var domain = record.getDomain({fieldName: fieldName});
            if (domain.length) {
                var localID = (record._changes && fieldName in record._changes) ?
                                record._changes[fieldName] :
                                record.data[fieldName];
                if (localID) {
                    var element = this.localData[localID];
                    domain = ["|", ["id", "=", element.data.id]].concat(domain);
                }
            }

            // avoid rpc if not necessary
            var hasChanged = this._saveSpecialDataCache(record, fieldName, {
                context: context,
                domain: domain,
            });
            if (!hasChanged) {
                return Promise.resolve();
            }

            var self = this;
            return this._rpc({
                    model: field.relation,
                    method: 'search_read',
                    fields: ["id"].concat(fieldsToRead || []),
                    context: context,
                    domain: domain,
                })
                .then(function (records) {
                    var ids = _.pluck(records, 'id');
                    return self._rpc({
                            model: field.relation,
                            method: 'name_get',
                            args: [ids],
                            context: context,
                        })
                        .then(function (name_gets) {
                            _.each(records, function (rec) {
                                var name_get = _.find(name_gets, function (n) {
                                    return n[0] === rec.id;
                                });
                                rec.display_name = name_get[1];
                            });
                            return records;
                        });
                });
        },
    })

    var PHDFieldRadio = FieldRadio.extend({
        specialData: "_phdfetchSpecialMany2ones",

        _onInputClick: function (event) {
            this._super.apply(this, arguments);
            var self = this;
            var index = $(event.target).data('index');
            var value = this.values[index];
            var context = this.record.context;
            framework.blockUI();
            if (context.forecasted_qty != undefined && context.forecasted_qty) {
                $("#forecasted_qty_report_fiter").click();
            } else if (context.is_negative_report != undefined && context.is_negative_report) {
                $("#negative_report_filter").click();
            } else if (context.is_warehouse_report != undefined && context.is_warehouse_report) {
                $("#warehouse_report_filter").click();
            } else if (context.is_current_stock != undefined && context.is_current_stock) {
                $("#lot_qty_report_filter").click();
            }
            framework.unblockUI();
        },
    });

    registry
    .add('phd_radio', PHDFieldRadio);

    return BasicModel;
});