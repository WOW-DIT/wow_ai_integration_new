import frappe
import requests
import json
import re
import openai
from openai import OpenAI
from datetime import datetime
from io import BytesIO
from docx import Document
import pandas as pd
from ollama import Client
from frappe.utils.file_manager import save_file
from frappe.utils import get_url


AI_SYSTEM_PROMPT = """
Today's Date: {DATE}
--------------
Response Format:
--------------
THE MOST IMPORTANT RULE: return a pure plain JSON string (text not code) containing these fixed main fields:
1- type:
  A- 'question' ONLY if more information is needed.
  B- 'request' ONLY if the user provided some information and you need to get more information from the server or database, example: car model, and you need to fetch more data to availability, or answer some questions.
  C- 'answer' ONLY if no more information is needed from the user side, then you will do an action like making an appointment, and you will do a post request using the JSON template.

2- response: 
  A- if the 'type' = 'question', respond to the user to provide more information.
  B- if the 'type' = 'request', then provide some waiting message to the user based on the context.
  C- if the 'type' = 'answer', confirmation message with utilities such as order or transaction id, date, etc... .

3- client_number: VERY IMPORTANT to be able to respond to the user.

4- request: ONLY If the 'type' = 'request'. The (Request Template). This is a dynamic nested JSON object after replacing the variables or placeholders.

5- json_body: ONLY If the 'type' = 'answer'. The (JSON template) after replacing with new values.

{RESPONSE_FIELDS}

--------------
Instructions:
--------------
{INSTRUCTIONS}
--------------
Request Types
--------------
{REQUEST_TYPES}
--------------
Context Data:
--------------
{CONTEXT_INSTS}

{CONTEXT}
--------------
JSON template:
--------------
{JSON}
--------------
Completion:
--------------
{COMPLETION}
--------------

Above, the Completion did not satisfy the constraints given in the Instructions.
Error:
--------------
{ERROR}
--------------

Please try again. Please only respond with an answer that satisfies the constraints laid out in the Instructions:
"""

@frappe.whitelist()
def get_models():
    settings = frappe.get_doc("Ai Settings", "Ai Settings")
    url = f"{settings.base_url}/tags"

    response = requests.get(url)

    if response.status_code == 200:
        models = []
        for m in response.json()["models"]:
            models.append({"model": m["model"]})

        return models

    frappe.throw("Couldn't fetch LLMs")


@frappe.whitelist()
def get_gpt_models():
    try:
        # cred_id = frappe.get_value("Client Credentials", {"user": frappe.session.user})
        # if cred_id:
            creds = frappe.get_doc("Client Credentials", "Main")
            api_key = creds.get_password("api_key")

            if api_key:
                models = []
                ai_client = OpenAI(api_key=api_key)
                response = ai_client.models.list()

                for model in response.data:
                    models.append(model.id)

                return models
                
    except Exception as e:
        save_response_log(str(e), "001", "001", True)
        
        frappe.throw("invalid credentials")


def save_response_log(body, from_number, to_number, is_error=False):
    log = frappe.new_doc("WhatsApp Logs")
    log.from_number = from_number
    log.to_number = to_number
    log.method = "Sent"
    log.timestamp = datetime.now()
    log.body = body
    log.is_error = is_error
    log.save(ignore_permissions=True)


def get_ai_requests_types(source_template):
    source_template = frappe.get_doc("Ai Data Source Template", source_template)
    sources = source_template.data_source_table
    strings = []
    for s in sources:
        src = frappe.get_doc("Ai Data Source", s.source)
        
        strings.append(f"""{{
        "when": "{src.when.strip() if src.when else ""}",
        "method": "{src.method.strip()}",
        "url": "{src.get_full_url()}",
        "body": {src.get_json_body()},
        "auth_type": "{src.auth_type.strip() if src.auth_type else ""}",
        "auth_token": "{src.auth_token.strip() if src.auth_token else ""}",
        "instructions": "{src.instructions.strip() if src.instructions else ""}"
    }}""")

    requests = ",\n".join(strings)

    save_response_log(
        str(requests),
        "-1-1-1-1-1",
        "-1-1-1-1-1"
    )
    return requests


def get_external_links(links_template):
    links_template = frappe.get_doc("Ai External Link Template", links_template)
    links = links_template.links

    sources = []
    for l in links:
        src = frappe.get_doc("Ai External Link", l.source)
        sources.append({
            "url": src.url.strip(),
            "instructions": src.instructions.strip()
        })

    return sources


def web_search(context, chat, links):
    for link in links:
        url = link.get("url")
        response = requests.get(url)

        if response.status_code == 200:
            page_content = response.text
            instructions = link.get("instructions")


def save_message(chat, role, content, message_text: str=None, image: dict=None, message_type="text", timestamp: datetime=datetime.now()):
    message = frappe.new_doc("Ai Message")
    message.chat = chat
    message.type = message_type
    message.role = role
    message.content = content
    message.message_text = message_text
    message.timestamp = timestamp
    message.insert(ignore_permissions=True)

    if image:
        image_content = image.get("content")
        image_name = image.get("name")

        filedoc = save_file(
            fname=image_name,
            content=image_content.getvalue(),
            dt="Ai Message",
            dn=message.name,
            is_private=0
        )

        message.image = filedoc.file_url
        message.save(ignore_permissions=True)

    return message


def confirm_response(message_id):
    message = frappe.get_doc("Ai Message", message_id)
    message.responded_to = 1
    message.save(ignore_permissions=True)


@frappe.whitelist(allow_guest=True)
def ai_chat(
    model,
    chat_id,
    message_type,
    new_message,
    plain_text: str=None,
    image: dict=None,
    to_number=None,
    timestamp: datetime=datetime.now(),
    stream=False,
):
    try:
        if not isinstance(new_message, dict):
            new_message = json.loads(new_message)

        chat = frappe.get_doc("Ai Chat", chat_id)
        context = frappe.get_doc("AI Agent", chat.context)

        is_live = chat.is_live
        
        user_message = save_message(
            chat=chat.name,
            role=new_message["role"],
            content=new_message["content"],
            message_text=plain_text,
            image=image,
            message_type=message_type,
            timestamp=timestamp,
        )

        ## Add image to prompt
        if image:
            image_url = f"{get_url()}{user_message.image}"
            text = new_message["content"]
            new_message["content"] = [
                {"type": "input_text", "text": text},
                {"type": "input_image", "image_url": image_url}
            ]

        chat.append(
            "messages",
            {"message": user_message.name}
        )

        if is_live:
            chat.save(ignore_permissions=True)
            confirm_response(user_message.name)
            frappe.db.commit()
            return {"is_live": is_live, "response": plain_text}
        

        messages = get_current_messages(chat_id, context)
        messages.append(new_message)
            
        if context.override_model == 1:
            ai_response = ask_gpt_ai(model, context, messages, to_number)
        elif context.default_model == 1:
            ai_response = ask_ollama_ai(model, messages, to_number)
        else:
            ai_response = ask_local_ai(model, messages, to_number)

        role = ai_response.get("role")
        content = ai_response.get("content")
        content = content.replace("```json", "").replace("```", "")

        data = json.loads(content)

        ai_message = data.get("response")

        resp_message = save_message(
            chat=chat,
            role=role,
            content=content,
            message_text=ai_message,
            timestamp=timestamp,
        )

        chat.append(
            "messages",
            {"message": resp_message.name}
        )

        response_type = data.get("type")

        extra_data = None
        if response_type == "request" and context.integration == 1 and context.source_type == "Template":
            ## I want to get data from API and then embed it in the system prmopt or
            ## send a new hidden user message to the llm

            request_data = data.get("request")

            if request_data:
                url = request_data.get("url")
                auth_type = request_data.get("auth_type")
                auth_token = request_data.get("auth_token")

                query_data = get_online_data(url, auth_type, auth_token)
                if query_data:
                    messages.append({
                        "role": "system",
                        "content": str(query_data),
                    })

                    if context.override_model == 1:
                        ai_response = ask_gpt_ai(model, context, messages, to_number)
                    elif context.default_model == 1:
                        ai_response = ask_ollama_ai(model, messages, to_number)
                    else:
                        ai_response = ask_local_ai(model, messages, to_number)

                    role = ai_response.get("role")
                    content = ai_response.get("content")

                    data = json.loads(content)

                    ai_message = data.get("response")

                    message = save_message(
                        chat=chat,
                        role="system",
                        content=str(query_data),
                        message_text="",
                        timestamp=timestamp,
                    )

                    chat.append(
                        "messages",
                        {"message": message.name}
                    )

                    message = save_message(
                        chat=chat,
                        role=role,
                        content=content,
                        message_text=ai_message,
                        timestamp=timestamp,
                    )

                    chat.append(
                        "messages",
                        {"message": message.name}
                    )

        if response_type == "answer" and context.integration == 1 and context.webhook_uri:
            save_response_log(str(data), "PAPAPAPAPAPAP", "PAPAPAPAPAPAP")

            json_body = data.get("json_body")
            extra_data = post_to_webhook(context, json_body)
        
        chat.save(ignore_permissions=True)
        confirm_response(user_message.name)
        frappe.db.commit()
        return {"is_live": is_live, "response": ai_message}
    
    except Exception as e:
        save_response_log(str(e), "AAAAAAAA", "AAAAAAAAAAAAA")
        return None


def speech_to_text(model: str, client_credentials, file_name: str, audio_data: BytesIO):
    try:
        creds = frappe.get_doc("Client Credentials", client_credentials)
        api_key = creds.get_password("api_key")

        ai_client = OpenAI(api_key=api_key)

        with audio_data as f:
            f.name = file_name
            
            transcription = ai_client.audio.transcriptions.create(
                model=model, 
                file=f,
            )

        return transcription.text        
    except Exception as e:
        return str(e)


def ask_local_ai(model, messages, to_number, stream=False):
    try:
        settings = frappe.get_doc("Ai Settings", "Ai Settings")
        url = f"{settings.base_url}/chat"
        body = {
            "model": model,
            "messages": messages,
            "stream": stream,
        }
        response = requests.post(url, json=body)

        if response.status_code == 200:
            res_message = response.json()["message"]
            role = res_message["role"]
            content = res_message["content"]
            content = re.sub(r'[\x00-\x1F\x7F]', '', content)

            return {
                "role": role,
                "content": content,
            }
    
    except Exception as e:
        save_response_log(
            str(e),
            "Local",
            to_number,
        )


def ask_ollama_ai(model, messages, to_number, stream=False):
    try:
        client = Client(
            host="https://ollama.com",
            headers={'Authorization': '4b78847708a1463297acb80a08716843.SBNnfMMNHiqn8RgfzSIj4E6_'}
        )

        resp = client.chat(model=model, messages=messages, stream=False)
        msg = resp.get("message") or {}

        return {"role": msg.get("role", "assistant"), "content": msg.get("content", "")}
    
    except Exception as e:
        save_response_log(
            str(e),
            "Default",
            to_number,
        )


def ask_gpt_ai(model, context, messages, to_number, stream=False):
    try:
        creds = frappe.get_doc("Client Credentials", context.client_credentials)
        api_key = creds.get_password("api_key")

        if api_key:
            ai_client = OpenAI(api_key=api_key)

            response = ai_client.responses.create(
                model=model,
                input=messages,
                store=False,
            )

            role = response.output[0].role
            content = response.output[0].content[0].text

            return {
                "role": role,
                "content": content,
            }
    
    except openai.OpenAIError as e:
        save_response_log(str(e), "GPT", to_number, True)

    except Exception as e:
        save_response_log(str(e), "GPT", to_number, True)


def get_online_data(url, auth_type=None, auth_token=None, timeout=30):
    try:
        headers = {
            "Accept-Content": "application/json"
        }
        
        if (auth_type and auth_token) and auth_type in ["Bearer", "Basic", "Token"]:
            headers["Authorization"] = f"{auth_type} {auth_token}"

        response = requests.get(url, headers=headers, timeout=timeout)
        if response.status_code == 200:
            return response.json()
        
        return None
    except:
        return None
    

def post_to_webhook(context, json_body):
    url = context.webhook_uri
    try:
        if isinstance(json_body, str):
            payload = json.loads(json_body)
        elif isinstance(json_body, dict):
            payload = json_body
        else:
            return None
        
        headers = {}

        if context.auth_token:
            headers["Authorization"] = context.auth_token

        tries = 3
        while tries > 0:
            response = requests.post(url=url, json=payload, headers=headers, timeout=15)
            if response.status_code != 200:
                tries -= 1
            else:
                return response.json()
    except:
        return None
    


@frappe.whitelist()
def get_current_messages(chat_id, context) -> list:
    def get_remote_context(url):
        tries = 3
        while tries > 0:
            response = requests.get(url, timeout=30)

            if response.status_code == 200:
                return response.json()
            else:
                tries -= 1

        return ""

    def get_file_context(file_url):
        # Download file
        response = requests.get(file_url)
        response.raise_for_status()
        file_data = BytesIO(response.content)

        # Detect file type by extension
        file_url_lower = file_url.lower()
        text_content = ""

        if file_url_lower.endswith(".docx"):
            # Read DOCX
            doc = Document(file_data)
            text_content = "\n".join([p.text for p in doc.paragraphs if p.text.strip()])

        elif file_url_lower.endswith(".txt"):
            # Read plain text
            text_content = file_data.read().decode("utf-8", errors="ignore")

        elif file_url_lower.endswith(".csv"):
            # Read CSV
            df = pd.read_csv(file_data)
            text_content = df.to_string(index=False)

        elif file_url_lower.endswith((".xlsx", ".xls")):
            # Read Excel
            df = pd.read_excel(file_data)
            text_content = df.to_string(index=False)

        else:
            raise ValueError("Unsupported file type")

        return text_content.strip()
    
    messageDocs = frappe.get_all(
        "Ai Messages Table",
        filters={"parent": chat_id},
        fields=["role", "content"],
        order_by="idx",
        limit=0,
    )

    messages = []

    content = AI_SYSTEM_PROMPT
    content = content.replace("{DATE}", datetime.now().strftime("%Y-%m-%d"))

    response_fields = context.response_fields if context.response_fields else ""
    content = content.replace("{RESPONSE_FIELDS}", response_fields)

    if context.integration == 1 and context.source_type:
        if context.source_type == "Link":
            remote_context = get_remote_context(context.source_link)
        elif context.source_type == "File":
            remote_context = get_file_context(context.sourec_file)
        elif context.source_type == "Text":
            remote_context = context.source_text
        else:
            remote_context = ""

        if context.source_type == "Template":
            content = content.replace("{REQUEST_TYPES}", get_ai_requests_types(context.source_template))
        else:
            content = content.replace("{CONTEXT}", str(remote_context))

    content = content.replace("{INSTRUCTIONS}", context.system_prompt or "")
    content = content.replace("{JSON}", context.json_template or "")
    content = content.replace("{COMPLETION}", context.on_completion or "")
    content = content.replace("{ERROR}", context.on_error or "")
    
    messages.append({
        "role": "system",
        "content": content,
    })

    for m in messageDocs:
        role = m["role"] if (m["role"] == "assistant" or m["role"] == "user") else "assistant"
        messages.append({
            "role": role,
            "content": m["content"],
        })
    return messages


@frappe.whitelist()
def getAIResponse(mctName, docName):
    """
    Generate a response from OpenAI's chat model based on a AI Agent and a target document.

    This function retrieves a AI Agent and the relevant target document from Frappe.
    It formats the text according to the specified fields and sends a prompt to the OpenAI API 
    to generate a response based on the provided system prompt and user prompt.

    Parameters:
        mctName (str): The name of the AI Agent from which to retrieve formatting and prompts.
        docName (str): The name of the target document from which to retrieve field values.

    Returns:
        str: The content of the AI-generated response.

    Raises:
        frappe.ValidationError: If there is an issue with account credentials while calling the OpenAI API.
    """
    mctDoc = frappe.get_doc('AI Agent', mctName)
    targetDocument = frappe.get_doc(mctDoc.target_doctype, docName)

    formattedText = ''

    for row in mctDoc.text_format:
        ## Concat table row fields
        if row.linked_field_type == "Table":
            msg = (row.before if row.before is not None else "")
            formattedText += msg + '\n'

            # doct = frappe.get_doc("DocType", row.target_doctype)
            row_children = frappe.get_all(
                "RAG Children Table",
                filters={"parent": mctDoc.name, "reference_type": row.target_doctype},
                fields=["content"],
            )

            for i, child in enumerate(row_children):
                child_fields = str(child.content).split(",")
                table_items = getattr(targetDocument, row.linked_field_name)

                for ti in table_items:

                    content = ""
                    for f in child_fields:
                        content += f". {getattr(ti, f)}"

                    ch_row = f"{i}- {content}"
                    formattedText += ch_row + '\n'

        else:
            msg = (row.before if row.before is not None else "") + " " + str(getattr(targetDocument, row.field_name)) + " " + (row.after if row.after is not None else "")
            formattedText += msg + '\n'

    """
    Search for records by selected references
    """
    for target in mctDoc.reference_targets:
        alias = "fi"
        sql_fields = ", ".join(f"{alias}.{field.strip()}" for field in target.fields.split(","))
        columns = "row_number|" + "|".join(f"{alias}.{field.strip()}" for field in target.fields.split(","))

        formattedText += f"{target.before}\n"
        formattedText += f"{target.reference} columns: {columns.replace(f'{alias}.', '')}\n"
        formattedText += f"{target.reference} rows:\n"

        if target.filter_fields != "" and target.filter_fields is not None and len(target.filter_fields.split(",")) > 0 and len(target.filter_fields.split(",")) == len(target.fields_values.split(",")):
            filter_fields = target.filter_fields.split(",")
            values = target.fields_values.split(",")
            sql_filters = []
            
            for i, f in enumerate(filter_fields):
                field = filter_fields[i].strip()
                value = values[i].strip()

                sql_filters.append(f"{alias}.{field} LIKE '%{value}%'")

            sql_filters = ", ".join(sql_filters)
            sql_filters = f"""WHERE {sql_filters}"""
        else:
            sql_filters = ""

        query = f"""
            SELECT {sql_fields}
            FROM `tab{target.reference}` AS {alias} {sql_filters};
        """

        target_items = frappe.db.sql(query, as_dict=True)

        for i, item in enumerate(target_items):
            item_row = f"{i+1}|{'|'.join(str(value) for value in item.values())}\n"

            formattedText += item_row

        formattedText += "\n"

    formattedText += '\n' + mctDoc.user_prompt

    systemPrompt = mctDoc.system_prompt
    userPrompt = formattedText

    # return userPrompt

    try:
        settings = frappe.get_doc("Ai Settings", "Ai Settings")
        url = f"{settings.base_url}/chat"
        messages=[
            {"role": "system", "content": systemPrompt},
            {"role": "user", "content": userPrompt}
        ]
        data = {
            "model": mctDoc.selected_model,
            "messages": messages,
            "stream": False,
        }
        response = requests.post(url, json=data)

        if response.status_code == 200:
            return response.json()["message"]["content"]
        else:
            frappe.throw("ERROR: response failed")

    except Exception as e:
        frappe.throw(f"Error: {e}")
