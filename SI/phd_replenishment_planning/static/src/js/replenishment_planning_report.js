odoo.define('phd_replenishment_planning_report.replenishment_planning_report', function (require) {
    'use strict';

    var ReplenishmentPlanReport = require('replenishment_planning_report.replenishment_planning_report');
    var Widget = require('web.Widget');
    var StandaloneFieldManagerMixin = require('web.StandaloneFieldManagerMixin');
    const {FieldMany2One} = require("web.relational_fields");
    var core = require('web.core');
    var framework = require('web.framework');
    var _t = core._t;


    var CustomMany2One = Widget.extend(StandaloneFieldManagerMixin, {
        init: function (parent, modelID, field, extraParams) {
            this._super.apply(this, arguments);
            StandaloneFieldManagerMixin.init.call(this);
            this.widget = undefined;
            this.value = modelID;
            this.field = field;
            this.extraParams = extraParams;
        },
        willStart: async function () {
            await this._super.apply(this, arguments);
            await this._createM2OWidget(this.field, this.value, this.extraParams);
        },
        start: function () {
            const $content = $(`<div></div>`);
            this.$content = $content;
            this.$el.append($content);
            this.widget.appendTo($content).then(res => {
                    if (this.extraParams.isRequired === true) {
                        this.$el.addClass('o_required_modifier')
                    }
                }
            );
            return this._super.apply(this, arguments);
        },
        _confirmChange: async function () {
            const result = await StandaloneFieldManagerMixin._confirmChange.apply(this, arguments);
            this.trigger_up(`${this.extraParams.key}_selected`, {value: this.widget.value.res_id});
            this.widget.$input.blur();
            return result;
        },
        _dialogRequireField: function () {
            this.widget.$input.addClass('o_field_invalid')
        },
        _createM2OWidget: async function (fieldName, modelID, extraParams) {
            let recordCreatedData = {
                name: fieldName,
                relation: modelID,
                type: "many2one",
                domain: extraParams.domain
            }
            if (extraParams.default_id !== undefined) {
                recordCreatedData.value = [extraParams.default_id, extraParams.default];
            }
            const recordID = await this.model.makeRecord(modelID, [
                recordCreatedData,
            ]);
            let record_data = this.model.get(recordID);
            this.widget = new FieldMany2One(this, fieldName,
                record_data, {
                    mode: "edit",
                    attrs: {
                        options: {
                            no_quick_create: true,
                            no_create: true,
                            can_write: false,
                        }
                    },
                },
                extraParams.advance
            );
            this._registerWidget(recordID, fieldName, this.widget);
        },
    });
    var ReplenishmentPlanReport = ReplenishmentPlanReport.include({
        custom_events: _.extend({}, ReplenishmentPlanReport.prototype.custom_events, {
            vendor_selected: '_onVendorChanged',
            bom_selected: '_onBOMChanged',
        }),

        events: _.extend({}, ReplenishmentPlanReport.prototype.events, {
            'change .estimated_cost': '_onChangeEstimatedCost',
        }),

        renderSearch: function () {
            return true
        },
        _refreshQtyFormat: function () {
            let self = this;
            _.each(this.$el.find('.free_qty'), function (k) {
                let precision = parseInt(k.getAttribute('data-precision')) || 2,
                    precisionRounding = parseInt(k.getAttribute('data-precision_rounding')) || 1,
                    raw_value = $(k).closest('tr').data('free_qty') || 0;
                k.textContent = self._formatNumber(raw_value, precision, precisionRounding);
            });
        },
        _refreshView: function () {
            this._super.apply(this, arguments);
            if (!this.customEl) {
                this.customEl = {
                    "vendor": {}
                }
            }
            this._refreshComponentView(this.data['raw'])
            this._refreshQtyFormat();
        },

        _refreshComponentView: function (raw) {
            let self = this;
            raw?.forEach(el => {
                self._refreshViewLine(el);
            });
        },
        _refreshViewLine: function (el) {
            if (el) {
                var rootElement = $(`tr[data-key='${el.key}']`);
                if (rootElement.length === 1){
                    if (el.vendor_domain !== false){
                        let M2OVendorFilters = new CustomMany2One(this, 'res.partner', 'name', {
                            domain: el.vendor_domain,
                            parent: rootElement,
                            isRequired: true,
                            key: 'vendor'
                        });
                        M2OVendorFilters.appendTo(rootElement.find('.vendor_m2o'));
                    }
                    if (el.bom_domain !== false){
                        let M2OBOMFilters = new CustomMany2One(this, 'mrp.bom', 'name', {
                            domain: el.bom_domain,
                            parent: rootElement,
                            key: 'bom',
                            default: el.default_bom_name,
                            default_id: el.default_bom_id
                        });
                        M2OBOMFilters.appendTo(rootElement.find('.bom_m2o'));
                    }
                }
            }
        },
        _onVendorChanged: function (evt) {
            let parent = evt.target.$el.parents('tr');
            parent.attr('data-vendor_id', evt.data.value);
            let self = this;
            this._rpc({
                model: 'report.replenishment_planning_report',
                method: 'get_vendor_dependent',
                args: [parseInt(parent.data('product_id')), evt.data.value]
            })
                .then(function (result) {
                    self._updateDependentVendor(parent, result)
                });
        },
        _updateDependentVendor: function (line, result) {
            line.find('.lead_time').text(result['leadTime'])
        },
        _onBOMChanged(evt) {
            let bom_id = ((evt.data.value)?evt.data.value: false);
            evt.target.$el.closest('tr').data('bom_id', bom_id);
            this._onSelectChildBOM(evt);
        },
        _getAutoReplenishmentdata: function (elem) {
            let $elem = $(elem),
                dataset = elem.dataset,
                po_qty = parseFloat($elem.find('.po_qty').text()),
                mo_qty = parseFloat($elem.find('.mo_qty').text()),
                requested_qty = parseFloat($elem.find('.requested_quantity').val()),
                po_percentage = parseFloat($elem.find('.po_perc').val());
            return {
                'bom_id': dataset.id || null,
                'line': dataset.line,
                'parent_id': dataset.parent_id,
                'product_id': dataset.product_id,
                'level': dataset.level || 1,
                'po_qty': po_qty,
                'mo_qty': mo_qty,
                'requested_qty': requested_qty,
                'po_percentage': po_percentage,
                'warehouse_id': dataset.warehouse_id,
                'vendor_id': parseInt(elem.getAttribute('data-vendor_id'))
            };
        },
        _onClickAutoReplenish: function (ev) {
            let requiredList = this.$('.o_required_modifier');
            let invalidList = [];
            for (let element of requiredList) {
                let $element = $(element);
                if (!$element.find('input')?.val()) {
                    invalidList.push($element);
                    $element.addClass('o_field_invalid')
                } else {
                    $element.removeClass('o_field_invalid')
                }
            }
            if (invalidList.length) {
                this._notifyRequiredField(invalidList);
            } else {
                let self = this,
                    $elements = self.$el.find('.o_mrp_bom_report_page tbody tr'),
                    dict = [];
                this.create_mo = false;
                _.each($elements, function (elem) {
                    dict.push(self._getAutoReplenishmentdata(elem));
                });
                let create_mo = (this.create_mo !== undefined) ? this.create_mo : true;
                let create_po = (this.create_po !== undefined) ? this.create_po : true;
                let warehouse_id = self.given_context.warehouse_id;
                self._rpc({
                    model: 'replenishment.history',
                    method: 'auto_replenishment',
                    args: [dict, warehouse_id, create_po, create_mo],
                }).then(function (result) {
                    return self.do_action(result);
                }).guardedCatch(framework.unblockUI);

            }
        },
        _notifyRequiredField: function ($invalidList) {
            let self = this;
            let message = "";
            let ids = Array.from(new Set($invalidList.map(e => parseInt(e.parents('tr').attr('data-product_id')))));
            this._rpc({
                model: 'product.product',
                method: 'read',
                args: [ids, ['display_name']]
            })
                .then(function (result) {
                    for (let res of result) {
                        message += `• ${res.display_name}<br>`
                    }
                    self.do_warn(_t("Missing required field(s) of product(s)"), _t(message));
                });
        },

        //    Override method of ME
        _getBOMData: function (ev) {
            let self = this,
                warehouse_id = self.given_context.warehouse_id,
                $currentTarget = ev.target.$el,
                $parent = $currentTarget.closest('tr'),
                parentBomID = $parent.data('parent_id'),
                activeID = $parent.data('bom_id'),
                productID = $parent.data('product_id'),
                lineID = $parent.data('line'),
                qty = $parent.data('qty'),
                bom_ids = $parent.data('bom_ids'),
                is_root = $parent.data('is_root'),
                level = Number($parent.data('level')) || 0,
                parentProductID = $("[data-id=" + parentBomID + "]").data('product_id') || -1;
            return [
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
            ]
        },
        _onSelectChildBOM: function (ev) {
            let self = this;
            return this._rpc({
                model: 'report.replenishment_planning_report',
                method: 'get_child_bom',
                args: self._getBOMData(ev),
                context: self.given_context
            }).then(function (result) {
                self._renderBOM(result, ev)
                return result
            });
        },
        _renderBOM: function (result, ev) {
            this._renderBOMLines(result.data, ev)
            this._refreshComponentView(result['raw']);
        },
        _renderBOMLines: function (result, ev) {
            let self = this;
            let $parent = ev.target.$el.closest('tr');
            self._removeLines($parent);
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
                    need_to_manufacture = Math.max(orderQty - need_to_buy, 0);
                // today = new Date(),
                // id = $trParent.data('id');

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
                    self._changeChild($trParent, $root, parentId, po_qty_val);
                }
            } else {
                self.do_warn(_t("Warning"), _t('Please input the Number in range 0-100%.'));
            }
        },

        _onChangePOQty: function (ev) {
            let $currentTarget = $(ev.currentTarget),
                $parent = $currentTarget.closest('tr'),
                $poQty = $parent.find('.po_qty'),
                $openPO = $parent.find('.open_po'),
                $estimatedCost = $parent.find('.estimated_cost'),
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
            //Trigger Estimated Cost changed
            $estimatedCost.change();

            this._updateOpenPOQty($parent);
        },

        _onChangeEstimatedCost: function (ev) {
            let $currentTarget = $(ev.currentTarget),
                $parent = $currentTarget.closest('tr'),
                $poQty = $parent.find('.po_qty'),
                $estimatedCost = $parent.find('.estimated_cost'),
                $productCost = $parent.find('.product_cost'),
                poQty = this._convertTextFieldToNumber($poQty),
                productCostValue = this._convertTextFieldToNumber($productCost),
                estimatedCostValue = poQty * productCostValue,
                precision_digits = $estimatedCost.data('precision'),
                currency = $estimatedCost.data('currency')
            ;
            $estimatedCost[0].textContent = estimatedCostValue.toLocaleString("en-US", {
                style: 'currency',
                currency: currency,
                minimumFractionDigits: precision_digits,
                maximumFractionDigits: precision_digits
            });
        },


    });
    return ReplenishmentPlanReport;

});
