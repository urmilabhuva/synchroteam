# -*- coding: utf-8 -*-

from odoo import api, fields, models, _

class JobLog(models.Model):
	_name = 'synchroteam.log'
	_description = "Job Log"

	record_id = fields.Integer('Record ID')
	record_obj = fields.Many2one('ir.model')
	datetime = fields.Datetime('Datetime Call')
	record_method = fields.Char('Method Name')
	request_url = fields.Char('Request Url')
