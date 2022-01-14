odoo.define('phd_tools.phd_lot_many2one_filter', function (require) {
"use strict";

    var RelationalFields = require('web.relational_fields');
    var registry = require('web.field_registry');
    var core = require('web.core');
    var _t = core._t;


    var PHDLotMany2one = RelationalFields.FieldMany2One.extend({
        _manageSearchMore: function (values, search_val, domain, context) {
            var self = this;
            values = values.slice(0, this.limit);
            values.push({
                label: _t("Search More..."),
                action: function () {
                    var prom = self._rpc({
                            model: self.field.relation,
                            method: 'name_search',
                            kwargs: {
                                name: search_val,
                                args: domain,
                                operator: "ilike",
                                limit: self.SEARCH_MORE_LIMIT,
                                context: context,
                            },
                        });
                    Promise.resolve(prom).then(function (results) {
                        var dynamicFilters;
                        if (results) {
                            var ids = _.map(results, function (x) {
                                return x[0];
                            });
                            dynamicFilters = [{
                                description: _.str.sprintf(_t('Quick search: %s'), search_val),
                                domain: [['id', 'in', ids]],
                            }];
                        }
                        self._searchCreatePopup("search", false, {}, dynamicFilters);
                    });
                },
                classname: 'o_m2o_dropdown_option',
            });
            return values;
        }
    });
    registry.
        add('phd_lot_many2one_filter', PHDLotMany2one);
    return PHDLotMany2one;
});
