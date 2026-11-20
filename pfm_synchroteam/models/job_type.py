# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class JobType(models.Model):
	_name = 'job.type'
	_description = 'Job Types'

	name = fields.Char('Name')
	st_job_type_id = fields.Integer('ST Job Type ID')
	sent_to_st = fields.Boolean('Sent to ST', default=True)
