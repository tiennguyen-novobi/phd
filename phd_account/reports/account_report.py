from odoo import models, fields, api, _


class AccountReport(models.AbstractModel):
    _inherit = 'account.report'

    @api.model
    def _resolve_caret_option_view(self, target):
        res = super(AccountReport, self)._resolve_caret_option_view(target)
        if res == 'account.view_account_payment_form':
            if 'is_deposit_customization' in target and target.is_deposit_customization:
                res = 'phd_account.view_account_payment_customization_payment'
        return res
