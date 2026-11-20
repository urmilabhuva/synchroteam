# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class ProductTemplate(models.Model):
	_inherit = 'product.template'

	need_to_perform_task = fields.Boolean('Need to be performed before Job', default=False)
