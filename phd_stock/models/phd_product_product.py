from odoo import models, fields, api, _


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    def get_product_accounts(self, fiscal_pos=None):
        """ Add the stock journal related to product to the result of super()
        @return: dictionary which contains all needed information regarding stock accounts and journal and super (income+expense accounts)
        """
        accounts = super(ProductTemplate, self).get_product_accounts(fiscal_pos=fiscal_pos)
        accounts.update({'stock_consumable': self.categ_id.property_consumable_account_id or False})
        return accounts


class PHDProductProduct(models.Model):
    _inherit = 'product.product'

    safety_stock = fields.Float(String='Safety Stock', default=0)
    qty_reserved = fields.Float('Quantity Reserved', compute='_compute_qty_reserved', store=False)

    def _compute_qty_reserved(self):
        for record in self:
            record.qty_reserved = 0
            stock_move_line_ids = record.stock_move_ids.mapped('move_line_ids').filtered(
                lambda line: line.state in ('partially_available', 'assigned'))
            if stock_move_line_ids:
                record.qty_reserved = sum(line.product_uom_qty for line in stock_move_line_ids)

    def action_open_reserved(self):
        context = {
            'create': 0,
        }
        action = self.env.ref('stock.stock_move_line_action').read()[0]
        action['domain'] = [('product_id', '=', self.id), ('state', 'in', ('partially_available', 'assigned')),
                            ('product_uom_qty', '!=', 0)]
        action['context'] = context
        action['view_type'] = 'tree'
        action['view_mode'] = 'list'
        action['views'] = [(self.env.ref('phd_stock.phd_view_move_line_tree_qty_reserved').id, 'list')]
        return action


class ProductCategory(models.Model):
    _inherit = 'product.category'

    property_consumable_account_id = fields.Many2one(
        'account.account', 'Consumable Account', company_dependent=True,
        domain="[('company_id', '=', allowed_company_ids[0]), ('deprecated', '=', False)]", check_company=True)
