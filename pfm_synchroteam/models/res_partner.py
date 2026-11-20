# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class ResPartner(models.Model):
	_inherit = 'res.partner'

	st_partner_id = fields.Integer('ST Partner ID', copy=False)
	job_ids = fields.One2many('job.job', 'site_id', string='Jobs')
