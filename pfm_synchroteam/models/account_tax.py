# -*- coding: utf-8 -*-


from odoo import api, fields, models, _


class AccountTax(models.Model):
	_inherit = 'account.tax'

	st_tax_id = fields.Integer('ST Tax ID')
