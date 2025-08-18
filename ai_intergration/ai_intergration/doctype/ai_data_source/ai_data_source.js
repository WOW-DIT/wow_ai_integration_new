// Copyright (c) 2025, yazan sorour and contributors
// For license information, please see license.txt

frappe.ui.form.on('Ai Data Source', {
	// refresh: function(frm) {

	// }
	test_connection: function(frm) {
		if(!frm.doc.name.startsWith("new")) {
			if(!frm.doc.url) {
				frappe.throw("URL is required")
			}
			frappe.call({
				method: "ai_intergration.ai_intergration.doctype.ai_data_source.ai_data_source.verify_url",
				args: {
					url: frm.doc.url,
					auth_token: frm.doc.auth_token,
					auth_type: frm.doc.auth_type,
				},
				callback: function(res) {
					frm.set_value("verified", res.message)
					if(res.message) {
						frm.save()
					}
				}
			})
		}
	}
});
