odoo.define('phd_tools.sum.avg.ListRenderer', function (require) {

    var ListRenderer = require('web.ListRenderer');
    var config = require('web.config');
    var core = require('web.core');
    var dom = require('web.dom');
    var field_utils = require('web.field_utils');
    var Pager = require('web.Pager');
    var utils = require('web.utils');
    var viewUtils = require('web.viewUtils');
    var rpc = require('web.rpc');
    var _t = core._t;

    var SumAvgListRenderer = ListRenderer.extend({
        willStart: function() {
            var _this = this;
            var createtine_cost = this._rpc({
                model: 'product.product',
                method: 'get_createtine_cost',
            }).then(function (result) {
                _this.createtine_cost = result;
            });
            return Promise.all([this._super.apply(this, arguments), createtine_cost]);
        },
       _renderAggregateCells: function (aggregateValues) {
            var self = this;
            return _.map(this.columns, function (column) {
                var $cell = $('<td>');
                if (config.isDebug()) {
                    $cell.addClass(column.attrs.name);
                }
                if (column.attrs.editOnly) {
                    $cell.addClass('oe_edit_only');
                }
                if (column.attrs.readOnly) {
                    $cell.addClass('oe_read_only');
                }
                if (column.attrs.name in aggregateValues) {
                    var field = self.state.fields[column.attrs.name];
                    if (aggregateValues[column.attrs.name].constructor == Array) {
                        var html = '';
                        for ( var i = 0; i < aggregateValues[column.attrs.name].length; i++) {
                            var object = JSON.parse(aggregateValues[column.attrs.name][i]['help']);
                            var formatFunc = field_utils.format[object['widget']];
                            if (!formatFunc) {
                                formatFunc = field_utils.format[field.type];
                            }
                            var formattedValue = formatFunc(aggregateValues[column.attrs.name][i].value, field, {
                                escape: true,
                                digits: column.attrs.digits ? JSON.parse(object['digits']) : undefined,
                            });
                            html += formattedValue + '<br>';
                            if (object['is_createtine_in_dollar'] != undefined) {
                                var formatFunc = field_utils.format[object['is_createtine_in_dollar']['widget']];
                                if (!formatFunc) {
                                    formatFunc = field_utils.format[field.type];
                                }

                                var formattedValue = formatFunc(aggregateValues[column.attrs.name][i].value * self.createtine_cost, field, {
                                        escape: true,
                                        digits: column.attrs.digits ? JSON.parse(object['is_createtine_in_dollar']['widget']) : undefined,
                                    });
                                    html += formattedValue + '<br>';
                            }
                        }

                        $cell.addClass('o_list_number').attr('title', help).html(html);
                    }
                    else {
                        var value = aggregateValues[column.attrs.name].value;
                        var help = aggregateValues[column.attrs.name].help;
                        var formatFunc = field_utils.format[column.attrs.widget];
                        if (!formatFunc) {
                            formatFunc = field_utils.format[field.type];
                        }
                        var formattedValue = formatFunc(value, field, {
                            escape: true,
                            digits: column.attrs.digits ? JSON.parse(column.attrs.digits) : undefined,
                        });
                        $cell.addClass('o_list_number').attr('title', help).html(formattedValue);
                    }
                }
                return $cell;
            });
        },

        _computeColumnAggregates: function (data, column) {
            var attrs = column.attrs;
            var field = this.state.fields[attrs.name];
            if (!field) {
                return;
            }
            var type = field.type;
            if (type !== 'integer' && type !== 'float' && type !== 'monetary') {
                return;
            }
            var func = (attrs.sum && 'sum') || (attrs.avg && 'avg') ||
                (attrs.max && 'max') || (attrs.min && 'min');
            if (func) {
                var count = 0;
                var aggregateValue = 0;
                if (func === 'max') {
                    aggregateValue = -Infinity;
                } else if (func === 'min') {
                    aggregateValue = Infinity;
                }
                _.each(data, function (d) {
                    count += 1;
                    var value = (d.type === 'record') ? d.data[attrs.name] : d.aggregateValues[attrs.name];
                    if (func === 'avg') {
                        aggregateValue += value;
                    } else if (func === 'sum') {
                        aggregateValue += value;
                    } else if (func === 'max') {
                        aggregateValue = Math.max(aggregateValue, value);
                    } else if (func === 'min') {
                        aggregateValue = Math.min(aggregateValue, value);
                    }
                });
                if (attrs.sum && attrs.avg) {
                    aggregateAvgValue = count ? aggregateValue / count : aggregateValue;
                    column.aggregate = [{
                        help: attrs['sum'],
                        value: aggregateValue,
                    },{ help: attrs['avg'],
                        value: aggregateAvgValue,} ];
                }
                else {
                    if (func === 'avg') {
                        aggregateValue = count ? aggregateValue / count : aggregateValue;
                    }
                    column.aggregate = {
                        help: attrs[func],
                        value: aggregateValue,
                    };
                }
            }
        },
    });

    return SumAvgListRenderer;
});
