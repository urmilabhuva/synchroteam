# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class PurchaseOrder(models.Model):
	_inherit = 'purchase.order'

	job_id = fields.Many2one('job.job', string='Job')