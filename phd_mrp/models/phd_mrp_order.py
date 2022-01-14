import logging

from odoo import api, fields, models, SUPERUSER_ID, _
import pytz

_logger = logging.getLogger(__name__)


class PHDMrpOrder(models.Model):
    _inherit = 'mrp.production'

    cert_analysis_number = fields.Char(string="Certificate of Analysis Number")

    def _default_stage_id(self):
        return self.env['phd.mrp.order.stage'].search([], order='sequence asc', limit=1).id

    stage_id = fields.Many2one(
        'phd.mrp.order.stage', 'Stage', ondelete='restrict', copy=False,
        group_expand='_read_group_stage_ids',
        tracking=False, default=lambda self: self._default_stage_id())

    purchase_id = fields.Many2one('purchase.order',
                                  string="Purchase Order",
                                  copy=False)

    purchase_line_id = fields.Many2one('purchase.order.line',
                                       string="Purchase Order Line",
                                       copy=False)

    def action_assign(self):
        """
        If not_auto_assign has set, do not call the action assign (Check Availability) of MO
        :return:
        :rtype: bool
        """
        res = self._context.get('not_auto_assign') or super(PHDMrpOrder, self).action_assign()
        return res

    @api.model
    def _read_group_stage_ids(self, stages, domain, order):
        search_domain = []
        stage_ids = stages._search(search_domain, order=order, access_rights_uid=SUPERUSER_ID)
        return stages.browse(stage_ids)

    @api.constrains('state')
    def _change_stage(self):
        switcher = {
            'draft': self.env.ref('phd_mrp.phd_mrp_order_stage_draft').id,
            'confirmed': self.env.ref('phd_mrp.phd_mrp_order_stage_confirmed').id,
            'planned': self.env.ref('phd_mrp.phd_mrp_order_stage_planned').id,
            'progress': self.env.ref('phd_mrp.phd_mrp_order_stage_in_progress').id,
            'to_close': self.env.ref('phd_mrp.phd_mrp_order_stage_to_close').id,
            'done': self.env.ref('phd_mrp.phd_mrp_order_stage_done').id,
            'cancel': self.env.ref('phd_mrp.phd_mrp_order_stage_cancelled').id,
        }
        for mrp in self:
            stage_id = switcher.get(mrp.state, False)
            if stage_id:
                mrp.write({'stage_id': stage_id})

    # def add_consume(self):
    #     self.ensure_one()
    #     if self.purchase_id:
    #         move_raw_data = self._get_moves_raw_values()
    #         if move_raw_data:
    #             move_raw_data[0]['product_uom_qty'] = self.product_qty - self.qty_produced
    #         move_raw = self.env['stock.move'].create(move_raw_data)
    #         for move in self.move_raw_ids:
    #             move.write({
    #                 'unit_factor': move.product_uom_qty / (self.product_qty - self.qty_produced),
    #             })
    #         move_raw._adjust_procure_method()
    #         (self.move_raw_ids | self.move_finished_ids)._action_confirm()
    #
    #         picking = self.purchase_id.picking_ids.filtered(lambda m: m.state not in ['done', 'cancel'])
    #         if picking:
    #             move_lines = picking.move_lines.filtered(lambda x: x.product_id == self.product_id)
    #             if move_lines:
    #                 finished_move = self.move_finished_ids.filtered(lambda m: m.product_id == move_lines[0].product_id)
    #                 finished_move.write({'move_dest_ids': [(4, move_lines[0].id, False)]})
    #
    #                 self.move_raw_ids._action_assign()
    #                 self.workorder_ids._refresh_wo_lines()

    def open_add_qty_to_produce(self):
        self.ensure_one()
        add_qty = self.env['phd.mrp.add.qty.to.produce'].create({
            'production_id': self.id
        })
        return {
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'phd.mrp.add.qty.to.produce',
            'target': 'new',
            'res_id': add_qty.id,
        }

    def phd_open_produce_product(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Produce Date',
            'res_model': 'phd.update.date',
            'target': 'new',
            'view_id': self.env.ref('phd_inventory.phd_update_date_form_view').id,
            'view_mode': 'form',
            'context': {
                'default_date_time': fields.datetime.today(),
                'default_res_id': self.id,
                'default_production_id': self.id,
                'default_field': 'date',
                'default_is_update': False,
                'default_model': self._name,
                'default_action_name': 'open_produce_product',
                'default_update_action_name': 'update_date_model_related',
            }
        }

    @api.model
    def _update_missing_journal_entry_produce_over_plan(self):
        pass
