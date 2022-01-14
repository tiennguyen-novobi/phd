odoo.define('phd_mrp.mrp_order_calendar', function(require) {
    'use strict';

    var core = require('web.core');
    var CalendarController = require("web.CalendarController");
    var CalendarModel = require('web.CalendarModel');
    var CalendarRenderer = require('web.CalendarRenderer');
    var CalendarView = require('web.CalendarView');
    var viewRegistry = require('web.view_registry');
    var qweb = core.qweb;

    var MrpOrderCalendarRenderer = CalendarRenderer.extend({
        _eventRender: function (event) {
            var qweb_context = {
                event: event,
                record: event.record,
                color: this.getColor(event.color_index),
            };
            this.qweb_context = qweb_context;
            if (_.isEmpty(qweb_context.record)) {
                return '';
            } else {
                return qweb.render("phd-mrp-order-calendar-box", qweb_context);
            }
        },
    });

    var MrpOrderCalendarView = CalendarView.extend({
        config: _.extend({}, CalendarView.prototype.config, {
            Controller: CalendarController,
            Model: CalendarModel,
            Renderer: MrpOrderCalendarRenderer,
        }),
    });

    viewRegistry.add('phd_mrp_order_calendar', MrpOrderCalendarView);
});
