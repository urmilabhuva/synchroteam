# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class MrpProduction(models.Model):
	_inherit = 'mrp.production'

	job_id = fields.Many2one('job.job', string='Job')
