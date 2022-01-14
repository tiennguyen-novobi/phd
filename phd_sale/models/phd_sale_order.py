import logging

from odoo import api, fields, models, SUPERUSER_ID, _

_logger = logging.getLogger(__name__)


class PHDSaleOrder(models.Model):
    _inherit = 'sale.order'

    def _default_stage_id(self):
        return self.env['phd.sale.order.stage'].search([], order='sequence asc', limit=1).id

    stage_id = fields.Many2one(
        'phd.sale.order.stage', 'Stage', ondelete='restrict', copy=False,
        group_expand='_read_group_stage_ids',
        tracking=True, default=lambda self: self._default_stage_id())
    partner_id = fields.Many2one(
        domain="[('type', '!=', 'delivery'),'|', ('company_id', '=', False), ('company_id', '=', company_id)]")
    closed_date = fields.Datetime(copy=False, default=fields.Datetime.now, string="Closed Date")
    previous_state = fields.Many2one('phd.sale.order.stage', 'Stage')
    partner_shipping_id = fields.Many2one(
        domain="['|', '&', '|', ('company_id', '=', False), ('company_id', '=', company_id), ('parent_id', '=', partner_id), ('id', '=', partner_id)]")
    partner_invoice_id = fields.Many2one(
        domain="['|', '&', '|', ('company_id', '=', False), ('company_id', '=', company_id), ('parent_id', '=', partner_id),  ('id', '=', partner_id)]")

    @api.model
    def _read_group_stage_ids(self, stages, domain, order):
        search_domain = []
        stage_ids = stages._search(search_domain, order=order, access_rights_uid=SUPERUSER_ID)
        return stages.browse(stage_ids)

    @api.constrains('state')
    def _change_stage(self):
        switcher = {
            'draft': self.env.ref('phd_sale.phd_sale_order_stage_quotation').id,
            'sent': self.env.ref('phd_sale.phd_sale_order_stage_quotation_sent').id,
            'sale': self.env.ref('phd_sale.phd_sale_order_stage_sale_order').id,
            'cancel': self.env.ref('phd_sale.phd_sale_order_stage_cancelled').id,
        }
        for so in self:
            stage_id = switcher.get(so.state, False)
            if stage_id:
                so.write({'stage_id': stage_id})

    def action_closed(self):
        self.write(
            {'stage_id': self.env.ref('phd_sale.phd_sale_order_stage_closed').id, 'closed_date': fields.Datetime.now()})

    def action_on_hold(self):
        self.write(
            {'stage_id': self.env.ref('phd_sale.phd_sale_order_stage_on_hold').id, 'previous_state': self.stage_id.id})

    def action_continue(self):
        self.write({'stage_id': self.previous_state.id})

    def action_partially_shipped(self):
        self.write({'stage_id': self.env.ref('phd_sale.phd_sale_order_stage_partially_shipped').id})
