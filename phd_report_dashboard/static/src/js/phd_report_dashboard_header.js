odoo.define('phd_report_dashboard.header', function (require) {
    "use strict";

    var core = require('web.core');
    var KanbanController = require('web.KanbanController');
    var KanbanModel = require('web.KanbanModel');
    var KanbanRenderer = require('web.KanbanRenderer');
    var KanbanView = require('web.KanbanView');
    var view_registry = require('web.view_registry');

    var QWeb = core.qweb;

    var _t = core._t;
    var _lt = core._lt;

    var HeaderPHDRenderer = KanbanRenderer.extend({
        _render: function () {
            var self = this;
            return this._super.apply(this, arguments).then(function () {
                var data = self.state.dashboardValues;
                debugger;
                self._render_header(data);
            });
        },

        _render_header: function (data) {
            var self = this;
            debugger;
            var account_dashboard_dashboard = QWeb.render('phd_report_dashbord.PHDDashboard', {
                widget: self,
                data: data
            });
            self.$el.prepend(account_dashboard_dashboard);
        },
    });

    var HeaderPHDModel = KanbanModel.extend({
        /**
         * @override
         */
        init: function () {
            debugger;
            this.dashboardValues = {};
            this._super.apply(this, arguments);

        },

        get: function (localID) {
            var result = this._super.apply(this, arguments);
            if (_.isObject(result)) {
                result.dashboardValues = this.dashboardValues[localID];
            }
            return result;
        },

        load: function () {
            return this._loadDemo(this._super.apply(this, arguments));
        },

        reload: function () {
            return this._loadDemo(this._super.apply(this, arguments));
        },

        _loadDemo: function (super_def) {
            var self = this;
            var dashboard_def = this._rpc({
                model: 'phd.report.dashboard',
                method: 'phd_report_dashboard_header_render',
            });
            return $.when(super_def, dashboard_def).then(function(id, dashboardValues) {
                self.dashboardValues[id] = dashboardValues;
                return id;
            });
        },
    });

    var HeaderPHDController = KanbanController.extend({
    });

    var HeaderPHDView = KanbanView.extend({
        config: _.extend({}, KanbanView.prototype.config, {
            Model: HeaderPHDModel,
            Renderer: HeaderPHDRenderer,
            Controller: HeaderPHDController,
        }),
        display_name: _lt('Dashboard'),
        icon: 'fa-dashboard',
        searchview_hidden: true,
    });

    view_registry.add('phd_report_dashboard_header', HeaderPHDView);

    return {
        Model: HeaderPHDModel,
        Renderer: HeaderPHDRenderer,
        Controller: HeaderPHDController,
    };

});
