from odoo import api, fields, models, tools, SUPERUSER_ID, _
from datetime import date
from odoo.exceptions import ValidationError, UserError

class PHDMkoStage(models.Model):
    _name = 'phd.mko.stage'
    _description = 'MKO Stage'
    _order = "sequence, id"
    _fold_name = 'folded'

    @api.model
    def _get_sequence(self):
        others = self.search([('sequence','<>',False)], order='sequence desc', limit=1)
        if others:
            return (others[0].sequence or 0) + 1
        return 1

    name = fields.Char('Name', required=True, translate=True)
    sequence = fields.Integer('Sequence', default=_get_sequence)
    folded = fields.Boolean('Folded in kanban view')
    allow_apply_change = fields.Boolean(string='Allow to apply changes', help='Allow to apply changes from this stage.')
    final_stage = fields.Boolean(string='Final Stage')

    approval_template_ids = fields.One2many('phd.mko.approval.template', 'stage_id', 'Approvals')
    approval_roles = fields.Char('Approval Roles', compute='_compute_approvals', store=True)
    is_blocking = fields.Boolean('Blocking Stage', compute='_compute_is_blocking', store=True)

    @api.depends('approval_template_ids.name')
    def _compute_approvals(self):
        for rec in self:
            rec.approval_roles = ', '.join(rec.approval_template_ids.mapped('name'))

    @api.depends('approval_template_ids.approval_type')
    def _compute_is_blocking(self):
        for rec in self:
            rec.is_blocking = any(template.approval_type == 'mandatory' for template in rec.approval_template_ids)

class PHDMkoApproval(models.Model):
    _name = "phd.mko.approval"
    _description = 'Approval'
    _order = 'approval_date desc'

    eco_id = fields.Many2one(
        'phd.mko', 'MKO',
        ondelete='cascade', required=True)
    approval_template_id = fields.Many2one(
        'phd.mko.approval.template', 'Template',
        ondelete='cascade', required=True)
    name = fields.Char('Role', related='approval_template_id.name', store=True, readonly=False)
    user_id = fields.Many2one(
        'res.users', 'Approved by')
    required_user_ids = fields.Many2many(
        'res.users', string='Requested Users', related='approval_template_id.user_ids', readonly=False)
    template_stage_id = fields.Many2one(
        'phd.mko.stage', 'Approval Stage',
        related='approval_template_id.stage_id', store=True, readonly=False)
    eco_stage_id = fields.Many2one(
        'phd.mko.stage', 'Stage',
        related='eco_id.stage_id', store=True, readonly=False)
    status = fields.Selection([
        ('none', 'Not Yet'),
        ('comment', 'Commented'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected')], string='Status',
        default='none', required=True)
    approval_date = fields.Datetime('Approval Date')
    is_closed = fields.Boolean()
    is_approved = fields.Boolean(
        compute='_compute_is_approved', store=True)
    is_rejected = fields.Boolean(
        compute='_compute_is_rejected', store=True)

    @api.depends('status', 'approval_template_id.approval_type')
    def _compute_is_approved(self):
        for rec in self:
            if rec.approval_template_id.approval_type == 'mandatory':
                rec.is_approved = rec.status == 'approved'
            else:
                rec.is_approved = True

    @api.depends('status', 'approval_template_id.approval_type')
    def _compute_is_rejected(self):
        for rec in self:
            if rec.approval_template_id.approval_type == 'mandatory':
                rec.is_rejected = rec.status == 'rejected'
            else:
                rec.is_rejected = False

class MrpEcoApprovalTemplate(models.Model):
    _name = "phd.mko.approval.template"
    _order = "sequence"
    _description = 'MKO Approval Template'

    name = fields.Char('Role', required=True)
    sequence = fields.Integer('Sequence')
    approval_type = fields.Selection([
        ('optional', 'Approves, but the approval is optional'),
        ('mandatory', 'Is required to approve'),
        ('comment', 'Comments only')], 'Approval Type',
        default='mandatory', required=True)
    user_ids = fields.Many2many('res.users', string='Users', required=True)
    stage_id = fields.Many2one('phd.mko.stage', 'Stage', required=True)

class PHDMko(models.Model):
    _name = 'phd.mko'
    _description = 'Marketing Order'
    _order = "id, order_id"
    _rec_name = "order_id"

    def _default_stage_id(self):
        return self.env['phd.mko.stage'].search([], order='sequence asc', limit=1).id

    order_id = fields.Char(string="Order", copy=False)
    name = fields.Char('Name of Promotion', copy=False, required=True)
    user_id = fields.Many2one('res.users', string='User', default=lambda self: self.env.user,
                              tracking=True,
                              check_company=True, required=True, ondelete='cascade')
    requested_by = fields.Char(string="Requested By", related="user_id.name")
    stage_id = fields.Many2one(
        'phd.mko.stage', 'Stage', ondelete='restrict', copy=False,
        group_expand='_read_group_stage_ids',
        tracking=True, default = lambda self: self._default_stage_id())
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.company)
    note = fields.Text('Note')
    color = fields.Integer('Color')

    date_order = fields.Date('Date', required=True)
    memo = fields.Char(string="Memo")
    date_received = fields.Date(string="Date Received")
    promo_id = fields.Char(string="Promotion ID")
    internal_credit_memo = fields.Char(string="Internal Credit Memo")
    order_line = fields.One2many('phd.mko.line', 'mko_id', string='Order Lines', copy=True,
                                 auto_join=True)
    partner_id = fields.Many2one('res.partner', string="Customer", required=True)
    state = fields.Selection(selection=[
        ('draft', 'Draft'),
        ('progress', 'Progess'),
        ('done', 'Done')], string='State', default='draft')
    promotion_period_from = fields.Date(string="From", required=True, copy=False, default=fields.Date.today)
    promotion_period_to = fields.Date(string="To", required=True, copy=False, default=fields.Date.today)
    is_approved = fields.Boolean(copy=False)
    #Field for kanban logic
    allow_change_stage = fields.Boolean(
        'Allow Change Stage', compute='_compute_allow_change_stage')
    allow_apply_change = fields.Boolean(
        'Show Apply Change', compute='_compute_allow_apply_change')
    approval_ids = fields.One2many('phd.mko.approval', 'eco_id', 'Approvals', help='Approvals by stage')
    user_can_approve = fields.Boolean(
        'Can Approve', compute='_compute_user_approval',
        help='Technical field to check if approval by current user is required')
    user_can_reject = fields.Boolean(
        'Can Reject', compute='_compute_user_approval',
        help='Technical field to check if reject by current user is possible')
    kanban_state = fields.Selection([
        ('normal', 'In Progress'),
        ('done', 'Approved'),
        ('blocked', 'Blocked')], string='Kanban State',
        copy=False, compute='_compute_kanban_state', store=True)
    is_receivable = fields.Boolean(compute='_compute_group_receivable_user')
    is_mk_user = fields.Boolean(compute='_compute_group_mk_user')
    is_mk_manager = fields.Boolean(compute='_compute_group_mk_manger')

    def _compute_group_receivable_user(self):
        group_receivable_id = self.env.ref("phd_marketing.group_mko_receivable_user").id
        group_ids = self.env.user.groups_id.ids
        self.is_receivable = True if group_receivable_id in group_ids else False

    def _compute_group_mk_user(self):
        group_user_id = self.env.ref("phd_marketing.group_mko_user").id
        group_manager_id = self.env.ref("phd_marketing.group_mko_manager").id
        group_ids = self.env.user.groups_id.ids
        self.is_mk_user = True if group_user_id in group_ids and group_manager_id not in group_ids else False

    def _compute_group_mk_manger(self):
        group_manager_id = self.env.ref("phd_marketing.group_mko_manager").id
        group_ids = self.env.user.groups_id.ids
        self.is_mk_manager = True if group_manager_id in group_ids else False

    @api.depends('stage_id', 'approval_ids.is_approved', 'approval_ids.is_rejected')
    def _compute_kanban_state(self):
        for rec in self:
            approvals = rec.approval_ids.filtered(lambda app:
                                                  app.template_stage_id == rec.stage_id and not app.is_closed)
            if not approvals:
                rec.kanban_state = 'normal'
            elif all(approval.is_approved for approval in approvals):
                rec.kanban_state = 'done'
            elif any(approval.is_rejected for approval in approvals):
                rec.kanban_state = 'blocked'
            else:
                rec.kanban_state = 'normal'

    def action_apply(self):
        self.ensure_one()
        self._check_company()
        vals = {'state': 'done'}
        stage_id = self.env['phd.mko.stage'].search([('final_stage', '=', True)], limit=1).id
        if stage_id:
            vals['stage_id'] = stage_id
        self.write(vals)

    @api.depends('state', 'stage_id.allow_apply_change')
    def _compute_allow_apply_change(self):
        for rec in self:
            rec.allow_apply_change = rec.stage_id.allow_apply_change

    @api.depends('kanban_state', 'stage_id', 'approval_ids')
    def _compute_allow_change_stage(self):
        for rec in self:
            approvals = rec.approval_ids.filtered(lambda app: app.template_stage_id == rec.stage_id)
            if approvals:
                rec.allow_change_stage = rec.kanban_state == 'done' or rec.kanban_state == 'blocked'
            else:
                rec.allow_change_stage = rec.kanban_state in ['normal', 'done']

    def _compute_user_approval(self):
        for mko in self:
            is_required_approval = mko.stage_id.approval_template_ids.filtered(lambda x: x.approval_type in ('mandatory', 'optional') and self.env.user in x.user_ids)
            user_approvals = mko.approval_ids.filtered(lambda x: x.template_stage_id == mko.stage_id and x.user_id == self.env.user and not x.is_closed)
            last_approval = user_approvals.sorted(lambda a : a.create_date, reverse=True)[:1]
            mko.user_can_approve = is_required_approval and not last_approval.is_approved
            mko.user_can_reject = is_required_approval and not last_approval.is_rejected

    def approve(self):
        self._create_or_update_approval(status='approved')
        self.stage_id = self.env.ref("phd_marketing.phd_marketing_order_stage_approval")
        self._send_mail_approved_order()

    def reject(self):
        self._create_or_update_approval(status='rejected')
        stage_id = self.env.ref('phd_marketing.phd_marketing_order_stage_rejected').id
        vals = {'stage_id': stage_id,'kanban_state': 'blocked'}
        self.write(vals)

    def action_apply(self):
        self.ensure_one()
        self._check_company()
        vals = {'state': 'done'}
        stage_id = self.env.ref('phd_marketing.phd_marketing_order_stage_waiting_for_approval').id
        if stage_id:
            vals['stage_id'] = stage_id
        self.write(vals)

    def _create_or_update_approval(self, status):
        for eco in self:
            for approval_template in eco.stage_id.approval_template_ids.filtered(lambda a: self.env.user in a.user_ids):
                approvals = eco.approval_ids.filtered(lambda x: x.approval_template_id == approval_template and not x.is_closed)
                none_approvals = approvals.filtered(lambda a: a.status == 'none')
                confirmed_approvals = approvals - none_approvals
                if none_approvals:
                    none_approvals.write({'status': status, 'user_id': self.env.uid, 'approval_date': fields.Datetime.now()})
                    confirmed_approvals.write({'is_closed': True})
                    approval = none_approvals[:1]
                else:
                    approvals.write({'is_closed': True})
                    approval = self.env['phd.mko.approval'].create({
                        'eco_id': eco.id,
                        'approval_template_id': approval_template.id,
                        'status': status,
                        'user_id': self.env.uid,
                        'approval_date': fields.Datetime.now(),
                    })

    @api.model
    def _read_group_stage_ids(self, stages, domain, order):
        search_domain = []
        stage_ids = stages._search(search_domain, order=order, access_rights_uid=SUPERUSER_ID)
        return stages.browse(stage_ids)

    @api.model
    def _send_mail_to_manager(self):
        approvals = self.approval_ids.filtered(lambda app: app.approval_template_id and app.approval_template_id.approval_type == 'mandatory')
        if approvals:
            mail_template = self.env.ref('phd_marketing.phd_mko_notify_new_order')
            for app in approvals:
                for user in app.approval_template_id.user_ids:
                    if user.email:
                        mail_template.update({
                            'email_to': user.email,
                        })
                        mail_template.send_mail(self.id, force_send=True)

    @api.model
    def _send_mail_approved_order(self):
        mail_template = self.env.ref('phd_marketing.phd_mko_notify_approved_order')
        users = self.env['res.users'].search(
            [('groups_id', 'in', [self.env.ref('phd_marketing.group_mko_receivable_user').id])])
        emails = set(user.email for user in users if user.email)
        email_values = {
            'email_to': ','.join(emails)
        }
        mail_template.send_mail(self.id, force_send=True, email_values=email_values)

    @api.model
    def create(self, vals):
        prefix = self.env['ir.sequence'].next_by_code('phd.mko') or ''
        vals['name'] = '%s%s' % (prefix and '%s: ' % prefix or '', vals.get('name', ''))
        vals['order_id'] = prefix
        mko = super(PHDMko, self).create(vals)
        mko._create_approvals()
        return mko

    def _create_approvals(self):
        for mko in self:
            for approval_template in mko.stage_id.approval_template_ids:
                approval = mko.approval_ids.filtered(lambda app: app.approval_template_id == approval_template and not app.is_closed)
                if not approval:
                    self.env['phd.mko.approval'].create({
                        'eco_id': mko.id,
                        'approval_template_id': approval_template.id,
                    })

    @api.constrains('stage_id')
    def _check_stage(self):
        approval_id = self.env.ref("phd_marketing.phd_marketing_order_stage_approval")
        closed_id = self.env.ref("phd_marketing.phd_marketing_order_stage_closed")
        waiting_id = self.env.ref("phd_marketing.phd_marketing_order_stage_waiting_for_approval")
        draft_id = self.env.ref("phd_marketing.phd_marketing_order_stage_draft")
        rejected_id = self.env.ref("phd_marketing.phd_marketing_order_stage_rejected")
        canceled_id = self.env.ref("phd_marketing.phd_marketing_order_stage_canceled")

        group_user_id = self.env.ref("phd_marketing.group_mko_user").id
        group_receivable_id = self.env.ref("phd_marketing.group_mko_receivable_user").id
        group_manager_id = self.env.ref("phd_marketing.group_mko_manager").id

        not_allowed_change = 'You are not allowed to change this order'
        #Receivable Group
        if group_receivable_id in self.env.user.groups_id.ids:
            if not self.is_approved:
                raise UserError(_(not_allowed_change))
            else:
                if self.stage_id != closed_id and self.canceled_id:
                    raise UserError(_(not_allowed_change))

        #Manager Group
        if group_manager_id in self.env.user.groups_id.ids:
            if self.stage_id == approval_id or self.stage_id == canceled_id or self.stage_id == rejected_id or self.stage_id == closed_id:
                self.is_approved = True
            else:
                self.is_approved = False

        #Marketing User Group
        if group_manager_id not in self.env.user.groups_id.ids and group_user_id in self.env.user.groups_id.ids:
            if self.is_approved:
                raise UserError(_(not_allowed_change))
            else:
                if self.stage_id != waiting_id and self.stage_id != draft_id and self.stage_id != canceled_id:
                    raise UserError(_(not_allowed_change))

        if self.stage_id == closed_id:
            if self.order_line.filtered(lambda l: l.quantity <= 0):
                raise UserError(_("Quantity must be greater than 0."))
            if not self.promo_id:
                raise UserError(_("The field 'Promo ID' is required, please complete it to close the Marketing Order."))
            elif not self.date_received:
                raise UserError(_("The field 'Date Received' is required, please complete it to close the Marketing Order."))

    def write(self, vals):
        canceled_id = self.env.ref("phd_marketing.phd_marketing_order_stage_canceled")
        if vals.get('stage_id'):
            newstage = self.env['phd.mko.stage'].browse(vals['stage_id'])
            for mko in self:
                if mko.stage_id and ((newstage.sequence, newstage.id) > (mko.stage_id.sequence, mko.stage_id.id)):
                    if vals.get('stage_id') != canceled_id.id and not self.is_approved:
                        if not mko.allow_change_stage:
                            raise UserError(_('You cannot change the stage, as approvals are still required.'))
                        has_blocking_stages = self.env['phd.mko.stage'].search_count([
                            ('sequence', '>=', mko.stage_id.sequence),
                            ('sequence', '<=', newstage.sequence),
                            ('id', 'not in', [mko.stage_id.id] + [vals['stage_id']]),
                            ('is_blocking', '=', True)])
                        if has_blocking_stages:
                            raise UserError(_('You cannot change the stage, as approvals are required in the process.'))
                if mko.stage_id != newstage:
                    mko.approval_ids.filtered(lambda x: x.status != 'none').write({'is_closed': True})
                    mko.approval_ids.filtered(lambda x: x.status == 'none').unlink()
        mko = super(PHDMko, self).write(vals)
        if vals.get('stage_id'):
            self._create_approvals()
            if vals.get('stage_id') == self.env.ref("phd_marketing.phd_marketing_order_stage_waiting_for_approval").id:
                self._send_mail_to_manager()
        return mko

    def start_mko(self):
        self.write({'state': 'progress'})

    def action_see_attachments(self):
        domain = ['&', ('res_model', '=', 'phd.mko'), ('res_id', '=', self.id)]
        attachment_kanban_view = self.env.ref('phd_marketing.view_document_file_kanban_mko')
        attachment_form_view = self.env.ref('phd_marketing.view_document_file_form_mko')
        if self.is_approved:
            if self.env.ref("phd_marketing.group_mko_receivable_user").id in self.env.user.groups_id.ids:
                attachment_kanban_view = self.env.ref('phd_marketing.view_document_file_kanban_mko')
                attachment_form_view = self.env.ref('phd_marketing.view_document_file_mko_receivable_form')
            if self.env.ref("phd_marketing.group_mko_manager").id not in self.env.user.groups_id.ids and self.env.ref("phd_marketing.group_mko_user").id in self.env.user.groups_id.ids:
                attachment_kanban_view = self.env.ref('phd_marketing.view_document_file_mko_user_kanban')
                attachment_form_view = self.env.ref('phd_marketing.view_document_file_mko_user_form')
        return {
            'name': _('Attachments'),
            'domain': domain,
            'res_model': 'phd.mko.document',
            'type': 'ir.actions.act_window',
            'view_id': attachment_kanban_view.id,
            'views': [(attachment_kanban_view.id, 'kanban'), (attachment_form_view.id, 'form')],
            'view_mode': 'kanban,tree,form',
            'help': _('''<p class="o_view_nocontent_smiling_face">
                        Upload files to your product
                    </p><p>
                        Use this feature to store any files, like drawings or specifications.
                    </p>'''),
            'limit': 80,
            'context': "{'default_res_model': '%s','default_res_id': %d, 'default_company_id': %s}" %
                       ('phd.mko', self.id, self.company_id.id)
        }

    @api.constrains('promotion_period_from', 'promotion_period_to')
    def _check_date(self):
        today = date.today()
        for mko in self:
            if today > mko.promotion_period_from or today > mko.promotion_period_to:
                raise ValidationError(_('Promotion Period must be greater than today.'))
            elif mko.promotion_period_to < mko.promotion_period_from:
                raise ValidationError(_('Promotion from date must be earlier than promotion end date.'))

    def unlink(self):
        waiting_id = self.env.ref("phd_marketing.phd_marketing_order_stage_waiting_for_approval")
        draft_id = self.env.ref("phd_marketing.phd_marketing_order_stage_draft")
        if not self.env.ref("phd_marketing.group_mko_manager").id in self.env.user.groups_id.ids:
            if not self.is_approved and (self.stage_id == waiting_id or self.stage_id == draft_id):
                super(PHDMko, self).unlink()
            else:
                raise UserError(_('You are not allowed to delete this order.'))
        else:
            super(PHDMko, self).unlink()