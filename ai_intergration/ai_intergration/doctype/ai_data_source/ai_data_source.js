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
			let params = [];
			for(let i = 0; i < frm.doc.filters.length; i++) {
				const param = frm.doc.filters[i];
				params.push(param.field_name)
			}

			console.log(params)

			frappe.call({
				method: "ai_intergration.ai_intergration.doctype.ai_data_source.ai_data_source.verify_url",
				args: {
					url: frm.doc.url,
					method: frm.doc.method,
					auth_token: frm.doc.auth_token,
					auth_type: frm.doc.auth_type,
					params: params,
				},
				callback: function(res) {
					console.log(res.message)
					frm.set_value("verified", res.message.success)
					if(res.message.success) {
						frm.save()
					}
				}
			})
		}
	}
});
