# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    incoming_repair_lot_id = fields.Many2one('stock.production.lot', string='Serial Number in', copy=False)
    outgoing_repair_lot_id = fields.Many2one('stock.production.lot', string='Serial Number out', copy=False)
    warranty = fields.Boolean(string="Warranty", copy=False, default=False)

    def explode_bom(self):
        for line in self:
            if line.display_type not in ['line_section', 'line_note']:
                product = line.product_id
                boms = line.product_id.bom_ids
                line_list = []
                line_list.append(_('%s' % (line.product_id.variant_description_sale)))
                line_list.append(_('Additional Parts:'))
                for bom in boms:
                    for bomline in bom.bom_line_ids:
                        if not bomline._skip_bom_line(product):
                            if bomline.bom_product_template_attribute_value_ids:
                                for attribute in bomline.bom_product_template_attribute_value_ids:
                                    if attribute in product.product_template_attribute_value_ids:
                                        attribute_value =  self.env['product.template.attribute.value'].search([('product_attribute_value_id', '=', attribute.id), ('product_tmpl_id', '=', product.product_tmpl_id.id)], limit=1)
                                        line_list.append(_('  %s x - %s' % (bomline.product_qty, bomline.product_id.name)))
                line.name = '\n'.join(line_list)

    @api.onchange('warranty')
    def onchange_warranty(self):
        for line in self:
            if line.warranty is True:
                line.discount = 100
            else:
                line.discount = 0
                

    def _prepare_invoice_line(self, **optional_values):
        res = super(SaleOrderLine, self)._prepare_invoice_line()
        res.update({
            'warranty': self.warranty,
        })
        return res
    
    
