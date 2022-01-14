odoo.define('phd.web.hide.add.line.detailed.operation.renderer', function (require) {
"use strict";
    var ListRenderer = require('web.ListRenderer');
    var FieldOne2Many = require('web.relational_fields').FieldOne2Many;
    var FieldRegistry = require('web.field_registry');
    var PHDListRenderer = ListRenderer.extend({
           init: function (parent, state, params) {
                this._super.apply(this, arguments);
                if (this.addCreateLine) {
                    if (parent.recordData.hide_add_line_detailed_operation && parent.attrs.name == "move_line_ids_without_package") {
                        this.addCreateLine = false;
                    }
                }
            },
    });

    var PHDFieldOne2Many = FieldOne2Many.extend({
        _getRenderer: function (){
            if (this.view.arch.tag === 'tree'){
                return PHDListRenderer;
            }
            return this._super.apply(this, arguments);
        },
    });

    FieldRegistry.add('remove_add_line', PHDFieldOne2Many);
});