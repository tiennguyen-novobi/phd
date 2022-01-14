#coding: utf-8

from odoo import _, api, fields, models
from odoo.addons import decimal_precision as dp
from odoo.exceptions import UserError

NOERROR = _("It is not allowed to change category, location or warehouse in an existing rule. Create a new one instead")


class product_categ_order_point(models.Model):
    """
    The model to configure order points by product category not variants

    To-do:
     * open product rules from category rule
    """
    _name = "product.categ.order.point"
    _description = "Minimum Inventory Rule per Category"
    _rec_name = "category_id"

    @api.model
    def default_get(self, fields):
        """
        Re-write to define defaults for warehouse and location
        """
        res = super(product_categ_order_point, self).default_get(fields)
        warehouse = None
        if 'warehouse_id' not in res and res.get('company_id'):
            warehouse = self.env['stock.warehouse'].search([('company_id', '=', res['company_id'])], limit=1)
        if warehouse:
            res['warehouse_id'] = warehouse.id
            res['location_id'] = warehouse.lot_stock_id.id
        return res

    category_id = fields.Many2one(
        "product.category",
        string="Product Category",
        ondelete='cascade',
        required=True,
    )
    warehouse_id = fields.Many2one(
        'stock.warehouse',
        'Warehouse',
        ondelete="cascade",
        required=True,
    )
    location_id = fields.Many2one(
        'stock.location',
        'Location',
        ondelete="cascade",
        required=True,
    )
    company_id = fields.Many2one(
        'res.company',
        'Company',
        required=True,
        default=lambda self: self.env['res.company']._company_default_get('stock.warehouse.orderpoint'),
    )
    product_min_qty = fields.Float(
        'Minimum Quantity',
        digits=dp.get_precision('Product Unit of Measure'),
        required=True,
    )
    product_max_qty = fields.Float(
        'Maximum Quantity',
        digits=dp.get_precision('Product Unit of Measure'),
        required=True,
    )
    qty_multiple = fields.Float(
        'Qty Multiple',
        digits=dp.get_precision('Product Unit of Measure'),
        default=1,
        required=True,
    )
    group_id = fields.Many2one(
        'procurement.group',
        'Procurement Group',
        copy=False,
    )
    company_id = fields.Many2one(
        'res.company',
        'Company',
        required=True,
        default=lambda self: self.env['res.company']._company_default_get('stock.warehouse.orderpoint'),
    )
    lead_days = fields.Integer(
        'Lead Time',
        default=1,
    )
    lead_type = fields.Selection(
        [('net', 'Day(s) to get the products'), ('supplier', 'Day(s) to purchase')],
        'Lead Type',
        required=True,
        default='supplier',
    )

    _sql_constraints = [
        (
            'category_location_uniq',
            'unique(category_id, location_id)',
            _('The rule should be unique per category and location'),
        )
    ]

    @api.model
    def create(self, values):
        """
        Override to update minimum stock rules by products

        Methods:
         * _update_product_rules
        """
        res = super(product_categ_order_point, self).create(values)
        res._update_product_rules()
        return res

    @api.multi
    def write(self, values):
        """
        Override to update minimum stock rules by products

        Methods:
         * _update_product_rules
        """
        if values.get("category_id") or values.get("location_id") or values.get("warehouse_id"):
            raise UserError(NOERROR)
        res = super(product_categ_order_point, self).write(values)
        self._update_product_rules()
        return res

    @api.multi
    def unlink(self):
        """
        Ovrerride to unlink also minimum stock rules

        Methods:
         * _deactivate_related_rules()
        """
        self._deactivate_related_rules()
        res = super(product_categ_order_point, self).unlink()
        return res

    @api.multi
    def name_get(self):
        """
        Method to define display name
        """
        res = []
        for obj in self:
            title_name = _(u"Rule for the category '{}'' and the location '{}'".format(
                obj.category_id.name, obj.location_id.name)
            )
            res.append((obj.id, title_name))
        return res

    @api.multi
    def _deactivate_related_rules(self):
        """
        The method to mark related product rules as not active
        """
        for rule in self:
            query = """
                UPDATE stock_warehouse_orderpoint
                SET active = FALSE
                WHERE category_rule_id = %(category_rule_id)s
            """
            self._cr.execute(query, {"category_rule_id": rule.id})
            self._cr.commit()

    @api.multi
    def _update_product_rules(self):
        """
        The method to manage product re-ordering rules based on categories re-ordering rules
         1. Update rules with a link for this category rule
         2. Deactivate this category product rules if its category is changed OR product type is not any more storable
            OR new manual rule is activated
         3. Prepare new product rules
          3.1 Get products of this categroy and which rules does not exist per this location. So, products which rules
            should be created. We consider a rule as lacking if no active rules exist (on the first step all topical
            have been already activated)
          3.2 Create rules for products without rules at all

        Methods:
         * _prepare_vals_for_rule()

        Extra info:
         * We update create rules only for active products
         * We rely upon strict category match, not hierarchy
         * In case there is an active manual rule (not linked to a category rule), it is prime, an extra category would
           not be created
        """
        for rule in self:
            options = rule._prepare_vals_for_rule()
            query = """
                SELECT pr.id
                    FROM product_product pr
                         LEFT JOIN product_template pt ON (pr.product_tmpl_id = pt.id)
                    WHERE pt.categ_id = %(category_id)s
            """
            self._cr.execute(query, {"category_id": rule.category_id.id})
            this_categ_products_dict = self._cr.dictfetchall()
            this_categ_product_ids = [iditem["id"] for iditem in this_categ_products_dict]
            this_categ_product_ids = this_categ_product_ids or [-1]
            options.update({"products_of_this_categ": tuple(this_categ_product_ids)})
            # 1
            query = """
                UPDATE stock_warehouse_orderpoint
                SET
                    active = TRUE,
                    warehouse_id = %(warehouse_id)s,
                    location_id = %(location_id)s,
                    product_min_qty = %(product_min_qty)s,
                    product_max_qty = %(product_max_qty)s,
                    qty_multiple = %(qty_multiple)s,
                    lead_days = %(lead_days)s,
                    lead_type = %(lead_type)s,
                    company_id = %(company_id)s,
                    group_id = %(group_id)s
                WHERE
                    category_rule_id = %(category_rule_id)s
                    AND product_id IN %(products_of_this_categ)s
            """
            self._cr.execute(query, options)
            self._cr.commit()
            # 2
            query = """
                WITH manual_order_points AS (
                    SELECT product_id
                    FROM stock_warehouse_orderpoint
                    WHERE
                        location_id = %(location_id)s
                        AND active = TRUE
                        AND category_rule_id IS NULL
                )
                UPDATE stock_warehouse_orderpoint
                SET active = FALSE
                WHERE
                    category_rule_id = %(category_rule_id)s
                    AND (
                        product_id NOT IN %(products_of_this_categ)s
                        OR product_id IN (SELECT product_id FROM manual_order_points)
                    )
            """
            self._cr.execute(query, options)
            self._cr.commit()

            # 3.1
            query = """
                WITH order_points AS (
                    SELECT product_id
                    FROM stock_warehouse_orderpoint
                    WHERE
                        location_id = %(location_id)s
                        AND (
                            (active = TRUE AND category_rule_id IS NULL)
                            OR (category_rule_id = %(category_rule_id)s)
                        )
                )
                SELECT prod.id
                FROM product_product prod
                    LEFT JOIN product_template pt ON (prod.product_tmpl_id = pt.id)
                WHERE
                    pt.categ_id = %(category_id)s
                    AND pt.type = 'product'
                    AND pt.active = TRUE
                    AND prod.active = TRUE
                    AND prod.id NOT IN (SELECT product_id FROM order_points)
            """
            self._cr.execute(query, {
                "location_id": rule.location_id.id,
                "category_id": rule.category_id.id,
                "category_rule_id": rule.id,
            })
            product_dict = self._cr.dictfetchall()
            if product_dict:
                product_ids = [iditem["id"] for iditem in product_dict]
                options.update({"product_ids": product_ids,})
                # 3.2
                query = """
                    INSERT INTO stock_warehouse_orderpoint
                    (
                        product_id,
                        name,
                        active,
                        warehouse_id,
                        location_id,
                        product_min_qty,
                        product_max_qty,
                        qty_multiple,
                        lead_days,
                        lead_type,
                        company_id,
                        group_id,
                        category_rule_id
                    )
                    SELECT  product_id,
                            %(name)s,
                            TRUE active,
                            %(warehouse_id)s,
                            %(location_id)s,
                            %(product_min_qty)s,
                            %(product_max_qty)s,
                            %(qty_multiple)s,
                            %(lead_days)s,
                            %(lead_type)s,
                            %(company_id)s,
                            %(group_id)s,
                            %(category_rule_id)s
                    FROM unnest(%(product_ids)s) product_id
                """
                self._cr.execute(query, options)
                self._cr.commit()

    @api.multi
    def _prepare_vals_for_rule(self):
        """
        The method to prepare values for a new rule

        Returns:
         * dict

        Extra info:
         * Expected singleton
        """
        self.ensure_one()
        values = {
            "warehouse_id": self.warehouse_id.id,
            "location_id": self.location_id.id,
            "product_min_qty": self.product_min_qty,
            "product_max_qty": self.product_max_qty,
            "qty_multiple": self.qty_multiple,
            "group_id": self.group_id.id or None,
            "lead_days": self.lead_days,
            "lead_type": self.lead_type,
            "company_id": self.company_id.id,
            "category_rule_id": self.id,
            "name": self.name_get()[0][1],
        }
        return values
