# -*- coding: utf-8 -*-
from odoo import http

# class EditEffectiveDate(http.Controller):
#     @http.route('/edit_effective_date/edit_effective_date/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/edit_effective_date/edit_effective_date/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('edit_effective_date.listing', {
#             'root': '/edit_effective_date/edit_effective_date',
#             'objects': http.request.env['edit_effective_date.edit_effective_date'].search([]),
#         })

#     @http.route('/edit_effective_date/edit_effective_date/objects/<model("edit_effective_date.edit_effective_date"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('edit_effective_date.object', {
#             'object': obj
#         })