// Copyright (c) 2025, yazan sorour and contributors
// For license information, please see license.txt

frappe.ui.form.on('Ai Chat', {
	refresh: function(frm) {
		// getModels(frm)
	},
	model: function(frm) {
		if(frm.doc.model) {
			frm.set_value("selected_model", frm.doc.model)
			frm.save()
		}
	},
	send: function(frm) {
		if(frm.doc.prompt && frm.doc.model){
			frappe.call({
				method: "ai_intergration.ai_intergration.api.ai_chat",
				args: {
					model: frm.doc.model,
					chat_id:frm.doc.name,
					new_message: {
						role: "user",
						content: frm.doc.prompt,
					}
				},
				callback: function(r) {
					console.log(r)
					frm.set_value('response', r.message);
				}
			})
		} else {
			if(!frm.doc.prompt) {
				frappe.throw("You can't send empty message");
			} else {
				frappe.throw("Please select a model.");
			}
		}
	}
});


function getModels(frm) {
	frappe.call({
		method: "ai_intergration.ai_intergration.api.get_models",
		callback: function(r) {
			const models = [""];
			let selected_model = ""

			for(const m of r.message) {
				models.push(m.model)
				if(frm.doc.selected_model == m.model) {
					selected_model = m.model
				}
			}

			const model = frm.fields_dict['model'];

			frm.set_df_property("model", "options", models.join("\n"));
			
			if(selected_model) {
				frm.set_value('model', selected_model);
			} else {
				frm.refresh_field('model');
			}
		}
	})
}