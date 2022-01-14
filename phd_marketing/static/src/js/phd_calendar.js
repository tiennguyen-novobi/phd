odoo.define('phd_marketing.mko_calendar', function(require) {
    'use strict';

    var core = require('web.core');
    var CalendarController = require("web.CalendarController");
    var CalendarModel = require('web.CalendarModel');
    var CalendarRenderer = require('web.CalendarRenderer');
    var CalendarView = require('web.CalendarView');
    var viewRegistry = require('web.view_registry');
    var qweb = core.qweb;

    var MarketingOrderCalendarRenderer = CalendarRenderer.extend({
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
                return qweb.render("phd-calendar-box", qweb_context);
            }
        },
    });

    var MarketingOrderCalendarView = CalendarView.extend({
        config: _.extend({}, CalendarView.prototype.config, {
            Controller: CalendarController,
            Model: CalendarModel,
            Renderer: MarketingOrderCalendarRenderer,
        }),
    });

    viewRegistry.add('marketing_order_calendar', MarketingOrderCalendarView);
});
