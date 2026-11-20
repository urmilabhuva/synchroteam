# -*- coding: utf-8 -*-

from odoo import api, fields, models


class ProductPricelist(models.Model):
    _inherit = 'product.pricelist'

    operating_unit_id = fields.Many2one(
        comodel_name='operating.unit',
        string='Operating Unit',
    )