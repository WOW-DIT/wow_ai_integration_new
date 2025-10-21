# Copyright (c) 2025, yazan sorour and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
import requests
import json

class AiDataSource(Document):
	def validate(self):
		self.get_full_url()

	def get_full_url(self):
		base_url = self.url

		if self.method == "POST":
			return base_url

		filters = []
		for filter in self.filters:
			example = filter.example if filter.example else filter.field_name
			filters.append(f"{filter.field_name}={{{example}}}")

		full_url = f"{base_url}?{'&'.join(filters)}"

		return full_url


	def get_json_body(self):
		body = {}
		if self.method == "GET":
			return body
		
		for field in self.filters:
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
def verify_url(url, method="GET", auth_token=None, auth_type=None, params=None):
	try:
		if params:
			params = json.loads(params)
		else:
			params = {}

		headers = {
			"Content-Type": "application/json"
		}

		if auth_type and auth_token:
			headers["Authorization"] = f"{auth_type} {auth_token}"

		if method == "GET":
			body = {"test": True}
			for param in params:
				body[param] = param

			response = requests.get(url, headers=headers, params=body, timeout=5)

		elif method == "POST":
			body = {"test": True}
			for param in params:
				body[param] = param

			response = requests.post(url, headers=headers, json=body, timeout=5)

		else:
			return {"success": False, "error": f"Unsupported method: {method}"}
		
		return {"success": response.status_code == 200, "status_code": response.status_code}


	except Exception as e:
		return {"success": False, "error": str(e)}