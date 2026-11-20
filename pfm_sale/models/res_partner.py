# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class ResPartner(models.Model):
	_inherit = 'res.partner'

	agreement_ids = fields.One2many('customer.agreement', 'partner_id', string="Customer Agreements")
