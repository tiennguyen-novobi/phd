odoo.define('phd_tool.search_filters', function (require) {
"use strict";

    var core = require('web.core');
    var search_filters = require('web.search_filters');
    var search_filters_registry = require('web.search_filters_registry');
    var _t = core._t;
    var _lt = core._lt;

    var ExtendedSearchProposition = search_filters.ExtendedSearchProposition.extend({
        template: 'phd_tool.SearchView.extended_search.proposition',

        init: function (parent, fields) {
            this._super.apply(this, arguments);
            if (this.__parentedParent.__parentedParent.context.date_range != undefined) {
                this.date_range = this.__parentedParent.__parentedParent.context.date_range;
            } else {
                this.date_range = '';
            }
        },

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
            this.value.operators = [{value: "between", text: _lt("is between")}];
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

odoo.define('phd_tool.filter', function (require) {
"use strict";

var config = require('web.config');
var Domain = require('web.Domain');
var controlPanelViewParameters = require('web.controlPanelViewParameters');
var FilterMenu = require('web.FilterMenu');
var search_filters = require('phd_tool.search_filters');
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

        _appendProposition: function () {
            Object.filter = (obj, predicate) =>
            Object.keys(obj)
                  .filter( key => predicate(obj[key]) )
                  .reduce( (res, key) => (res[key] = obj[key], res), {} );
            this.fields = Object.filter(this.fields, field => field.type == 'datetime')
            var fields = this.fields;
            var prop = new search_filters.ExtendedSearchProposition(this, this.fields);
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
            var $generatorMenu = QWeb.render('phd_tool.FilterMenuGenerator', {widget: this});
            this.$menu.append($generatorMenu);
            this.$addFilterMenu = this.$menu.find('.o_add_filter_menu');
            if (this.generatorMenuIsOpen && !this.propositions.length) {
               this._appendProposition();
            }
            this.$dropdownReference.dropdown('update');
        },
    });
    return PHDFilterMenu;
});

odoo.define('phd_tool.ControlPanelRenderer', function (require) {
"use strict";

    var PHDFilterMenu = require('phd_tool.filter');
    var FavoriteMenu = require('web.FavoriteMenu');
    var FilterMenu = require('web.FilterMenu');
    var GroupByMenu = require('web.GroupByMenu');
    var Renderer = require('web.ControlPanelRenderer');

    var ControlPanelRenderer = Renderer.extend({
        _getMenuItems: function (menuType) {
            var menuItems;
            if (menuType === 'dateRange') {
                 return menuItems = [];
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

odoo.define('phd_tool.ControlPanelView', function (require) {
"use strict";

    var ControlPanelRenderer = require('phd_tool.ControlPanelRenderer');
    var ControlPanelView = require('web.ControlPanelView');

    var ControlPanelView = ControlPanelView.extend({
            config: _.extend({}, ControlPanelView.prototype.config, {
                Renderer: ControlPanelRenderer,}),
        });
        return ControlPanelView;
    });

odoo.define('phd_tool.date_range_list_view', function(require) {
    'use strict';
    var ListView = require('web.ListView');
    var ControlPanelView = require('phd_tool.ControlPanelView');
    var viewRegistry = require('web.view_registry');

    var ReportView = ListView.extend({
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

    viewRegistry.add('phd_tool_date_range_list_view', ReportView);
});