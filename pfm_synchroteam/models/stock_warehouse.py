# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class Warehouse(models.Model):
	_inherit = 'stock.warehouse'

	one_step_location = fields.Many2one('stock.location.route', string='One Step Location Route')
	two_step_location = fields.Many2one('stock.location.route', string='Two Step Location')

	def get_one_step_dict(self):
		routes = []
		one_step_route ={
			'delivery_route_id': {
					'routing_key': 'ship_only',
					'depends': ['delivery_steps'],
					'route_update_values': {
						'name': self._format_routename(route_type='ship_only')
					},
					'route_create_values': {
						'product_categ_selectable': True,
						'warehouse_selectable': True,
						'product_selectable': False,
						'company_id': self.company_id.id,
						'sequence': 10,
						'sale_selectable': True,
					},
					'rules_values': {
						'active': True,
					}
				},

			}
		routes.append(one_step_route)
		two_step_route ={
			'delivery_route_id': {
					'routing_key': 'pick_ship',
					'depends': ['delivery_steps'],
					'route_update_values': {
						'name': self._format_routename(route_type='pick_ship')
					},
					'route_create_values': {
						'product_categ_selectable': True,
						'warehouse_selectable': True,
						'product_selectable': False,
						'company_id': self.company_id.id,
						'sequence': 10,
						'sale_selectable': True,
					},
					'rules_values': {
						'active': True,
					}
				},

			}

		routes.append(two_step_route)
		return routes

	def _create_or_update_route(self):
		res = super(Warehouse, self)._create_or_update_route()
		rules_dict = self.get_rules_dict()
		route_model = self.env['stock.location.route']
		for route in self.get_one_step_dict():
			for route_field, route_data in route.items():
				routing_key = route_data.get('routing_key')
				rules = rules_dict[self.id][routing_key]
				if route_data['route_update_values']:
					name = route_data['route_update_values']['name']
				else:
					name = ''
				if routing_key == 'ship_only':
					route_job = route_model.search([
						('name', 'like', name), ('sale_selectable', '=', True)
					])
					if route_job:
						self.one_step_location = route_job
					else:
						route_data['route_create_values'].update(route_data['route_update_values'])
						route_job = self.env['stock.location.route'].create(route_data['route_create_values'])
						self.one_step_location = route_job
				if routing_key == 'pick_ship':
					route_job = route_model.search([
						('name', 'like', name), ('sale_selectable', '=', True)
					])
					if route_job:
						self.two_step_location = route_job
					else:
						route_data['route_create_values'].update(route_data['route_update_values'])
						route_job = self.env['stock.location.route'].create(route_data['route_create_values'])
						self.two_step_location = route_job


				if 'rules_values' in route_data:
					route_data['rules_values'].update({'route_id': route_job.id})
				else:
					route_data['rules_values'] = {'route_id': route_job.id}
				rules_list = self._get_rule_values(
					rules, values=route_data['rules_values'])
				for rule_vals in rules_list:
					existing_rule = self.env['stock.rule'].search([
						('picking_type_id', '=', rule_vals['picking_type_id']),
						('location_src_id', '=', rule_vals['location_src_id']),
						('location_id', '=', rule_vals['location_id']),
						('route_id', '=', rule_vals['route_id']),
						('action', '=', rule_vals['action']),
						('active', '=', True),
					])
					if not existing_rule:
						self.env['stock.rule'].create(rule_vals)
					else:
						existing_rule.write({'active': True})
			
		return res
