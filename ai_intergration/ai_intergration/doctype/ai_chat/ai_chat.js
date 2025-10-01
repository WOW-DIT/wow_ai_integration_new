// Copyright (c) 2025, yazan sorour and contributors
// For license information, please see license.txt

frappe.ui.form.on('Ai Chat', {
	refresh: function(frm) {
		if(!frm.doc.name.startsWith("new")) {
			frm.add_custom_button("Go Live", () => {
				startLiveSession(frm);
			}).addClass("btn-primary");
		}

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


function startLiveSession(frm) {
	frappe.call({
		method: "whatsapp_integration.whatsapp_integration.doctype.whatsapp_live_chat.whatsapp_live_chat.start_live_session",
		args: {
			chat_id: frm.doc.name
		},
		callback: function(r) {
			if(r.message.success) {
				location.href = r.message.url;
			}
		}
	})
}


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