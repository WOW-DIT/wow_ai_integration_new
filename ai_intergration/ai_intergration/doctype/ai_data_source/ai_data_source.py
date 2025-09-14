# Copyright (c) 2025, yazan sorour and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
import requests

class AiDataSource(Document):
	def validate(self):
		self.get_full_url()

	def get_full_url(self):
		base_url = self.url

		filters = []
		for filter in self.filters:
			example = filter.example if filter.example else filter.field_name
			filters.append(f"{filter.field_name}={{{example}}}")

		full_url = f"{base_url}?{'&'.join(filters)}"

		return full_url


	def get_json_body(self):
		body = {}
		for field in self.fields:
			example = field.example if field.example else field.field_name
			body[field.field_name] = example

		return body


	def fetch_data(self):
		try:
			url = self.get_full_url()
			headers = {
				"Content-Type": "application/json"
			}
			if self.auth_type and self.auth_token:
				headers["Authorization"] = f"{self.auth_type} {self.auth_token}"

			response = requests.get(url, headers=headers)

			if response.status_code == 200:
				return response.json()
			else:
				return {"error_message": self.error_message}
			
		except:
			return {"error_message": self.error_message}
	



@frappe.whitelist()
def verify_url(url, auth_token=None, auth_type=None):
	try:
		headers = {
			"Content-Type": "application/json"
		}
		if auth_type and auth_token:
			headers["Authorization"] = f"{auth_type} {auth_token}"

		response = requests.get(url, headers=headers, timeout=5)
	
		return response.status_code == 200
	
	except:
		return False
	
	
