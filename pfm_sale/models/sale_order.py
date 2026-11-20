# -*- coding: utf-8 -*-

from odoo import api, fields, models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    agreement_id = fields.Many2one('customer.agreement', string='Customer Agreement')
    is_warranty_order = fields.Boolean('Is Warranty Order', compute='compute_is_warranty_order')
    repair_order = fields.Boolean(string="Repair Order", copy=False)
    partner_invoice_id = fields.Many2one(states={'draft': [('readonly', False)], 'sent': [('readonly', False)], 'sale': [('readonly', False)]})

    @api.onchange('agreement_id')
    def onchange_agreement(self):
        ref = self.agreement_id.po_number
        if ref:
            self.client_order_ref = ref

    @api.onchange('operating_unit_id')
    def _onchange_operating_unit(self):
        pricelist = self.env['product.pricelist'].search([('operating_unit_id', '=', self.operating_unit_id.id)], limit=1)
        if pricelist:
            self.pricelist_id = pricelist

    def compute_is_warranty_order(self):
        for order in self:
            warranty_lines = order.order_line.filtered(lambda p: p.warranty)
            if len(warranty_lines) > 0:
                order.is_warranty_order = True
            else:
                order.is_warranty_order = False

    def explode_bom(self):
        for line in self.order_line:
            line.explode_bom()
