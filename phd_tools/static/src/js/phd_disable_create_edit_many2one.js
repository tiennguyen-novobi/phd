odoo.define('phd_tools.web.disable.create.edit.many2one', function (require) {
    "use strict";
    var relational_fields = require('web.relational_fields');
    var view_dialogs = require('web.view_dialogs')
    var PartnerField = require('partner.autocomplete.many2one');
    var core = require('web.core');
    var dom = require('web.dom');
    var _t = core._t;
    var FieldMany2One = relational_fields.FieldMany2One;
    var SelectCreateDialog = view_dialogs.SelectCreateDialog;

    PartnerField.include({
        _searchSuggestions: function (search_val) {
            var context = this.record.getContext(this.recordParams);
            if (!context.is_disable_create_edit_many2one) {
                return this._super(search_val);
            }
        },
    });

    FieldMany2One.include({
        _onExternalButtonClick: function () {
            var context = this.record.getContext(this.recordParams);
            if (context.is_disable_create_edit_many2one) {
                this.can_write = false;
            }
            this._super.apply(this, arguments);
        },

        _onInputFocusout: function () {
            var context = this.record.getContext(this.recordParams);
            if (!context.is_disable_create_edit_many2one) {
                this._super.apply(this, arguments);
            }
        },

        _search: function (search_val) {
            var self = this;
            var def = new Promise(function (resolve, reject) {
                var context = self.record.getContext(self.recordParams);
                var domain = self.record.getDomain(self.recordParams);

                // Add the additionalContext
                _.extend(context, self.additionalContext);

                var blacklisted_ids = self._getSearchBlacklist();
                if (blacklisted_ids.length > 0) {
                    domain.push(['id', 'not in', blacklisted_ids]);
                }

                self._rpc({
                    model: self.field.relation,
                    method: "name_search",
                    kwargs: {
                        name: search_val,
                        args: domain,
                        operator: "ilike",
                        limit: self.limit + 1,
                        context: context,
                    }
                }).then(function (result) {
                    // possible selections for the m2o
                    var values = _.map(result, function (x) {
                        x[1] = self._getDisplayName(x[1]);
                        return {
                            label: _.str.escapeHTML(x[1].trim()) || data.noDisplayContent,
                            value: x[1],
                            name: x[1],
                            id: x[0],
                        };
                    });

                    // search more... if more results than limit
                    if (values.length > self.limit) {
                        values = self._manageSearchMore(values, search_val, domain, context);
                    }
                    var create_enabled = self.can_create && !self.nodeOptions.no_create;
                    // quick create
                    var raw_result = _.map(result, function (x) {
                        return x[1];
                    });
                    if (!context.is_disable_create_edit_many2one) {
                        if (create_enabled && !self.nodeOptions.no_quick_create &&
                            search_val.length > 0 && !_.contains(raw_result, search_val)) {
                            values.push({
                                label: _.str.sprintf(_t('Create "<strong>%s</strong>"'),
                                    $('<span />').text(search_val).html()),
                                action: self._quickCreate.bind(self, search_val),
                                classname: 'o_m2o_dropdown_option'
                            });
                        }
                    }
                    // create and edit ...
                    if (create_enabled && !self.nodeOptions.no_create_edit) {
                        var createAndEditAction = function () {
                            // Clear the value in case the user clicks on discard
                            self.$('input').val('');
                            return self._searchCreatePopup("form", false, self._createContext(search_val));
                        };
                        if (!context.is_disable_create_edit_many2one) {
                            values.push({
                                label: _t("Create and Edit..."),
                                action: createAndEditAction,
                                classname: 'o_m2o_dropdown_option',
                            });
                        }
                    } else if (values.length === 0) {
                        values.push({
                            label: _t("No results to show..."),
                        });
                    }

                    resolve(values);
                });
            });
            this.orderer.add(def);
            return def;
        },
    });

    SelectCreateDialog.include({
        init: function (parent, options) {
            this._super(parent, options);
            var context = this.context;
            if (context.is_disable_create_edit_many2one) {
                this.options.no_create = true;
            }
        },
    })

    return {
        FieldMany2One: FieldMany2One,
        SelectCreateDialog: SelectCreateDialog,
    };
});