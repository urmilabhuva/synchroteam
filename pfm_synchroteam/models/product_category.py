# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class ProductCategory(models.Model):
    _inherit = "product.category"

    st_category_id = fields.Integer('ST Part Category ID')

