# -*- coding: utf-8 -*-

from odoo import api, fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    st_id = fields.Integer(string='ST id', copy=False)
    st_name = fields.Char(string="ST Name", copy=False)