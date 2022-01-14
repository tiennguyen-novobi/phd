# -*- coding: utf-8 -*-

from odoo import models, fields, api, _

INDIVIDUAL = 'individual'
SOLE_PROPRIETOR = 'sole_proprietor'
SINGLE_MEMBER_LLC = 'single_member_llc'
C_CORP = 'c_corp'
S_CORP = 's_corp'
PARTNERSHIP = 'partnership'
TRUST_ESTATE = 'trust_estate'
LLC_C = 'llc_c'
LLC_S = 'llc_s'
LLC_P = 'llc_p'

TRACK_1099_ENTITY = [INDIVIDUAL, SOLE_PROPRIETOR, SINGLE_MEMBER_LLC, PARTNERSHIP, LLC_P]


class ResPartner(models.Model):
    _inherit = 'res.partner'

    ###################################
    # FIELDS
    ###################################

    county = fields.Char('County')

    tax_classification = fields.Selection([
        (INDIVIDUAL, _('Individual')),
        (SOLE_PROPRIETOR, _('Sole Proprietor')),
        (SINGLE_MEMBER_LLC, _('Single Member LLC')),
        (C_CORP, _('C-Corporation')),
        (S_CORP, _('S-Corporation')),
        (PARTNERSHIP, _('Partnership')),
        (TRUST_ESTATE, _('Trust/Estate')),
        (LLC_C, 'LLC-C'),
        (LLC_S, 'LLC-S'),
        (LLC_P, 'LLC-P')], string='Tax Classification')

    is_amazon_distribution_center = fields.Boolean(string='Amazon Distribution Center', copy=False)
    e1_ship_to = fields.Char(string="E1 Ship To")

    ###################################
    # ONCHANGE FUNCTIONS
    ###################################
    @api.onchange('tax_classification')
    def _onchange_tax_classification(self):
        self.vendor_eligible_1099 = self.tax_classification in TRACK_1099_ENTITY

    @api.model
    def _address_fields(self):
        """Returns the list of address fields that are synced from the parent."""
        res = super(ResPartner, self)._address_fields()
        res += ('county',)
        return res
