from odoo import api, models, fields, _

MODEL_METHOD_MAPPING = {
    'payarc.batch.report': 'get_batch_from_payarc',
    'paypal.transaction': 'get_paypal_transaction_via_braintree'
}


class RequestLog(models.Model):
    _name = 'request.log'
    _description = 'Request Log'
    _rec_name = 'create_date'
    _order = 'create_date desc'

    status = fields.Selection([
        ('done', 'Done'),
        ('failed', 'Failed')
    ])
    is_resolved = fields.Boolean(string='Is Resolved')
    from_date = fields.Date(string='Date From')
    to_date = fields.Date(string='Date To')
    api_ref = fields.Char(string='Res ID')

    res_model = fields.Char(string='Resource Model', readonly=True)
    res_id = fields.Many2oneReference('Resource ID', model_field='res_model',
                                      readonly=True, help="The record id this is attached to.")

    message = fields.Char(string='Message')
    datas = fields.Text(string='Datas')

    def action_open_details(self):
        return True

    def run(self):
        self.ensure_one()
        if hasattr(self.env[self.res_model], MODEL_METHOD_MAPPING[self.res_model]):
            getattr(self.env[self.res_model], MODEL_METHOD_MAPPING[self.res_model])(self.from_date.strftime("%Y-%m-%d"),
                                                                                    self.to_date.strftime("%Y-%m-%d"))
        self.update({'is_resolved': True})

