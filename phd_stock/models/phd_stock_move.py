from odoo import models, fields, api, _
from datetime import datetime
from datetime import date as dt

from odoo.exceptions import UserError

BOM_SUBCONTRACT_TYPE = 'subcontract'
PRODUCT_CONSUMABLE_TYPE = 'consu'
LOCATION_PRODUCTION_USAGE = 'production'


class PHDStockMove(models.Model):
    _inherit = "stock.move"

    product_sku = fields.Char(string='SKU', related='product_id.default_code', store=True)
    lot_id = fields.Many2one('stock.production.lot', 'Lot#', compute='_compute_lot', store=True)
    partner_id_warehouse = fields.Many2one('res.partner', string='Partner', compute='_compute_partner_for_warehouse',
                                           store=True)
    ship_to = fields.Char(string='Ship To', related='partner_id.e1_ship_to', store=True)
    internal_po = fields.Many2one('purchase.order', string='Internal PO', related='purchase_line_id.order_id',
                                  store=True)
    customer_po = fields.Char(related='sale_line_id.order_id.client_order_ref', string='Customer PO', store=True)

    sale_order_id = fields.Many2one('sale.order', string='SO#', related='sale_line_id.order_id', store=True)
    sale_order_date = fields.Datetime(string='SO Date', related='sale_order_id.date_order', store=True)
    variance = fields.Float(string='Variance', compute='_compute_variance', store=True)
    original_promised_date = fields.Datetime(string='Original Promise Date', compute='_compute_original_promised_date',
                                             store=True)
    days_late = fields.Integer(string="Days Late", compute="_compute_days_late", store=True)

    trigger_field = fields.Integer(compute='_compute_trigger_field')
    quantity_sent = fields.Float(string='Quantity Sent', store=True)
    quantity_before_move = fields.Float(compute='_compute_quantity_before_move', store=True)

    purchase_order_id = fields.Many2one('purchase.order', related='purchase_line_id.order_id', store=True)
    purchase_order_date = fields.Datetime(string='PO Date', related='purchase_order_id.date_order', store=True)
    mo_id = fields.Many2one('mrp.production', compute='_compute_manufacturing_order', store=True, string='MO#')
    date_planned_end = fields.Datetime(compute='_compute_date_planned_end',store=True)
    vendor_wo = fields.Char(string='Vendor WO', related='mo_id.vendor_wo', store=True)
    warehouse = fields.Char(string='Warehouse', compute='_compute_warehouse')
    is_warehouse_report = fields.Boolean(compute='_compute_is_warehouse_report')
    transaction_type = fields.Char(string='Transaction Type', compute='_compute_transaction_type')

    @api.depends('date_expected','mo_id.date_planned_finished')
    def _compute_date_planned_end(self):
        for record in self:
            if record.mo_id:
                record.date_planned_end = record.mo_id.date_planned_finished
            else:
                record.date_planned_end = record.date_expected

    def _compute_transaction_type(self):
        for record in self:
            location = self._context.get('default_location_id', -1)
            if record.location_id.id == location:
                record.transaction_type = 'WH OUT'
            elif record.location_dest_id.id == location:
                record.transaction_type = 'WH IN'
            elif record.inventory_id:
                record.transaction_type = 'WH INV-ADJ'
            elif record.picking_id:
                record.transaction_type = 'WH Transfer'
            else:
                record.transaction_type = False

    def _compute_is_warehouse_report(self):
        for record in self:
            location = self._context.get('default_location_id', False)
            if location:
                if record.location_id.id == location or record.location_dest_id.id == location:
                    record.is_warehouse_report = True
                else:
                    record.is_warehouse_report = False
            else:
                record.is_warehouse_report = False

    def _compute_warehouse(self):
        for record in self:
            if self._context.get('default_location_id', False):
                location = self.env['stock.location'].search(
                    [('id', '=', self._context.get('default_location_id', False))], limit=1)
                if location:
                    record.warehouse = location.display_name
                else:
                    record.warehouse = False
            else:
                record.warehouse = False

    @api.depends('state')
    def _compute_quantity_before_move(self):
        for record in self:
            if record.sale_line_id:
                record.quantity_before_move = record.sale_line_id.qty_to_deliver + record.quantity_done
            elif record.purchase_line_id:
                record.quantity_before_move = record.purchase_line_id.product_uom_qty - record.purchase_line_id.qty_received + record.quantity_done

    @api.depends('purchase_line_id', 'state')
    def _compute_manufacturing_order(self):
        for record in self:
            if record.purchase_line_id:
                mrp = self.env['mrp.production'].search(
                    [('product_id', '=', record.product_id.id), ('purchase_id', '=', record.purchase_order_id.id)],
                    limit=1)
                if mrp:
                    record.mo_id = mrp
                else:
                    record.mo_id = False
            else:
                record.mo_id = False

    def _compute_trigger_field(self):
        for record in self:
            record.trigger_field = 1
            record.quantity_sent = record.quantity_done

    @api.depends('quantity_before_move', 'quantity_done', 'state')
    def _compute_variance(self):
        for line in self:
            line.variance = line.quantity_done - line.quantity_before_move

    @api.depends('state', 'sale_line_id.order_id.state', 'purchase_line_id.order_id.state')
    def _compute_original_promised_date(self):
        for line in self:
            if line.sale_line_id:
                if hasattr(line.sale_line_id.order_id, 'delay_tracker_ids'):
                    delay_tracker = line.sale_line_id.order_id.delay_tracker_ids
                    if delay_tracker:
                        dates = []
                        for date in delay_tracker:
                            if isinstance(date.promised_date, dt):
                                dates.append(date.promised_date)
                        line.original_promised_date = min(dates)
                    else:
                        line.original_promised_date = False
                else:
                    line.original_promised_date = False

            if line.purchase_line_id:
                if hasattr(line.purchase_line_id.order_id, 'delay_tracker_ids'):
                    delay_tracker = line.purchase_line_id.order_id.delay_tracker_ids
                    if delay_tracker:
                        dates = []
                        for date in delay_tracker:
                            if isinstance(date.promised_date, dt):
                                dates.append(date.promised_date)
                        line.original_promised_date = min(dates)
                    else:
                        line.original_promised_date = False
                else:
                    line.original_promised_date = False

    @api.depends('date_expected', 'original_promised_date')
    def _compute_days_late(self):
        for line in self:
            if line.date_expected and line.original_promised_date:
                line.days_late = (line.date_expected - line.original_promised_date).days
            else:
                line.days_late = 0

    @api.depends('move_line_ids.lot_id')
    def _compute_lot(self):
        for line in self:
            if line.move_line_ids:
                if line.move_line_ids[0].lot_id:
                    line.lot_id = line.move_line_ids[0].lot_id
                else:
                    line.lot_id = False
            else:
                line.lot_id = False

    @api.depends('purchase_line_id.partner_id', 'sale_line_id.order_partner_id')
    def _compute_partner_for_warehouse(self):
        for line in self:
            if line.purchase_line_id:
                line.partner_id_warehouse = line.purchase_line_id.partner_id
            elif line.sale_line_id:
                line.partner_id_warehouse = line.sale_line_id.order_partner_id
            else:
                line.partner_id_warehouse = False

    def action_get_warehouse_report(self):
        records = self.env['stock.move'].search([])
        if records:
            list_of_ids = records.filtered(lambda x: x.is_warehouse_report).ids
            action = self.env.ref('phd_stock.phd_warehouse_report_action').read()[0]
            action['domain'] = [('id', 'in', list_of_ids), ('state', '=', 'done')]
            action['context'] = {'list_view_report_id': self.env.ref('phd_stock.phd_warehoure_report').id,
                                 'date_range': 'date',
                                 'default_location_id': self._context.get('default_location_id', False)}
            return action

    #########################
    # HELPER FUNCTIONS
    #########################
    def is_subcontracting_component_move(self):
        return self.raw_material_production_id.bom_id.type == BOM_SUBCONTRACT_TYPE

    def is_production_location(self, location):
        return location and location.usage == LOCATION_PRODUCTION_USAGE

    def create_journal_entry_for_consumable_leaving_company(self, qty, description, svl_id, cost):
        location_to = self.location_dest_id
        company_from = self.mapped('move_line_ids.location_id.company_id') or False
        cost = -1 * cost
        account_data = self._get_accounting_data_for_consumable_valuation()

        journal_id = account_data.get('journal_id')
        acc_consu = account_data.get('acc_consu')
        acc_dest = account_data.get('acc_dest')

        if self.is_subcontracting_component_move:
            if self.is_production_location(location_to):  # goods delivered to production
                self.with_context(force_company=company_from.id)._create_account_move_line(acc_consu, acc_dest,
                                                                                           journal_id, qty, description,
                                                                                           svl_id, cost)

    def _get_accounting_data_for_consumable_valuation(self):
        journal_id, acc_src, acc_dest, acc_valuation = super(PHDStockMove, self)._get_accounting_data_for_valuation()
        accounts_data = self.product_id.product_tmpl_id.get_product_accounts()
        acc_consu = None
        if self.product_id.type == PRODUCT_CONSUMABLE_TYPE:
            acc_consu = accounts_data.get('stock_consumable', False) and accounts_data.get('stock_consumable').id

        if not acc_consu:
            raise UserError(_(
                'Cannot find a stock consumable account for the product %s. You must define one on the product category, '
                'or on the location, before processing this operation.') % (self.product_id.display_name))

        return {
            'journal_id': journal_id,
            'acc_src': acc_src,
            'acc_dest': acc_dest,
            'acc_consu': acc_consu,
            'acc_valuation': acc_valuation
        }

    def _account_entry_move(self, qty, description, svl_id, cost):
        """ Accounting Consumable Valuation Entries """
        self.ensure_one()

        if self.product_id.type == PRODUCT_CONSUMABLE_TYPE:
            if self.restrict_partner_id:
                # if the move isn't owned by the company, we don't make any valuation
                return False

            if self._is_out():
                self.create_journal_entry_for_consumable_leaving_company(qty, description, svl_id, cost)

            if self.company_id.anglo_saxon_accounting:
                # eventually reconcile together the invoice and valuation accounting entries on the stock interim accounts
                self._get_related_invoices()._stock_account_anglo_saxon_reconcile_valuation(product=self.product_id)

        return super(PHDStockMove, self)._account_entry_move(qty, description, svl_id, cost)
