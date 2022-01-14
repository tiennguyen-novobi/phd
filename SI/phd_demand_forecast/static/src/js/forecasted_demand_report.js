odoo.define('phd_demand_forecast.ForecastedDemandReport', function (require) {
    "use strict";

    var AbstractAction = require('web.AbstractAction');
    var core = require('web.core');
    var QWeb = core.qweb;


    var ForecastedDemandReport = AbstractAction.extend({
        // contentTemplate: 'ForecastedDemandReportTemplate',
        hasControlPanel: true,
        xmlDependencies: [
            '/phd_demand_forecast/static/src/xml/forecasted_demand_report.xml',
        ],
        jsLibs: [
            '/web/static/lib/Chart/Chart.js',
        ],
        events: {
            'click .clickable': '__onOpenRecord',
        },
        start: function () {
            this._super.apply(this, arguments);
            this.renderReport()
        },
        __getReportData: async function () {
            return await this._rpc({
                model: 'demand.forecast.report',
                method: 'get_forecasted_report_data',
                context: {'report_product_id': this.controlPanelParams.context.active_id}
            })
        },

        renderReport: async function () {
            let res = await this.__getReportData();
            res.canvasID = _.uniqueId('canvas');
            res['headerContent'].lastUpdate = this._formatDatetime(res['headerContent'].lastUpdate);
            this.$('.o_content').html($(QWeb.render('ForecastedDemandReportTemplate', {widget: res})));
            this.factor = res['formatFactor'];
            this.renderChart(res['bodyContent'].chartConfig, res.canvasID)
        },
        renderChart: function (chartConfig = false, canvasID) {
            if (chartConfig) {
                let context = this.$(`#${canvasID}`)[0].getContext('2d');
                let factor = this.factor;
                chartConfig.options.tooltips.callbacks ={
                        title: (tooltipItems, data) => {
                            var axis_label = tooltipItems[0].label;
                            if (data.tooltip_extend_labels){
                                axis_label += ` (${data.tooltip_extend_labels[tooltipItems[0].index]})`
                            }
                            return axis_label;
                        },
                        label: function(tooltipItem, data){
                            let value = data.datasets[tooltipItem.datasetIndex].data[tooltipItem.index];
                            return `${data.datasets[tooltipItem.datasetIndex].label}: ${value.toLocaleString('en-US', {minimumFractionDigits: factor})}`
                        }
                };
                new Chart(context, chartConfig);
            }
        },
        __onOpenRecord: function (evt) {
            evt.stopPropagation();
            console.log(evt);
            let eventElement = evt.currentTarget;
            let modelName = eventElement.getAttribute('model');
            let resID = eventElement.getAttribute('res_id');
            if (modelName && resID > 0) {
                this.__openOpenRecordAction(modelName, resID);
            }
        },
        __openOpenRecordAction: function (modelName, resID) {
            this.do_action({
                'type': 'ir.actions.act_window',
                'res_model': modelName,
                'view_mode': 'form',
                'view_type': 'form',
                'res_id': parseInt(resID),
                'views': [[false, 'form']],
            });
        },
        _formatDatetime: function (value) {
            if (value && value != '') {
                let date = new moment(value);
                return new moment(date).format("MMM DD, h:mm A");
            }
            return '';
        },
    });

    core.action_registry.add('forecasted_demand_report', ForecastedDemandReport);
    return ForecastedDemandReport;
});
