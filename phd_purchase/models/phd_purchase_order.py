import logging

from odoo import api, fields, models, SUPERUSER_ID, _

_logger = logging.getLogger(__name__)


class PHDSaleOrder(models.Model):
    _inherit = 'purchase.order'

    ###################################
    # DEFAULT FUNCTIONS
    ###################################

    def _default_stage_id(self):
        return self.env['phd.purchase.order.stage'].search([], order='sequence asc', limit=1).id

    ###################################
    # FIELDS
    ###################################

    stage_id = fields.Many2one(
        'phd.purchase.order.stage', 'Stage', ondelete='restrict', copy=False,
        group_expand='_read_group_stage_ids',
        tracking=True, default=lambda self: self._default_stage_id())
    partner_id = fields.Many2one(domain="[('type', '!=', 'delivery'),'|', ('company_id', '=', False), ('company_id', '=', company_id)]")
    # previous_state = fields.Char()
    is_subcontracting = fields.Boolean(related='partner_id.is_subcontractor', readonly=True)

    # Kanban View
    previous_state = fields.Many2one('phd.purchase.order.stage', 'Stage')
    # previous_state_text = fields.Char()
    # current_stage = fields.Char(related='stage_id.name', store=True)

    shipping_address_id = fields.Many2one('res.partner', string="Shipping Address", check_company=True)

    ###################################
    # ONCHANGE FUNCTIONS
    ###################################
    @api.onchange('picking_type_id')
    def _onchange_shipping_operation_type(self):
        default_dest_address_id = self.picking_type_id.default_dest_address_id
        if default_dest_address_id:
            self.shipping_address_id = default_dest_address_id

    @api.model
    def _read_group_stage_ids(self, stages, domain, order):
        search_domain = []
        if self._context.get('subcontracting',False):
            stage_ids = (
                self.env.ref('phd_purchase.phd_purchase_order_stage_rfq').id,
                self.env.ref('phd_purchase.phd_purchase_order_stage_rfq_sent').id,
                self.env.ref('phd_purchase.phd_purchase_order_stage_to_approve').id,
                self.env.ref('phd_purchase.phd_purchase_order_stage_purchase_order').id,
                self.env.ref('phd_purchase.phd_purchase_order_stage_cancelled').id,
                self.env.ref('phd_purchase.phd_purchase_order_stage_locked').id,
                self.env.ref('phd_purchase.phd_purchase_order_stage_on_hold').id,
            )
            search_domain = [('id', 'in', stage_ids)]
        stage_ids = stages._search(search_domain, order=order, access_rights_uid=SUPERUSER_ID)
        return stages.browse(stage_ids)
    
    @api.constrains('state')
    def _change_stage(self):
        switcher = {
            'draft':self.env.ref('phd_purchase.phd_purchase_order_stage_rfq').id,
            'sent':self.env.ref('phd_purchase.phd_purchase_order_stage_rfq_sent').id,
            'to approve':self.env.ref('phd_purchase.phd_purchase_order_stage_to_approve').id,
            'purchase':self.env.ref('phd_purchase.phd_purchase_order_stage_purchase_order').id,
            'done':self.env.ref('phd_purchase.phd_purchase_order_stage_locked').id,
            'cancel': self.env.ref('phd_purchase.phd_purchase_order_stage_cancelled').id,
        }
        for po in self:
            stage_id = switcher.get(po.state, False)
            if stage_id:
                po.write({'stage_id': stage_id})

    def action_on_hold(self):
        self.write({'stage_id': self.env.ref('phd_purchase.phd_purchase_order_stage_on_hold').id,
                    'previous_state': self.stage_id.id})

    def action_continue(self):
        self.write({'stage_id': self.previous_state.id})

    # def action_acknowledgment(self):
    #     self.write({'stage_id': self.env.ref('phd_purchase.phd_purchase_order_stage_acknowledgment').id})

    def action_ready_to_pickup(self):
        self.write({'stage_id': self.env.ref('phd_purchase.phd_purchase_order_stage_ready_pickup').id})

    def action_shipped(self):
        self.write({'stage_id': self.env.ref('phd_purchase.phd_purchase_order_stage_shipped').id})

    def generate_mo_for_subcontracting(self):
        self.ensure_one()
        pickings = self.picking_ids.filtered(lambda x: x.state not in ('done', 'cancel'))
        if pickings:
            for line in self.order_line:
                mo = self.env['mrp.production'].search([('purchase_id','=', line.order_id.id), ('product_id','=', line.product_id.id)], limit=1)
                if not mo:
                    move = pickings[0].move_lines.filtered(lambda x: x.product_id == line.product_id)
                    if move:
                        moves = move[0].filtered(lambda x: x.state not in ('done', 'cancel'))._action_confirm()
                        seq = 0
                        for move in sorted(moves, key=lambda move: move.date_expected):
                            seq += 5
                            move.sequence = seq
                        moves._action_assign()
                        if moves.move_line_ids:
                            mo = self.env['mrp.production'].search([('purchase_id','=', line.order_id.id), ('product_id','=', line.product_id.id)], limit=1)
                            if mo:
                                moves.move_line_ids[0].mo_id = mo.id