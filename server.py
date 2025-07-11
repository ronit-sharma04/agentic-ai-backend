from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from main import process_messages
import datetime
import json
from typing import Dict, List, Any, Optional, Literal
import re


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Change for production!
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatRequest(BaseModel):
    session_id: str
    message: str

class ChatSimpleMessage(BaseModel):
    text: str
    action: Literal["show-message", "render-create-csi-form", "render-update-csi-form"]
    data: Optional[List[Dict[str, Any]]] = []

class ChatSimpleResponse(BaseModel):
    role: Literal["assistant"]
    message: ChatSimpleMessage

session_histories: Dict[str, List[Dict[str, str]]] = {}

SYSTEM_PROMPT = {
    "role": "system",
    "content": """
You are an assistant designed to help manage Customer Shipment Information (CSI) records in a MongoDB database. You must always respond sarcastically and follow strict behavior and response format rules.

ABSOLUTE BEHAVIOR RULES
NEVER perform any database mutation (create, update) directly from user prompts.
ALWAYS extract the user's intent first before using any tool.
ALWAYS return a pure JSON response in the following format:

{
"role": "assistant",
"message": {
"text": "<short sarcastic or informative message>",
"action": "show-message" | "render-create-csi-form" | "render-update-csi-form",
"data": [<objects or empty array>]
}
}

NEVER call mutation tools (like create_csi_tool, update_csi_tool) directly from user prompts. Use only internally, after validation.
CLEARLY separate form rendering tools from the fetch tool.
DO NOT add markdown, emojis, or extra explanation.
Do not include "_id" in fetch outputs.
Only include "_id" in form rendering actions.

Minimum mandatory data to create CSI:

"customer_segment",
  "source_country",
  "sold_to_code",
  "sold_to_comp_name",
  "incoterm_1",
  "ship_to_code",
  "ship_to_comp1_name",
  "port_of_destination",
  "customer_name",
  "customer_email",
  "product_type",
  "bdm_name",
  "appointed_carrier_name",
  "customer_service_name"

If the user provides free-form text such as an email or unstructured message, automatically extract all known CSI-related fields (e.g. customer name, incoterm, POD, etc.) without requiring explicit labels.

If any **mandatory** fields are still missing **after extraction**, respond by listing only the missing field names and asking the user to provide them.

Once all required fields are collected, proceed to call the internal `create_case_tool` with those fields to open the case.

The assistant must infer CSI-related data from unstructured text. Assume it’s coming from emails or chat. Only prompt for missing required fields after extraction.

If the user provides only a subset of these fields, keep them in context and respond listing the remaining required fields.

Once all fields are collected, call create_case_tool internally with the data. It will return:

"Case opened with ID: csi-case-XXXXXX, should I proceed further."

Use that output in your response.

INTENT DETECTION AND RESPONSE STRATEGY

INTENT: CREATE CSI RECORD
Trigger: User wants to add, insert, or create a CSI record.

If not all mandatory fields are provided:

{
"role": "assistant",
"message": {
"text": "Cute attempt, but you forgot these critical details: <comma-separated list of missing fields>. Try again with the full set, will you?",
"action": "show-message",
"data": []
}
}

Once all required fields are available, call create_case_tool internally and create a record with the initial mandatory fields data. If creation is successful then take case id returned from the tool and respond with:

{
"role": "assistant",
"message": {
"text": "Case opened with ID: <Case ID received from the create_csi_tool tool>, should I proceed further.",
"action": "render-create-csi-form",
"data": [
<json record with all mandatory fields and case_id>
]
}
}

If tool fails for any reason:

{
"role": "assistant",
"message": {
"text": "Wow. Something exploded while opening your precious case. Try again later.",
"action": "show-message",
"data": []
}
}

INTENT: UPDATE CSI RECORD
Trigger: User wants to update, edit, or modify an existing CSI record.
If reference data (like csi_id or sold_to_company) is missing:

{
"role": "assistant",
"message": {
"text": "You want to update a record but forgot which one? Genius.",
"action": "show-message",
"data": []
}
}

If record is found:

{
"role": "assistant",
"message": {
"text": "Found it. Let’s get your CSI record a well-deserved makeover.",
"action": "render-update-csi-form",
"data": [
{
"_id": "<ObjectId>"
}
]
}
}

If record is not found:

{
"role": "assistant",
"message": {
"text": "Yeah, no. That CSI doesn’t exist. Try with real data.",
"action": "show-message",
"data": []
}
}

INTENT: FETCH CSI RECORD
Trigger: User wants to find, retrieve, or view CSI records.
Validate the query fields. If invalid:

{
"role": "assistant",
"message": {
"text": "You made up some fields. Try again with ones that actually exist.",
"action": "show-message",
"data": []
}
}

If records found:

{
"role": "assistant",
"message": {
"text": "Oh look, actual data! Here's what I found — 12 records, page 1.",
"action": "show-message",
"data": [
{
"csi_id": "CSI-2025-00034",
"customer_name": "PAUL MURRAY PLC",
"incoterm": "CIF"
},
...
]
}
}

If no match:

{
"role": "assistant",
"message": {
"text": "No CSI records match your ultra-rare criteria.",
"action": "show-message",
"data": []
}
}

TOOL OR LOGIC FAILURE

{
"role": "assistant",
"message": {
"text": "Oops. Something broke. It's not me, it's probably you.",
"action": "show-message",
"data": []
}
}

INSUFFICIENT INPUT HANDLING
If the input is insufficient, ask the user to provide more details

{
"role": "assistant",
"message": {
"text": "<sarcastic message about needing more details>",
"action": "show-message",
"data": [<All missing mandatory fields with empty values>]
}
}

DELETE FUNCTIONALITY
Currently disabled. Do not respond to any delete requests. If user asks to delete:

{
"role": "assistant",
"message": {
"text": "Delete? That feature took a vacation. Try later. Maybe.",
"action": "show-message",
"data": []
}
}

Make sure every output strictly follows this format.
"""

}

def log(msg: str):
    print(f"[{datetime.datetime.now().isoformat()}] {msg}")
@app.post("/chat", response_model=ChatSimpleResponse)
async def chat_endpoint(req: ChatRequest):
    process_id = f"{req.session_id}-{datetime.datetime.now().strftime('%Y%m%d%H%M%S%f')}"
    log(f"=== PROCESS START [{process_id}] ===")

    try:
        chat_history = session_histories.get(req.session_id, [])
        log(f"[{process_id}] Loaded {len(chat_history)} messages for session '{req.session_id}'")

        if not any(msg["role"] == "system" for msg in chat_history):
            log(f"[{process_id}] Injecting system prompt")
            chat_history.insert(0, {
                "role": "system",
                "content": SYSTEM_PROMPT["content"]
            })

        log(f"[{process_id}] Appending user message: {req.message}")
        chat_history.append({"role": "user", "content": req.message})

        log(f"[{process_id}] Calling process_messages()")
        assistant_message = process_messages(
            chat_history,
            session_id=req.session_id
        )

        log(f"[{process_id}] Assistant response: {assistant_message.get('content', '')}")
        chat_history.append(assistant_message)
        session_histories[req.session_id] = chat_history
        log(f"[{process_id}] Updated session memory to {len(chat_history)} messages")
        log(f"=== PROCESS END [{process_id}] ===\n")

        raw = assistant_message["content"]
        raw = re.sub(r"^```(?:json)?|```$", "", raw.strip(), flags=re.MULTILINE).strip()
        json_match = re.search(r"(\{[\s\S]*\})", raw)
        json_str = json_match.group(1) if json_match else raw

        try:
            res_json = json.loads(json_str)
        except Exception:
            log(f"[{process_id}] Failed to parse response JSON")
            raise HTTPException(status_code=500, detail="Invalid assistant response format")

        role = res_json.get("role", "assistant")
        message = res_json.get("message", {})

        text = message.get("text", "")
        action = message.get("action", "show-message")
        data = message.get("data", [])

        if isinstance(data, str):
            try:
                data = json.loads(data)
            except Exception:
                data = []

        if not isinstance(data, list):
            data = [data]

        return ChatSimpleResponse(
            role=role,
            message=ChatSimpleMessage(
                text=text,
                action=action,
                data=data
            )
        )

    except Exception as e:
        log(f"=== PROCESS ERROR [{process_id}] === {e}\n")
        raise HTTPException(status_code=500, detail="An error occurred while processing your request.")


@app.get("/get-form-fields")
def get_form_fields():
    form_fields = {
        "PART 1": {
            "Email Address": {"required": "true", "editable": "true", "data_type": "string"},
            "Attention To": {"required": "true", "editable": "true", "data_type": "string"},
            "Tax Identification Number": {"required": "true", "editable": "true", "data_type": "string"},
            "Sourcing Country": {
                "required": "true",
                "editable": "true",
                "data_type": "enum",
                "options": ["USA", "India", "China", "Germany", "Brazil"]
            },
            "Uapl Sold-To Code": {"required": "false", "editable": "false", "data_type": "string"},
            "Sourcing Cluster": {"required": "false", "editable": "false", "data_type": "string"},
            "Uapl Ship-To Code": {"required": "false", "editable": "false", "data_type": "string"},
            "Payment Term": {"required": "false", "editable": "false", "data_type": "string"},
            "Customer Segment": {"required": "false", "editable": "false", "data_type": "string"},
            "Bdm Name": {"required": "false", "editable": "false", "data_type": "string"},
            "Customer Service Name": {"required": "false", "editable": "false", "data_type": "string"},
            "Company Name": {"required": "false", "editable": "true", "data_type": "string"},
            "Company Address": {"required": "false", "editable": "true", "data_type": "string"},
            "Bank Details": {"required": "false", "editable": "true", "data_type": "string"}
        },
        "PART 2": {
            "Consignee": {"required": "true", "editable": "true", "data_type": "string"},
            "Notify Party": {"required": "true", "editable": "true", "data_type": "string"},
            "Uapl Ship-To  Code (Port Of Destination / Delivery Location Name)": {"required": "true", "editable": "true", "data_type": "string"},
            "(Attention To)": {"required": "true", "editable": "true", "data_type": "string"},
            "Freight Status": {"required": "false", "editable": "true", "data_type": "string"},
            "Origin Charges": {"required": "false", "editable": "true", "data_type": "string"},
            "Freight": {"required": "false", "editable": "true", "data_type": "string"},
            "Destination Charges": {"required": "false", "editable": "true", "data_type": "string"},
            "Incoterm": {"required": "false", "editable": "false", "data_type": "string"},
            "Shipping Line / Agent Name": {"required": "false", "editable": "true", "data_type": "string"},
            "Address": {"required": "false", "editable": "true", "data_type": "string"},
            "Telephone": {"required": "false", "editable": "true", "data_type": "string"},
            "Fax": {"required": "false", "editable": "true", "data_type": "string"},
            "Attention To": {"required": "false", "editable": "true", "data_type": "string"},
            "Container Load Type (Fcl ,Lcl ,Ftl)": {"required": "false", "editable": "true", "data_type": "string"}
        },
        "PART 3": {
            "Factory Packing List / Warehouse Packing List": {"required": "true", "editable": "true", "data_type": "string"},
            "Order Submission": {"required": "false", "editable": "true", "data_type": "string"},
            "Invoice & Documentation": {"required": "false", "editable": "true", "data_type": "string"},
            "Baki Sare .....................": {"required": "false", "editable": "true", "data_type": "string"}
        },
        "PART 4": {
            "Company Name": {"required": "false", "editable": "true", "data_type": "string"},
            "Company Address": {"required": "false", "editable": "true", "data_type": "string"},
            "Postal Code": {"required": "false", "editable": "true", "data_type": "string"},
            "Attention To": {"required": "false", "editable": "true", "data_type": "string"},
            "Telephone": {"required": "false", "editable": "true", "data_type": "string"},
            "Fax": {"required": "false", "editable": "true", "data_type": "string"},
            "Email": {"required": "false", "editable": "true", "data_type": "string"}
        },
        "PART 5": {
            "Delivery Time Slot": {"required": "false", "editable": "true", "data_type": "string"},
            "Delivery Day(s)": {"required": "false", "editable": "true", "data_type": "string"},
            "Maximum Trips Per Day": {"required": "false", "editable": "true", "data_type": "string"},
            "Contact Person": {"required": "false", "editable": "true", "data_type": "string"},
            "Telephone Number": {"required": "false", "editable": "true", "data_type": "string"},
            "Email Address": {"required": "false", "editable": "true", "data_type": "string"},
            "Are Documents Needed Upon Delivery?": {"required": "false", "editable": "true", "data_type": "string"},
            "Others, Specify": {"required": "false", "editable": "true", "data_type": "string"}
        },
        "PART 6": {
            "Packing Instruction": {"required": "true", "editable": "true", "data_type": "string"},
            "Specific Packing Instruction": {"required": "true", "editable": "true", "data_type": "string"},
            "Pre Loading Photos": {"required": "true", "editable": "true", "data_type": "string"},
            "Pallet Size": {"required": "false", "editable": "true", "data_type": "string"},
            "Pallet Type": {"required": "false", "editable": "true", "data_type": "string"},
            "Shipping Mark On Pallet (Name)": {"required": "false", "editable": "true", "data_type": "string"}
        }
    }

    return {"message": "Form field definitions loaded successfully", "data": [form_fields]}