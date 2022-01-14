odoo.define('phd.partner.autocomplete.many2one.remove.vat', function (require) {
'use strict';

var FieldMany2One = require('web.relational_fields').FieldMany2One;
var core = require('web.core');
var AutocompleteMixin = require('partner.autocomplete.Mixin');
var field_registry = require('web.field_registry');
var PartnerField = require('partner.autocomplete.many2one');
var _t = core._t;

var PHDPartnerField = PartnerField.extend(AutocompleteMixin, {

    init: function () {
            this._super.apply(this, arguments);
            this.additionalContext['show_vat'] = false;
        },
    });

    field_registry.add('res_partner_many2one_remove_vat', PHDPartnerField);

    return PHDPartnerField;
});
