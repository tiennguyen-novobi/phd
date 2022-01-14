from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class WarningTagAnalytic(models.TransientModel):
    _name = 'phd.tag.analytic'

    message = fields.Text('Message', default=_("Missing Analytic Account or Analytic Tags for Invoice Lines. Are you sure you want to continue ?"))

    def action_post(self):
        self.ensure_one()
        account_move = self.env['account.move'].browse(self._context.get('active_id'))
        if account_move:
            context = dict(self._context)
            context.update({
                'is_post': True
            })
            account_move.with_context(context).action_post()