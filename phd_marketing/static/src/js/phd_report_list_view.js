odoo.define('phd_marketing.search_filters', function (require) {
"use strict";

    var core = require('web.core');
    var search_filters = require('web.search_filters');
    var search_filters_registry = require('web.search_filters_registry');
    var _t = core._t;
    var _lt = core._lt;

    var ExtendedSearchProposition = search_filters.ExtendedSearchProposition.extend({
        template: 'phd_marketing.SearchView.extended_search.proposition',

        select_field: function (field) {
            var self = this;
            if(this.attrs.selected !== null && this.attrs.selected !== undefined) {
                this.value.destroy();
                this.value = null;
                this.$('.o_searchview_extended_prop_op').html('');
            }
            this.attrs.selected = field;
            if(field === null || field === undefined) {
                return;
            }

            var type = field.type;
            var Field = search_filters_registry.getAny([type, "char"]);

            this.value = new Field(this, field);

            if (field.name == 'promotion_period_from' && type =='date') {
                this.value.operators = [{value: ">=", text: _lt("is after or equal to")}]
            } else if (field.name == 'promotion_period_to' && type =='date') {
                this.value.operators = [{value: "<=", text: _lt("is before or equal to")}]
            }
            _.each(this.value.operators, function (operator) {
                $('<option>', {value: operator.value})
                    .text(String(operator.text))
                    .appendTo(self.$('.o_searchview_extended_prop_op'));
            });
            var $value_loc = this.$('.o_searchview_extended_prop_value').show().empty();
            this.value.appendTo($value_loc);
        },
    });

    return {
        ExtendedSearchProposition: ExtendedSearchProposition,
    };
});

odoo.define('phd_marketing.filter', function (require) {
"use strict";

var config = require('web.config');
var Domain = require('web.Domain');
var controlPanelViewParameters = require('web.controlPanelViewParameters');
var FilterMenu = require('web.FilterMenu');
var search_filters = require('phd_marketing.search_filters');
var core = require('web.core');
var _t = core._t;
var QWeb = core.qweb;

var PHDFilterMenu = FilterMenu.extend({
        init: function (parent, filters, fields) {
            this._super(parent, filters);

            // determines where the filter menu is displayed and its style
            this.isMobile = config.device.isMobile;
            // determines when the 'Add custom filter' submenu is open
            this.generatorMenuIsOpen = false;
            this.propositions = [];
            this.fields = _.pick(fields, function (field, name) {
                return field.selectable !== false && name !== 'id';
            });
            this.fields.id = {string: 'ID', type: 'id', searchable: true};
            this.dropdownCategory = 'filter';
            this.dropdownTitle = _t('Date Ranges');
            this.dropdownIcon = 'fa fa-calendar';
            this.dropdownSymbol = this.isMobile ?
                                    'fa fa-chevron-right float-right mt4' :
                                    false;
            this.dropdownStyle.mainButton.class = 'o_filters_menu_button ' +
                                                    this.dropdownStyle.mainButton.class;
        },

        _commitSearch: function () {
            var filters = _.invoke(this.propositions, 'get_filter').map(function (preFilter) {
                return {
                    type: 'filter',
                    is_dateRange: true,
                    description: preFilter.attrs.string,
                    domain: Domain.prototype.arrayToString(preFilter.attrs.domain),
                };
            });
            this.trigger_up('new_filters', {filters: filters});
            _.invoke(this.propositions, 'destroy');
            this.propositions = [];
            this._toggleCustomFilterMenu();
        },

        _appendProposition: function (field = '') {
            var fields = null;
            if (field == 'promotion_period_from') {
                fields = { 'promotion_period_from':this.fields[field] }
            } else if (field == 'promotion_period_to') {
                fields = { 'promotion_period_to':this.fields[field] }
            }

            var prop = new search_filters.ExtendedSearchProposition(this, fields != null ? fields : this.fields);
            this.propositions.push(prop);
            this.$('.o_apply_filter').prop('disabled', false);
            return prop.insertBefore(this.$addFilterMenu);
        },

        _renderGeneratorMenu: function () {
            this.generatorMenuIsOpen = true;
            this.$el.find('.o_generator_menu').remove();
            if (!this.generatorMenuIsOpen) {
                _.invoke(this.propositions, 'destroy');
                this.propositions = [];
            }
            var $generatorMenu = QWeb.render('phd_marketing.FilterMenuGenerator', {widget: this});
            this.$menu.append($generatorMenu);
            this.$addFilterMenu = this.$menu.find('.o_add_filter_menu');
            if (this.generatorMenuIsOpen && !this.propositions.length) {
                this._appendProposition('promotion_period_from');
                this._appendProposition('promotion_period_to');
            }
            this.$dropdownReference.dropdown('update');
        },
    });
    return PHDFilterMenu;
});

odoo.define('phd_marketing.ControlPanelRenderer', function (require) {
"use strict";

    var PHDFilterMenu = require('phd_marketing.filter');
    var FavoriteMenu = require('web.FavoriteMenu');
    var FilterMenu = require('web.FilterMenu');
    var GroupByMenu = require('web.GroupByMenu');
    var Renderer = require('web.ControlPanelRenderer');

    var ControlPanelRenderer = Renderer.extend({
        _getMenuItems: function (menuType) {
            var menuItems;
            if (menuType === 'dateRange') {
                 return menuItems = this.state.filters;
            }
            return this._super.apply(this, arguments);
        },

        _setupMenu: function (menuType) {
            var Menu;
            var menu;
            if (menuType === 'dateRange') {
                Menu = PHDFilterMenu;
                    if (_.contains(['dateRange'], menuType)) {
                    menu = new Menu(this, this._getMenuItems(menuType), this.state.fields);
                }
                this.subMenus[menuType] = menu;
                return menu.appendTo(this.$subMenus);
            }
            return this._super.apply(this, arguments);
        },
    });
    return ControlPanelRenderer;
});

odoo.define('phd_marketing.ControlPanelController', function (require) {
"use strict";

var ControlPanelController = require('web.ControlPanelController');

var ControlPanelController = ControlPanelController.extend({

    _onNewFilters: function (ev) {
        ev.stopPropagation();
        if (ev.data.filters.length == 2 && ev.data.filters[0].is_dateRange)
        {
            var list_filters = ev.data.filters;
            for (var i = 0; i < list_filters.length;i++) {
                var filter = [list_filters[i]]
                this.model.createNewFilters(filter);
                this._reportNewQueryAndRender();
            }
        } else {
            this._super.apply(this, arguments);
        }
    },
});

return ControlPanelController;

});

odoo.define('phd_marketing.ControlPanelView', function (require) {
"use strict";

    var ControlPanelController = require('phd_marketing.ControlPanelController');
    var ControlPanelRenderer = require('phd_marketing.ControlPanelRenderer');
    var ControlPanelView = require('web.ControlPanelView');

    var ControlPanelView = ControlPanelView.extend({
            config: _.extend({}, ControlPanelView.prototype.config, {
                Renderer: ControlPanelRenderer,
                Controller: ControlPanelController,}),
        });
        return ControlPanelView;
    });

odoo.define('phd_marketing.report_list_view', function(require) {
    'use strict';
    var ListView = require('web.ListView');
    var ControlPanelView = require('phd_marketing.ControlPanelView');
    var viewRegistry = require('web.view_registry');

    var MarketingOrderReportView = ListView.extend({
        searchMenuTypes: ['filter', 'groupBy', 'favorite', 'dateRange'],

        _createControlPanel: function (parent) {
            var self = this;
            var controlPanelView = new ControlPanelView(this.controlPanelParams);
            return controlPanelView.getController(parent).then(function (controlPanel) {
                self.controllerParams.controlPanel = controlPanel;
                return controlPanel.appendTo(document.createDocumentFragment()).then(function () {
                    self._updateMVCParams(controlPanel.getSearchQuery());
                    return controlPanel;
                });
            });
        },
    });

    viewRegistry.add('mko_report_list_view', MarketingOrderReportView);
});