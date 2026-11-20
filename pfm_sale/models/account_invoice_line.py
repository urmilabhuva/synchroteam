# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class AccountMoveLine(models.Model):
	_inherit = 'account.move.line'

	warranty = fields.Boolean(string="Warranty", copy=False, default=False)
