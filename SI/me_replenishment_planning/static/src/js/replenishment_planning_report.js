odoo.define('replenishment_planning_report.replenishment_planning_report', function (require) {
    'use strict';

    var core = require('web.core');
    var time = require('web.time');
    var framework = require('web.framework');
    var StandaloneFieldManagerMixin = require('web.StandaloneFieldManagerMixin');
    var RelationalFields = require('web.relational_fields');
    var stock_report_generic = require('stock.stock_report_generic');
    var utils = require('web.utils');
    var QWeb = core.qweb;
    var _t = core._t;
    var Widget = require('web.Widget');
    var round_pr = utils.round_precision;

    var ReplenishmentPlanReportFilters = Widget.extend(StandaloneFieldManagerMixin, {
        /**
         * @constructor
         * @param {Object} fields
         */
        init: function (parent, fields) {
            this._super.apply(this, arguments);
            StandaloneFieldManagerMixin.init.call(this);
            this.fields = fields;
            this.widgets = {};
        },
        /**
         * @override
         */
        willStart: function () {
            var self = this;
            var defs = [this._super.apply(this, arguments)];
            _.each(this.fields, function (field, fieldName) {
                defs.push(self._makeM2MWidget(field, fieldName));
            });
            return Promise.all(defs);
        },
        /**
         * @override
         */
        start: function () {
            var self = this;
            var $content = $(QWeb.render("me_replenishment_planning.fields_widget_table", {fields: this.fields}));
            self.$el.append($content);
            _.each(this.fields, function (field, fieldName) {
                self.widgets[fieldName].appendTo($content.find('#' + fieldName + '_field'));
            });
            return this._super.apply(this, arguments);
        },

        //--------------------------------------------------------------------------
        // Private
        //--------------------------------------------------------------------------

        /**
         * This method will be called whenever a field value has changed and has
         * been confirmed by the model.
         *
         * @private
         * @override
         * @returns {Deferred}
         */
        _confirmChange: function () {
            var self = this;
            var result = StandaloneFieldManagerMixin._confirmChange.apply(this, arguments);
            var data = {};
            _.each(this.fields, function (filter, fieldName) {
                if (filter['type'] == 'many2one') {
                    data[fieldName] = self.widgets[fieldName].value.res_id;
                } else {
                    data[fieldName] = self.widgets[fieldName].value.res_ids;
                }
            });
            this.trigger_up('value_changed', data);
            return result;
        },
        /**
         * This method will create a record and initialize M2M widget.
         *
         * @private
         * @param {Object} fieldInfo
         * @param {string} fieldName
         * @returns {Deferred}
         */
        _makeM2MWidget: function (fieldInfo, fieldName) {
            var self = this;
            var options = {};
            options[fieldName] = {
                options: {
                    no_create_edit: true,
                    no_create: true,
                }
            };
            var field_data = {
                fields: [{
                    name: 'id',
                    type: 'integer',
                }, {
                    name: 'display_name',
                    type: 'char',
                }],
                name: fieldName,
                relation: fieldInfo.modelName,
                type: fieldInfo.type,
            }
            if (fieldInfo.value != [] || fieldInfo.value != false) {
                field_data.value = fieldInfo.value
            }
            return this.model.makeRecord(fieldInfo.modelName, [field_data], options).then(function (recordID) {
                if (fieldInfo.type == 'many2one') {
                    self.widgets[fieldName] = new RelationalFields.FieldMany2One(self,
                        fieldName,
                        self.model.get(recordID),
                        {mode: 'edit',});
                } else {
                    self.widgets[fieldName] = new RelationalFields.FieldMany2ManyTags(self,
                        fieldName,
                        self.model.get(recordID),
                        {mode: 'edit',});
                }
                self._registerWidget(recordID, fieldName, self.widgets[fieldName]);
            });
        },
    });

    var ReplenishmentPlanReport = stock_report_generic.extend({
        init: function (parent, action) {
            var res = this._super.apply(this, arguments);
            this.given_context.product_ids = action.context.product_ids || [];
            this.given_context.product_info = action.context.product_info || {};
            this.given_context.warehouse_id = action.context.warehouse_id || false;
            if (!this.given_context.warehouse_id) {
                this._get_default_warehouse_id()
            }
            ;
            return res;
        },

        events: {
            'click .o_mrp_bom_unfoldable': '_onClickUnfold',
            'click .o_mrp_bom_foldable': '_onClickFold',
            'click .o_mrp_bom_action': '_onClickAction',
            'click .o_mrp_bom_next': '_onClickNext',
            'click .o_mrp_bom_back': '_onClickBack',
            'change .o_mrp_bom_select_bom': '_onSelectParentBOM',
            'change .select_bom': '_onSelectChildBOM',
            'change .po_perc': '_onChangePOPercentage',
            'change .po_qty': '_onChangePOQty',
            'change .mo_qty': '_onChangeMOQty',
            'change .order_qty': '_onChangeOrderQty',
            'change .requested_quantity': '_onChangeRequestedQuantity',
            'click .o_detail_transaction_action': '_onClickOpenDetailTransaction',
            'click .ex-in-button': '_onClickExInButton',
        },

        custom_events: {
            'value_changed': function (ev) {
                // console.log('value_changed');
                var self = this;

                self.given_context.product_ids = ev.data.product_ids;
                self.given_context.warehouse_id = ev.data.warehouse_id;

                return self._reload().then(function () {
                    // self.$searchView.find('.bom_filter').click();
                    _.each(self.$el.find('.requested_quantity'), function (item) {
                        if (item.localName === 'input') {
                            $(item).change()
                        }
                    });
                    _.each(self.$el.find('.mo_qty'), function (k) {
                        $(k).change();
                    });
                    _.each(self.$el.find('.po_qty'), function (k) {
                        $(k).change();
                    });
                });
            },
        },

        _get_default_warehouse_id: function () {
            let self = this;
            return this._rpc({
                model: 'report.replenishment_planning_report',
                method: 'get_default_warehouse_id',
                args: [[],],
                context: this.given_context,
            }).then(function (warehouse_id) {
                self.given_context.warehouse_id = warehouse_id;
            }).guardedCatch(framework.unblockUI);
        },

        _refreshOrderInfo: function () {
            // console.log('_refreshOrderInfo');
            let self = this;

            _.each(this.$el.find('.mo_qty'), function (k) {
                $(k).change();
            });
            _.each(this.$el.find('.po_qty'), function (k) {
                $(k).change();
            });

            _.each(this.$el.find('.po_perc'), function (k) {
                $(k).change();
            });

            let productIDSet = new Set();
            _.each(this.$el.find('.lacking_quantity'), function (k) {
                let $parent = $(k.closest('tr'));

                productIDSet.add($parent.data('product_id'));
            });

            let productIDArr = Array.from(productIDSet);
            productIDArr.forEach(productID => {
                self._computeLackingQuantity(productID);
            });

            $(".include-button:not(.hide-background)").click();

            self._foldAllButtonConfig();

        },

        _refreshView: function () {
            // console.log('_refreshView');
            _.each(this.$el.find('input.requested_quantity'), function (k) {
                $(k).change();
            });
            this._refreshOrderInfo();
        },

        _reCalculateRequestedQty: function () {
            _.each(this.$el.find('input.requested_quantity'), function (k) {
                $(k).change();
            });
        },

        // We need this method to re-render the control panel when going back in the breadcrumb
        do_show: function () {
            // console.log('do_show');
            this._super.apply(this, arguments);
            this._reload();
        },

        start: function () {
            // console.log('start');
            var self = this;
            return this._super.apply(this, arguments).then(function () {
                _.each(self.$el.find('.requested_quantity'), function (item) {
                    if (item.localName === 'input') {
                        $(item).change()
                    }
                });
                self._reload();
            });
        },

        get_html: function () {
            // console.log('get_html');
            let self = this,
                existedPids = this.$el === undefined ? [] : _.map(self.$el.find('[data-parent_id="-1"]'),
                    function (p) {
                        return Number(p.dataset.product_id);
                    }),
                product_ids = self.given_context.product_ids.filter(n => !existedPids.includes(n)),
                append_content = existedPids.length > 0,
                currentWarehouseID = self.given_context.warehouse_id;

            let args = [product_ids, currentWarehouseID, append_content],
                parentEle = this.$el != undefined && self.$el.find('[data-parent_id="-1"]') || [];
            if (parentEle.length > 0 && parentEle.data('warehouse_id') != currentWarehouseID) {
                args = [self.given_context.product_ids,
                    currentWarehouseID ? currentWarehouseID : parentEle.data('warehouse_id'),
                    false];
            }

            return this._rpc({
                model: 'report.replenishment_planning_report',
                method: 'get_html',
                args: args,
                context: this.given_context,
            }).then(function (result) {
                self.data = result;
            }).guardedCatch(framework.unblockUI);
        },

        set_html: function () {
            // console.log('set_html');
            var self = this;
            return this._super().then(function () {
                self.$('.o_content').html(self.data.lines);
                self.renderSearch();
                self.renderButtons();
                self.update_cp();
            });
        },

        render_html: function (event, $el, result) {
            // console.log('render_html');
            $el.after(result);
            $(event.currentTarget).toggleClass('o_mrp_bom_foldable o_mrp_bom_unfoldable fa-caret-right fa-caret-down');
        },

        update_cp: function () {
            // console.log('update_cp');
            var status = {
                cp_content: {
                    $buttons: this.$buttons,
                    $searchview_buttons: this.$searchView
                },
            };
            return this.updateControlPanel(status);
        },

        _reload: function () {
            // console.log('_reload');
            var self = this;
            return this.get_html().then(function () {
                if (self.data.lines !== false) {
                    self.$('.o_content').html(self.data.lines);
                }
                if (self.data.extend_lines !== false) {
                    self.$el.find('.o_mrp_bom_report_page tbody').append($(self.data.extend_lines));
                }

                self._removeRedundantFG();

                let header = self.$el.find('.o_mrp_bom_report_page thead th'),
                    length = header.length;
                for (let i = 0; i < length; i++) {
                    self._stickyElement($(header[i]), i === length - 1);
                }

                self._refreshView();
            });
        },

        _stickyElement: function (ele, last = false, transparent = false) {
            ele.css({
                'position': 'sticky',
                'top': 0,
                'background': transparent ? 'transparent' : '#fff',
                'z-index': 1
            });
            if (last) {
                ele.css({
                    'padding-right': '30px !important',
                });
            }
        },

        _removeRedundantFG: function () {
            // console.log('_removeRedundantFG');
            let productIds = this.given_context.product_ids,
                self = this;
            _.each(self.$el.find('[data-parent_id="-1"]'), function ($fg) {
                let fgID = self._convertTextToNumber($fg.dataset.product_id);
                if (!productIds.includes(fgID)) {
                    self._removeItemsFG($fg)
                }
            })
        },

        _removeItemsFG: function (fg) {
            // console.log('_removeItemsFG');
            let currentLine = fg;
            while (currentLine) {
                let nextLine = currentLine.nextElementSibling;
                currentLine.remove();
                currentLine = nextLine;
                if (currentLine && currentLine.dataset.parent_id === "-1") {
                    break
                }
            }

        },

        //--------------------------------------------------------------------------
        // Render Actions
        //--------------------------------------------------------------------------
        renderButtons: function () {
            var self = this;
            this.$buttons = $(QWeb.render("me_replenishment_planning.buttons", {}));
            let createPurchaseOrder = this.$buttons.filter('.create_purchase_orders'),
                createManufacturingOrders = this.$buttons.filter('.create_manufacturing_orders'),
                autoReplenish = this.$buttons.filter('.auto_replenish');

            createPurchaseOrder.on('click', self._onClickCreatePurchaseOrders.bind(this));
            createManufacturingOrders.on('click', self._onClickManufacturingOrders.bind(this));
            autoReplenish.on('click', self._onClickAutoReplenish.bind(this));

            return this.$buttons;
        },

        renderSearch: function () {
            this.$searchView = $(QWeb.render('me_replenishment_planning.report_replenishment_planning_search', _.omit(this.data, 'lines')));
            // product filter
            if (!this.ReplenishmentPlanReportFilters) {
                var fields = {};
                fields['product_ids'] = {
                    label: _t('Products'),
                    modelName: 'product.product',
                    value: this.given_context.product_ids,
                    type: 'many2many',
                };
                fields['warehouse_id'] = {
                    label: _t('Warehouse'),
                    modelName: 'stock.warehouse',
                    value: this.given_context.warehouse_id,
                    type: 'many2one',
                };
                if (!_.isEmpty(fields)) {
                    this.ReplenishmentPlanReportFilters = new ReplenishmentPlanReportFilters(this, fields);
                    this.ReplenishmentPlanReportFilters.appendTo(this.$searchView.find('.js_m2m'));
                }
            } else {
                this.$searchView.find('.js_m2m').append(this.ReplenishmentPlanReportFilters.$el);
            }

        },

        _onSelectParentBOM: function (ev) {
            this.given_context.active_id = Number($(ev.currentTarget).val());
            this._reload();
        },

        _onSelectChildBOM: function (ev) {
            ev.preventDefault();
            let self = this,
                warehouse_id = self.given_context.warehouse_id,
                $currentTarget = $(ev.currentTarget),
                $parent = $currentTarget.closest('tr'),
                parentBomID = $parent.data('parent_id'),
                activeID = Number($(ev.currentTarget).val()),
                productID = $parent.data('product_id'),
                lineID = $parent.data('line'),
                qty = $parent.data('qty'),
                bom_ids = $parent.data('bom_ids'),
                is_root = $parent.data('is_root'),
                level = Number($parent.data('level')) || 0,
                parentProductID = $("[data-id=" + parentBomID + "]").data('product_id') || -1;
            return this._rpc({
                model: 'report.replenishment_planning_report',
                method: 'get_child_bom',
                args: [
                    warehouse_id,
                    parentProductID,
                    activeID,
                    productID,
                    parseFloat(qty),
                    lineID,
                    level,
                    bom_ids,
                    parentBomID,
                    is_root
                ],
                context: self.given_context
            })
                .then(function (result) {
                    let $parent = $(ev.currentTarget).closest('tr');
                    self._removeLines($(ev.currentTarget).closest('tr'));
                    let $requestedQty = $parent.find('.requested_quantity'),
                        requestedQty = self._convertTextFieldToNumber($requestedQty),
                        precision_rounding = $parent.data('precision_rounding'),
                        precision_digits = $requestedQty.data('precision'),
                        $result = $(result)
                    ;

                    $parent.replaceWith($result);

                    $parent = $($result[0]);

                    let $bomUnfoldable = $parent.find('.o_mrp_bom_unfoldable');
                    $bomUnfoldable.click();

                    $requestedQty = $parent.find('.requested_quantity');
                    $requestedQty[0].textContent = self._formatNumber(requestedQty, precision_digits, precision_rounding);
                    $requestedQty[0].value = self._formatNumber(requestedQty, precision_digits, precision_rounding);
                    $requestedQty.change();

                    let productIDSet = new Set();
                    $result.each(function () {
                        let $currentElement = $(this),
                            currentElementProductID = $currentElement.data('product_id') || 0;

                        productIDSet.add(currentElementProductID);
                    });

                    let productIDArr = Array.from(productIDSet);
                    productIDArr.forEach(productID => {
                        self._computeLackingQuantity(productID);
                    });

                    _.each($parent.find('.include-button:not(.hide-background)'), function (k) {
                        $(k).click();
                    });
                    let $currentElement = $parent,
                        parentIDStack = [$currentElement.data('id')],
                        currentElementID;

                    while ($currentElement.next().length && parentIDStack.length) {
                        $currentElement = $currentElement.next();
                        currentElementID = $currentElement.data('id') || 0;

                        let parentID, curElementParentID = $currentElement.data('parent_id');
                        while (parentIDStack.length) {
                            parentID = parentIDStack.pop();

                            if (curElementParentID == parentID) {
                                _.each($currentElement.find('.include-button:not(.hide-background)'), function (k) {
                                    $(k).click();
                                });

                                parentIDStack.push(parentID);
                                parentIDStack.push(currentElementID)
                                break;
                            }
                        }
                    }

                    self._reCalculateRequestedQty();
                });
        },

        _onChangePOPercentage: function (ev) {
            this._computeMOPOQty(ev);
            // this._computeEDA(ev);
        },

        _onChangeOrderQty: function (ev) {
            this._computeMOPOQty(ev);
            // this._computeEDA(ev);
        },

        _onChangePOQty: function (ev) {
            let $currentTarget = $(ev.currentTarget),
                $parent = $currentTarget.closest('tr'),
                $poQty = $parent.find('.po_qty'),
                $openPO = $parent.find('.open_po'),
                poQty = this._convertTextFieldToNumber($poQty),
                inheritOpenPO = this._getOpenPOQty($parent),
                openPO = this._convertTextFieldToNumber($openPO),
                requestedPOQty = this._convertTextToNumber($poQty.data('po_qty')),
                precision_rounding = $parent.data('precision_rounding'),
                openPOValue = inheritOpenPO ? inheritOpenPO : openPO
            ;
            $openPO[0].textContent = this._formatNumber(openPOValue,
                $openPO.data('precision'), precision_rounding);
            if (openPOValue < requestedPOQty) {
                $poQty[0].textContent = this._formatNumber(Math.max(requestedPOQty - openPOValue),
                    $poQty.data('precision'), precision_rounding);
            }
            if (poQty > 0) {
                $poQty.addClass('warning-sale');
                $poQty.removeClass('enough-inventory');
            } else {
                $poQty.addClass('enough-inventory');
                $poQty.removeClass('warning-sale');
            }

            this._updateOpenPOQty($parent);
        },

        _onChangeMOQty: function (ev) {
            let $currentTarget = $(ev.currentTarget),
                $parent = $currentTarget.closest('tr'),
                $moQty = $parent.find('.mo_qty'),
                $openMO = $parent.find('.open_mo'),

                moQty = this._convertTextFieldToNumber($moQty),
                inheritOpenMO = this._getOpenMOQty($parent),
                openMO = this._convertTextFieldToNumber($openMO),
                requestedMOQty = this._convertTextToNumber($moQty.data('mo_qty')),
                precision_rounding = $parent.data('precision_rounding'),
                openMOValue = inheritOpenMO ? inheritOpenMO : openMO
            ;
            $openMO[0].textContent = this._formatNumber(openMOValue,
                $openMO.data('precision'), precision_rounding);
            if (openMOValue < requestedMOQty) {
                $moQty[0].textContent = this._formatNumber(Math.max(requestedMOQty - openMOValue),
                    $moQty.data('precision'), precision_rounding);
            }
            if (moQty > 0) {
                $moQty.addClass('warning-manufacture');
                $moQty.removeClass('enough-inventory');
            } else {
                $moQty.addClass('enough-inventory');
                $moQty.removeClass('warning-manufacture');
            }
            this._updateOpenMOQty($parent);
        },

        /**
         * Change some related fields in the row when the requested quantity change:
         *  - Available Quantity
         *  - Order Quantity
         * And Trigger
         *  - update available quantity
         *
         * @private
         * @param {OdooEvent} ev
         */

        _computeLackingQuantity: function (productID) {

            let parentIDArr = [],
                self = this,
                lackingQty = 0,
                curTotalLackingQty = 0;

            $("[data-product_id=" + productID + "]:not([data-parent_id=-1])").each(function () {
                let $currentElement = $(this),
                    $currentLackingQty = $currentElement.find('.lacking_quantity');

                let parent_productID = $("[data-id=" + $currentElement.data('parent_id') + "]").data("product_id");

                lackingQty = 0;
                if (parentIDArr.indexOf(parent_productID) < 0) {
                    parentIDArr.push(parent_productID);

                    lackingQty = parseFloat($currentElement.data('lacking_quantity') || 0);
                    curTotalLackingQty += lackingQty;
                }

                let precision = $currentElement.data('precision') || 2,
                    precisionRounding = $currentElement.data('precision_rounding') || 1.0,
                    $exInBtn = $currentElement.find('.ex-in-button');
                $currentElement.data('calculated_lacking_qty', lackingQty);
                $currentLackingQty[0].textContent = self._formatNumber(lackingQty, precision, precisionRounding);

                if (lackingQty <= 0) {
                    $exInBtn.addClass("hide-background");
                } else {
                    $exInBtn.removeClass("hide-background");
                }
            });

            $("[data-product_id=" + productID + "][data-parent_id=-1]").each(function () {
                let $currentElement = $(this),
                    $currentLackingQty = $currentElement.find('.lacking_quantity');

                let totalLackingQty = parseFloat($currentElement.data('total_lacking_quantity') || 0);
                lackingQty = totalLackingQty - curTotalLackingQty;

                let precision = $currentElement.data('precision') || 2,
                    precisionRounding = $currentElement.data('precision_rounding') || 1.0,
                    $exInBtn = $currentElement.find('.ex-in-button');
                $currentElement.data('calculated_lacking_qty', lackingQty);
                $currentLackingQty[0].textContent = self._formatNumber(lackingQty, precision, precisionRounding);

                if (lackingQty <= 0) {
                    $exInBtn.addClass("hide-background");
                } else {
                    $exInBtn.removeClass("hide-background");
                }

            });

        },

        _onChangeRequestedQuantity: function (ev) {
            ev.preventDefault();
            let $currentTarget = $(ev.currentTarget),
                $parent = $currentTarget.closest('tr'),
                inheritAvailableQty = this._getAvailableQty($parent),
                $availableQty = $parent.find('.forecasted_quantity'),
                $requestedQty = $parent.find('.requested_quantity'),
                $orderQty = $parent.find('.order_qty'),
                availableQty = this._convertTextFieldToNumber($availableQty),
                requestedQty = this._convertTextFieldToNumber($requestedQty),
                precision_rounding = $parent.data('precision_rounding'),

                $exInBtn = $parent.find('.ex-in-button'),
                lackingQty = $parent.data('calculated_lacking_qty') || 0;

            $availableQty[0].textContent = this._formatNumber(inheritAvailableQty ? inheritAvailableQty : availableQty,
                $availableQty.data('precision'), precision_rounding);

            if (!$exInBtn.hasClass('include-button') && requestedQty < lackingQty) {
                requestedQty = lackingQty;
            }
            $requestedQty[0].value = this._formatNumber(requestedQty ? requestedQty : 0,
                $requestedQty.data('precision'), precision_rounding);

            let orderQty = availableQty >= requestedQty ? 0 : Math.abs(requestedQty - availableQty);
            $orderQty[0].textContent = this._formatNumber(orderQty, $orderQty.data('precision'), precision_rounding);

            // call _onChangeOrderQty
            $orderQty.change();

            this._updateAvailableQty($parent);
        },

        _getAvailableQty: function ($current) {
            let availableQty = null,
                productId = $current.data('product_id'),
                originalQty = $current.data('qty_available'),
                currentLine = $current[0],
                updated = false;
            while (currentLine.previousElementSibling) {
                currentLine = currentLine.previousElementSibling;
                let $currentLine = $(currentLine),
                    curProductId = $currentLine.data('product_id');
                if (curProductId === productId) {
                    let $forecastedQuantity = $currentLine.find('.forecasted_quantity'),
                        forecastedQuantity = this._convertTextFieldToNumber($forecastedQuantity),
                        $requestedQuantity = $currentLine.find('.requested_quantity'),
                        requestedQuantity = this._convertTextFieldToNumber($requestedQuantity);
                    availableQty = Math.max(forecastedQuantity - requestedQuantity, 0);
                    updated = true;
                    break;

                }
            }
            if (updated === false) {
                availableQty = this._convertTextToNumber(String(originalQty));
            }
            return availableQty;
        },

        _getOpenMOQty: function ($current) {
            let openMOQty = null,
                productId = $current.data('product_id'),
                originalQty = $current.data('open_mo'),
                currentLine = $current[0],
                updated = false;
            while (currentLine.previousElementSibling) {
                currentLine = currentLine.previousElementSibling;
                let $currentLine = $(currentLine),
                    curProductId = $currentLine.data('product_id');
                if (curProductId === productId) {
                    let $openMOQty = $currentLine.find('.open_mo'),
                        preOpenMOQty = this._convertTextFieldToNumber($openMOQty),
                        $moQty = $currentLine.find('.mo_qty'),
                        moQty = this._convertTextToNumber($moQty.data('mo_qty'));
                    openMOQty = Math.max(preOpenMOQty - moQty, 0);
                    updated = true;
                    break;

                }
            }
            if (updated === false) {
                openMOQty = this._convertTextToNumber(originalQty);
            }
            return openMOQty;
        },

        _getOpenPOQty: function ($current) {
            let openPOQty = null,
                productId = $current.data('product_id'),
                originalQty = $current.data('open_po'),
                currentLine = $current[0],
                updated = false;
            while (currentLine.previousElementSibling) {
                currentLine = currentLine.previousElementSibling;
                let $currentLine = $(currentLine),
                    curProductId = $currentLine.data('product_id');
                if (curProductId === productId) {
                    let $openPOQty = $currentLine.find('.open_po'),
                        preOpenPOQty = this._convertTextFieldToNumber($openPOQty),
                        $poQty = $currentLine.find('.po_qty'),
                        poQty = this._convertTextToNumber($poQty.data('po_qty'));
                    openPOQty = Math.max(preOpenPOQty - poQty, 0);
                    updated = true;
                    break;

                }
            }
            if (updated === false) {
                openPOQty = this._convertTextToNumber(originalQty);
            }
            return openPOQty;
        },

        _getParentProduct: function ($current) {
            let productId = $current.data('product_id'),
                currentLine = $current[0],
                currLevel = $current.data('level');
            if (currLevel > 0) {
                while (currentLine.previousElementSibling) {
                    currentLine = currentLine.previousElementSibling;
                    let $currentLine = $(currentLine),
                        lineLevel = $currentLine.data('level') || 0;
                    if (lineLevel < currLevel - 1) {
                        this.do_warn(_t("Warning"), _t('Can not find the parent for product ' + productId));
                        break
                    }
                    if (lineLevel === currLevel - 1) {
                        return $currentLine
                    }
                }
                this.do_warn(_t("Warning"), _t('Can not find the parent for product ' + productId));
            }
            return false
        },

        _updateAvailableQty: function ($current) {
            let productId = $current.data('product_id'),
                $forecastedQuantity = $current.find('.forecasted_quantity'),
                forecastedQuantity = this._convertTextFieldToNumber($forecastedQuantity),
                $requestedQuantity = $current.find('.requested_quantity'),
                $parent = $requestedQuantity.closest('tr'),
                requestedQuantity = this._convertTextFieldToNumber($requestedQuantity),
                currentLine = $current[0],
                precision_rounding = $parent.data('precision_rounding')
            ;
            while (currentLine.nextElementSibling) {
                currentLine = currentLine.nextElementSibling;
                let $currentLine = $(currentLine),
                    curProductId = $currentLine.data('product_id');
                if (curProductId === productId) {
                    let $curForecastedQty = $currentLine.find('.forecasted_quantity'),
                        foreQtyPrecision = $curForecastedQty.data('precision'),
                        $curRequestedQuantity = $currentLine.find('.requested_quantity');
                    forecastedQuantity = Math.max(forecastedQuantity - requestedQuantity, 0);

                    $curForecastedQty[0].textContent = this._formatNumber(forecastedQuantity, foreQtyPrecision, precision_rounding);
                    $curRequestedQuantity.change();
                    break;

                }
            }
        },
        /**
         * @desc: Function update the open MO quantity and MO quantity of the nearest line below,
         * that have same product
         */
        _updateOpenMOQty: function ($current) {
            let productId = $current.data('product_id'),
                $openMO = $current.find('.open_mo'),
                openMO = this._convertTextFieldToNumber($openMO),
                $moQty = $current.find('.mo_qty'),
                moQty = this._convertTextToNumber($moQty.data('mo_qty')),
                currentLine = $current[0],
                precision_rounding = $current.data('precision_rounding')
            ;
            while (currentLine.nextElementSibling) {
                currentLine = currentLine.nextElementSibling;
                let $currentLine = $(currentLine),
                    curProductId = $currentLine.data('product_id');
                if (curProductId === productId) {
                    let $curOpenMO = $currentLine.find('.open_mo'),
                        curOpenMO = this._convertTextFieldToNumber($curOpenMO),
                        openMOPrecision = $curOpenMO.data('precision'),
                        $curMOQty = $currentLine.find('.mo_qty'),
                        curMOQtyNeed = this._convertTextToNumber($curMOQty.data('mo_qty'));
                    openMO = Math.max(openMO - moQty, 0);
                    if (curOpenMO !== openMO) {
                        let curMOQty = Math.max(curMOQtyNeed - openMO, 0);

                        $curOpenMO[0].textContent = this._formatNumber(openMO, openMOPrecision, precision_rounding);
                        $curMOQty[0].textContent = this._formatNumber(curMOQty, openMOPrecision, precision_rounding);
                        $curMOQty.change();
                    }

                    break;
                }
            }
        },

        /**
         * @desc: Function update the open PO quantity and PO quantity of the nearest line below,
         * that have same alternative product
         */
        _updateOpenPOQty: function ($current) {
            let productId = $current.data('product_id'),
                $openPO = $current.find('.open_po'),
                openPO = this._convertTextFieldToNumber($openPO),
                $poQty = $current.find('.po_qty'),
                poQty = this._convertTextToNumber($poQty.data('po_qty')),
                currentLine = $current[0],
                precision_rounding = $current.data('precision_rounding')
            ;
            while (currentLine.nextElementSibling) {
                currentLine = currentLine.nextElementSibling;
                let $currentLine = $(currentLine),
                    curProductId = $currentLine.data('product_id');
                if (curProductId === productId) {
                    let $curOpenPO = $currentLine.find('.open_po'),
                        curOpenPO = this._convertTextFieldToNumber($curOpenPO),
                        openPOPrecision = $curOpenPO.data('precision'),
                        $curPOQty = $currentLine.find('.po_qty'),
                        curPOQtyNeed = this._convertTextToNumber($curPOQty.data('po_qty'));
                    openPO = Math.max(openPO - poQty, 0);
                    if (curOpenPO !== openPO) {
                        let curPOQty = Math.max(curPOQtyNeed - openPO, 0);

                        $curOpenPO[0].textContent = this._formatNumber(openPO, openPOPrecision, precision_rounding);
                        $curPOQty[0].textContent = this._formatNumber(curPOQty, openPOPrecision, precision_rounding);
                        $curPOQty.change();
                    }

                    break;
                }
            }
        },

        _onChangeQty: function (ev) {
            var qty = $(ev.currentTarget).val().trim();
            if (qty) {
                this.given_context.searchQty = parseFloat(qty);
                this._reload();
            }
        },

        _changeChild: function ($trParent, $parentItem, id, requestedQty) {
            let parentQty = Number($trParent[0].dataset.bom_qty),
                requestedQtyNum = this._convertTextToNumber(requestedQty),
                lineLevel = $trParent.data('level') || 0,
                currentLine = $trParent[0];

            while (currentLine.nextElementSibling) {
                currentLine = currentLine.nextElementSibling;
                let $currentLine = $(currentLine),
                    parent_id = $currentLine.data('parent_id'),
                    currentLevel = $currentLine.data('level') || 0;
                if (currentLevel <= lineLevel) {
                    break;
                }
                if (currentLevel === lineLevel + 1 && parent_id === id) {
                    let line_qty = Number(currentLine.dataset.line_qty),
                        $requestedQuantity = $currentLine.find('.requested_quantity'),
                        requestedQty = requestedQtyNum / parentQty * line_qty,
                        precision_rounding = $currentLine.data('precision_rounding');

                    let $exInBtn = $currentLine.find('.ex-in-button'),
                        lackingQty = parseFloat($currentLine.data('calculated_lacking_qty') || 0);

                    if (!$exInBtn.hasClass('include-button')) {
                        requestedQty += lackingQty;
                    }

                    requestedQty = Math.ceil(requestedQty);

                    $requestedQuantity[0].textContent = this._formatNumber(requestedQty, $requestedQuantity.data('precision'), precision_rounding);
                    $requestedQuantity.change()
                }
            }
        },

        _computeMOPOQty: function (ev) {
            ev.preventDefault();
            let $currentTarget = $(ev.currentTarget),
                $trParent = $currentTarget.closest('tr'),
                $root = $currentTarget.closest('tbody'),
                self = this,
                qtyPercTxt = $trParent.find('.po_perc')[0].textContent ||
                    $trParent.find('.po_perc')[0].value,
                qtyPerc = this._convertTextToNumber(qtyPercTxt);
            if (/[0-9.]+/.test(qtyPercTxt) && (qtyPerc <= 100 && qtyPerc >= 0)) {
                let orderQtyTxt = $trParent.find('.order_qty')[0].textContent ||
                    $trParent.find('.order_qty')[0].value;
                let orderQty = this._convertTextToNumber(orderQtyTxt);
                if (!/[0-9.]+/.test(orderQtyTxt)) {
                    return;
                }
                let $poQty = $trParent.find('.po_qty'),
                    $moQty = $trParent.find('.mo_qty'),
                    $poQtyTotal = $trParent.find('.po_qty_total'),
                    $moQtyTotal = $trParent.find('.mo_qty_total'),
                    precision_rounding = $trParent.data('precision_rounding'),
                    open_po_qty = self._convertTextFieldToNumber($trParent.find('.open_po')),
                    open_mo_qty = self._convertTextFieldToNumber($trParent.find('.open_mo')),
                    need_to_buy = Math.ceil(orderQty * Math.min(100, qtyPerc) / 100),
                    need_to_manufacture = Math.max(orderQty - need_to_buy, 0),
                    today = new Date(),
                    id = $trParent.data('id');

                let mo_qty_val = Math.ceil(Math.max(need_to_manufacture - open_mo_qty, 0)),
                    po_qty_val = Math.ceil(Math.max(need_to_buy - open_po_qty, 0));

                $poQty.data('po_qty', need_to_buy);
                $moQty.data('mo_qty', need_to_manufacture);
                $poQty[0].textContent = this._formatNumber(po_qty_val, $moQty.data('precision'), precision_rounding);
                $moQty[0].textContent = this._formatNumber(mo_qty_val, $poQty.data('precision'), precision_rounding);
                $poQty.change();
                $moQty.change();

                $poQtyTotal[0].textContent = this._formatNumber(need_to_buy, $moQty.data('precision'), precision_rounding);
                $moQtyTotal[0].textContent = this._formatNumber(need_to_manufacture, $poQty.data('precision'), precision_rounding);

                let parentId = $trParent.data('id');
                if (parentId !== undefined) {
                    self._changeChild($trParent, $root, parentId, mo_qty_val);
                }
            } else {
                self.do_warn(_t("Warning"), _t('Please input the Number in range 0-100%.'));
            }
        },

        _onClickOption: function (ev) {
            var option_value = $(ev.currentTarget).data('filter');
            var self = this;
            _.each(this.$searchView.find('.js_bom_bool_filter'), function (k) {
                if (k.dataset.filter == option_value) {
                    $(k).addClass('selected');
                    self.given_context.option_value = option_value;
                } else {
                    $(k).removeClass('selected');
                }
            });
            this._reload();
        },

        _onClickUnfold: function (ev) {
            if (ev.currentTarget.id == 'fold-all-button') {
                this._unFoldAll();
                $(ev.currentTarget).toggleClass('o_mrp_bom_foldable o_mrp_bom_unfoldable fa-expand fa-compress');
            } else {
                this._hideLines($(ev.currentTarget).closest('tr'), false);
                $(ev.currentTarget).toggleClass('o_mrp_bom_foldable o_mrp_bom_unfoldable fa-caret-right fa-caret-down');
            }

            this._foldAllButtonConfig()
        },

        _onClickFold: function (ev) {
            if (ev.currentTarget.id == 'fold-all-button') {
                this._foldAll();
                $(ev.currentTarget).toggleClass('o_mrp_bom_foldable o_mrp_bom_unfoldable fa-expand fa-compress');
            } else {
                this._hideLines($(ev.currentTarget).closest('tr'), true);
                $(ev.currentTarget).toggleClass('o_mrp_bom_foldable o_mrp_bom_unfoldable fa-caret-right fa-caret-down');
            }

            this._foldAllButtonConfig()
        },

        _foldAllButtonConfig: function () {
            let self = this,
                foldableItems = self.$el.find("td > .o_mrp_bom_foldable").length,
                unfoldableItem = self.$el.find("td > .o_mrp_bom_unfoldable").length,
                $foldAllButton = $("#fold-all-button");

            if ((foldableItems == 0) && (unfoldableItem == 0)) {
                $foldAllButton.addClass('hide');
            } else {
                $foldAllButton.removeClass('hide');
                if (foldableItems == 0) {
                    if ($foldAllButton.hasClass('o_mrp_bom_foldable')) {
                        $foldAllButton.toggleClass('o_mrp_bom_foldable o_mrp_bom_unfoldable fa-expand fa-compress');
                    }
                } else {
                    if ($foldAllButton.hasClass('o_mrp_bom_unfoldable')) {
                        $foldAllButton.toggleClass('o_mrp_bom_foldable o_mrp_bom_unfoldable fa-expand fa-compress');
                    }
                }
            }
        },

        _onClickAutoReplenish: function (ev) {
            let self = this,
                $elements = self.$el.find('.o_mrp_bom_report_page tbody tr'),
                dict = [];

            // get Purchased Qty and Manufactured Qty from UI
            _.each($elements, function (elem) {
                let $elem = $(elem),
                    dataset = elem.dataset,
                    // get purchased and manufactured qty from the view
                    po_qty = self._convertTextFieldToNumber($elem.find('.po_qty')),
                    mo_qty = self._convertTextFieldToNumber($elem.find('.mo_qty')),
                    requested_qty = self._convertTextFieldToNumber($elem.find('.requested_quantity')),
                    po_percentage = self._convertTextFieldToNumber($elem.find('.po_perc'));
                dict.push({
                    'bom_id': dataset.id || null,
                    'line': dataset.line,
                    'parent_id': dataset.parent_id,
                    'product_id': dataset.product_id,
                    'level': dataset.level || 1,
                    'po_qty': po_qty,
                    'mo_qty': mo_qty,
                    'requested_qty': requested_qty,
                    'po_percentage': po_percentage,
                    'warehouse_id': dataset.warehouse_id
                });
            });
            let create_po = true;
            let create_mo = true;
            let warehouse_id = self.given_context.warehouse_id;
            self._rpc({
                model: 'replenishment.history',
                method: 'auto_replenishment',
                args: [dict, warehouse_id, create_po, create_mo],
            }).then(function (result) {
                return self.do_action(result);
            }).guardedCatch(framework.unblockUI);

        },

        _onClickCreatePurchaseOrders: function (ev) {
            let self = this,
                $elements = self.$el.find('.o_mrp_bom_report_page tbody tr'),
                dict = [];
            _.each($elements, function (elem) {
                let $elem = $(elem),
                    dataset = elem.dataset,
                    // get purchased and manufactured qty from the view
                    po_qty = self._convertTextFieldToNumber($elem.find('.po_qty')),
                    mo_qty = self._convertTextFieldToNumber($elem.find('.mo_qty')),
                    requested_qty = self._convertTextFieldToNumber($elem.find('.requested_quantity')),
                    po_percentage = self._convertTextFieldToNumber($elem.find('.po_perc'));
                dict.push({
                    'bom_id': dataset.id || null,
                    'line': dataset.line,
                    'parent_id': dataset.parent_id,
                    'product_id': dataset.product_id,
                    'level': dataset.level || 1,
                    'po_qty': po_qty,
                    'mo_qty': mo_qty,
                    'requested_qty': requested_qty,
                    'po_percentage': po_percentage,
                    'warehouse_id': dataset.warehouse_id
                });
            });
            let create_po = true;
            let create_mo = false;
            let warehouse_id = self.given_context.warehouse_id;
            self._rpc({
                model: 'replenishment.history',
                method: 'auto_replenishment',
                args: [dict, warehouse_id, create_po, create_mo],
            }).then(function (result) {
                return self.do_action(result);
            }).guardedCatch(framework.unblockUI);
        },

        _onClickManufacturingOrders: function (ev) {
            let self = this,
                $elements = self.$el.find('.o_mrp_bom_report_page tbody tr'),
                dict = [];
            _.each($elements, function (elem) {
                let $elem = $(elem),
                    dataset = elem.dataset,
                    // get purchased and manufactured qty from the view
                    po_qty = self._convertTextFieldToNumber($elem.find('.po_qty')),
                    mo_qty = self._convertTextFieldToNumber($elem.find('.mo_qty')),
                    requested_qty = self._convertTextFieldToNumber($elem.find('.requested_quantity')),
                    po_percentage = self._convertTextFieldToNumber($elem.find('.po_perc'));
                dict.push({
                    'bom_id': dataset.id || null,
                    'line': dataset.line,
                    'parent_id': dataset.parent_id,
                    'product_id': dataset.product_id,
                    'level': dataset.level || 1,
                    'po_qty': po_qty,
                    'mo_qty': mo_qty,
                    'requested_qty': requested_qty,
                    'po_percentage': po_percentage,
                });
            });
            let create_po = false;
            let create_mo = true;
            let warehouse_id = self.given_context.warehouse_id;
            self._rpc({
                model: 'replenishment.history',
                method: 'auto_replenishment',
                args: [dict, warehouse_id, create_po, create_mo],
            }).then(function (result) {
                return self.do_action(result);
            }).guardedCatch(framework.unblockUI);
        },

        _onClickAction: function (ev) {
            ev.preventDefault();
            return this.do_action({
                type: 'ir.actions.act_window',
                res_model: $(ev.currentTarget).data('model'),
                res_id: $(ev.currentTarget).data('res-id'),
                views: [[false, 'form']],
                target: 'current'
            });
        },
        _onClickOpenDetailTransaction: function (ev) {
            ev.preventDefault();
            var ids = $(ev.currentTarget).data('res-ids');
            return this.do_action({
                name: _t('Detail Transactions'),
                type: 'ir.actions.act_window',
                res_model: $(ev.currentTarget).data('model'),
                domain: [['id', 'in', ids]],
                views: [[false, 'list']],
                view_mode: 'list',
                target: 'current',
            });
        },

        _onClickExInButton: function (ev) {
            ev.preventDefault();

            let self = this,
                $exInBtn = $(ev.currentTarget),
                $parentElement = $($exInBtn.closest('tr')),
                $requestedQty = $parentElement.find('.requested_quantity'),
                parentProductID = $parentElement.data('parent_id'),
                requestedQty = parseFloat(self._convertTextFieldToNumber($requestedQty)),
                lacking_quantity = parseFloat($parentElement.data('calculated_lacking_qty') || 0);

            if ($exInBtn.hasClass("hide-background")) {
                return;
            }

            let $parent_product = $("tr[data-id=" + parentProductID + "]"),
                precision = $parentElement.data('precision'),
                precision_rounding = $parentElement.data('precision_rounding');

            if (parentProductID == -1) {
                if ($exInBtn.hasClass('include-button')) {
                    $exInBtn.removeClass('include-button');
                    requestedQty += lacking_quantity;
                } else {
                    $exInBtn.addClass('include-button');
                    requestedQty -= lacking_quantity;
                    requestedQty = requestedQty < 0 ? 0 : requestedQty;
                }
                self._setTextFieldValue($requestedQty, requestedQty, precision, precision_rounding);
                $requestedQty.change();
                return;
            }

            if ($exInBtn.hasClass('include-button')) {
                $exInBtn.removeClass('include-button');
            } else {
                $exInBtn.addClass('include-button');
            }

            $parent_product.find(".requested_quantity").change();

        },

        _hideLines: function ($el, hide) {
            var self = this;
            var activeID = $el.data('id');

            let $currentElement = $el,
                parentIDStack = [$currentElement.data('id')],
                currentElementID;

            while ($currentElement.next().length && parentIDStack.length) {
                $currentElement = $currentElement.next();
                currentElementID = $currentElement.data('id') || 0;

                let parentID, curElementParentID = $currentElement.data('parent_id');
                while (parentIDStack.length) {
                    parentID = parentIDStack.pop();

                    if (curElementParentID == parentID) {
                        if (hide) {
                            $currentElement.addClass('hide');

                            let $foldableBtn = $currentElement.find('.o_mrp_bom_foldable');
                            if ($foldableBtn.length) {
                                $foldableBtn.toggleClass('o_mrp_bom_foldable o_mrp_bom_unfoldable fa-caret-right fa-caret-down');
                            }
                        } else {
                            if (!parentIDStack.length) {
                                $currentElement.removeClass('hide');

                                let $foldableBtn = $currentElement.find('.o_mrp_bom_foldable');
                                if ($foldableBtn.length) {
                                    $foldableBtn.toggleClass('o_mrp_bom_foldable o_mrp_bom_unfoldable fa-caret-right fa-caret-down');
                                }
                            }
                        }
                        parentIDStack.push(parentID);
                        parentIDStack.push(currentElementID)
                        break;
                    }
                }
            }
        },

        _removeLines: function ($el) {
            var self = this;
            var activeID = $el.data('id');

            let $currentElement = $el,
                parentIDStack = [$currentElement.data('id')],
                deleteElementArr = [],
                currentElementID;

            while ($currentElement.next().length && parentIDStack.length) {
                $currentElement = $currentElement.next();
                currentElementID = $currentElement.data('id') || 0;

                let parentID, curElementParentID = $currentElement.data('parent_id');
                while (parentIDStack.length) {
                    parentID = parentIDStack.pop();

                    if (curElementParentID == parentID) {
                        deleteElementArr.push($currentElement);

                        parentIDStack.push(parentID);
                        parentIDStack.push(currentElementID)
                        break;
                    }
                }
            }

            deleteElementArr.forEach(element => {
                element.remove();
            });
        },

        _unFoldAll: function () {
            $(".text-o_mrp_bom_report_line").each(function () {
                let $currentElement = $(this);

                $currentElement.removeClass('hide');

                let $unFoldableBtn = $currentElement.find('.o_mrp_bom_unfoldable');
                if ($unFoldableBtn.length) {
                    $unFoldableBtn.toggleClass('o_mrp_bom_foldable o_mrp_bom_unfoldable fa-caret-right fa-caret-down');
                }
            });
        },

        _foldAll: function () {
            $(".text-o_mrp_bom_report_line").each(function () {
                let $currentElement = $(this);

                if ($currentElement.data('parent_id') != -1) {
                    $currentElement.addClass('hide');
                }

                let $unFoldableBtn = $currentElement.find('.o_mrp_bom_foldable');
                if ($unFoldableBtn.length) {
                    $unFoldableBtn.toggleClass('o_mrp_bom_foldable o_mrp_bom_unfoldable fa-caret-right fa-caret-down');
                }
            });
        },

        _convertTextFieldToNumber: function (item) {
            let value;
            if (item[0] instanceof HTMLInputElement) {
                value = item[0].value;
            } else {
                value = item[0].textContent;
            }
            return this._convertTextToNumber(value)
        },

        _setTextFieldValue: function (item, value, precision, precision_rounding) {
            if (item[0] instanceof HTMLInputElement) {
                item[0].value = this._formatNumber(value, precision, precision_rounding);
            } else {
                item[0].textContent = this._formatNumber(value, precision, precision_rounding);
            }
        },

        _convertTextToNumber: function (textValue) {
            let number_value = NaN;
            if (typeof textValue === 'number') {
                number_value = textValue;
            } else {
                if (textValue === undefined) {
                    number_value = 0;
                } else {
                    number_value = Number(textValue.replaceAll(/\s/g, '').replaceAll(/,/g, ''));
                }
            }
            return number_value;
        },

        _formatNumber: function (val, precision, precision_rounding) {
            return round_pr(val, precision_rounding).toFixed(precision)
                .replace(/(\d)(?=(\d{3})+(\.))/g, '$1,');
        }
    });

    core.action_registry.add('replenishment_planning_report', ReplenishmentPlanReport);
    return ReplenishmentPlanReport;

});
