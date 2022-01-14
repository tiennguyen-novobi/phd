odoo.define('phd_stock_status_report.limited_date_widget', function (require) {
    "use strict";

    var basic_fields = require('web.basic_fields');
    var registry = require('web.field_registry');

    var RelationLimitedDate = basic_fields.FieldDate.extend({
        className: 'o_field_date edit_style_on_read',
        init: function (parent, name, options) {
            this.parent = parent;
            this._super.apply(this, arguments);
            this.formatType = 'date';
            this.mode = 'edit';
            let endDateConfig = {hour: 23, minute: 59, second: 59};
            this.value.set(endDateConfig);
            if (this.datepickerOptions.minDate) {
                this.datepickerOptions.minDate = (moment.isMoment(
                    this.recordData[this.datepickerOptions.minDate]) ?
                    this.recordData[this.datepickerOptions.minDate] : '0001-01-01')
            }
            if (this.datepickerOptions.startFromToday) {
                this.datepickerOptions.minDate = new moment(new Date()).add(-1, 'day');
            }
            if (this.datepickerOptions.maxDate) {
                this.datepickerOptions.maxDate = (moment.isMoment(
                    this.datepickerOptions.maxDate) ?
                    this.recordData[this.datepickerOptions.maxDate] : '9999-01-01')
            }
        },
    });

    registry.add('limited_date', RelationLimitedDate)
});