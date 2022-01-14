odoo.define('phd_stock.forecasted_quantity_report', function (require) {
'use strict';

var core = require('web.core');
var AbstractAction = require('web.AbstractAction');
var accountReportsWidget = require('account_reports.account_report');

var forecastedQuantityReportWidget = accountReportsWidget.extend({
    filter_accounts: function(e) {
        var filter_products = [];
        var self = this;
        var query = e.target.value.trim().toLowerCase();
        this.$('.o_account_reports_level2').each(function(index, el) {
            var $accountReportLineFoldable = $(el);
            var line_id = $accountReportLineFoldable.find('.o_account_report_line').data('id');
            var $childs = self.$('tr[data-parent-id="'+line_id+'"]');
            var lineText = $accountReportLineFoldable.find('.account_report_line_name')
                .contents().get(0).nodeValue
                .trim();
            var queryFound = lineText.split(' ').some(function (str) {
                return str.toLowerCase().includes(query);
            });
            if (queryFound) {
                filter_products.push(line_id);
            }
            $accountReportLineFoldable.toggleClass('o_account_reports_filtered_lines', !queryFound);
            $childs.toggleClass('o_account_reports_filtered_lines', !queryFound);
        });
        this.report_options['filter_accounts'] = filter_products;
    },

    unfold_all: function(bool) {
        var self = this;
        var lines = this.$el.find('.js_account_report_foldable');
        self.report_options.unfold_lines = [];
        if (bool) {
            _.each(lines, function(el) {
                self.report_options.unfold_lines.push($(el).data('id'));
            });
        }
    },
});

core.action_registry.add('forecasted_quantity_report', forecastedQuantityReportWidget);

return forecastedQuantityReportWidget;

});
