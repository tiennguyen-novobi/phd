from odoo import models, fields, api, _

class PHDStockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    # lot_id = fields.Many2one(domain="[('product_id', '=', product_id), ('company_id', '=', company_id), ('lot_qty', '>', 0)]")

    mo_id = fields.Many2one('mrp.production', string="MO#", compute='_compute_mo_id', store=True)

    @api.depends('picking_id.state')
    def _compute_mo_id(self):
        for record in self:
            if record.picking_id:
                if record.picking_id.purchase_id:
                    mo_id = self.env['mrp.production'].search([('product_id','=',record.product_id.id),
                                                               ('state','not in',['draft','cancel']),
                                                               ('purchase_id','=',record.picking_id.purchase_id.id)],limit=1)
                    if mo_id:
                        record.mo_id = mo_id.id
                    else:
                        record.mo_id = False
                else:
                    record.mo_id = False
            else:
                record.mo_id = False

    @api.model
    def create(self, vals_list):
        res = super(PHDStockMoveLine, self).create(vals_list)
        res._compute_mo_id()
        return res