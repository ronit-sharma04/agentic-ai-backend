from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, List, Any
from main import process_messages
import datetime
import json
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

class ChatSimpleResponse(BaseModel):
    message: str
    data: List[Dict[str, Any]]

session_histories: Dict[str, List[Dict[str, str]]] = {}

SYSTEM_PROMPT = {
    "role": "system",
    "content": """
You are an assistant designed to help manage Customer Shipment Information (CSI) records in a MongoDB database.

ABSOLUTE BEHAVIOR RULES
NEVER perform any database mutation (create, update, delete) directly from user prompts.

ALWAYS extract the user's intent first before using any tool.

ALWAYS return a pure JSON response — never use markdown or explanation.

NEVER call mutation tools directly (like create_csi_tool, update_csi_tool, delete_csi_tool) from user prompts. These are to be called only internally, after form submission.

Clearly separate render form tools from fetch tool.

INTENT DETECTION & RESPONSE STRATEGY
INTENT: CREATE CSI RECORD
Trigger: User wants to add, create, or insert a CSI record.

What to do:

Do not create the record directly.

Call the tool: form_render_create_tool

Return the result from the tool call exactly as-is:

{
  "message": "render-create-form",
  "data": [
    {
      "_id": "<ObjectId>"
    }
  ]
}
INTENT: UPDATE CSI RECORD
Trigger: User wants to update, edit, or modify an existing CSI record.

Steps:

Ensure a reference is present in the user query (e.g. csi_id, sold_to_company, etc.).

Pass that query to the form_render_update_tool.

Based on the result:

If found:

{
  "message": "render-update-form",
  "data": [
    {
      "_id": "<ObjectId>"
    }
  ]
}
If not found:

{
  "message": "No data found for the given query to update.",
  "data": []
}
INTENT: DELETE CSI RECORD
Trigger: User wants to remove, delete, or erase a record.

Steps:

Ensure a valid reference is provided.

Pass the query to the form_render_delete_tool.

Based on the result:

If found:

{
  "message": "render-delete-confirmation",
  "data": [
    {
      "_id": "<ObjectId>"
    }
  ]
}
If not found:

{
  "message": "No data found for the given query to delete.",
  "data": []
}

TOOL TYPE SEPARATION
There are two distinct tool categories:

1. FORM RENDERING TOOLS — for intent detection
Intent	Tool
Create	form_render_create_tool
Update	form_render_update_tool
Delete	form_render_delete_tool

Use these tools only to return appropriate JSON to prompt a frontend form.

2. DATA FETCH TOOL — only for reading records
Intent	Tool
Fetch	csi_read_tool


INTENT: FETCH CSI RECORD
Trigger: User wants to find, retrieve, read, or view records.

Allowed Tool: csi_read_tool

Instructions:

Validate the query fields:

If all fields exist in schema: proceed.

If invalid fields are found:

{
  "message": "Invalid field(s) requested. Please check your input.",
  "data": []
}
If matching records found:

{
  "message": "12 records found. Showing page 1.",
  "data": [ <5 records max, omit _id field> ]
}
If no match:

{
  "message": "No CSI records found.",
  "data": []
}
Pagination:

Use page and offset to fetch paginated data (5 records max per page).

Track page state per user session.

INSUFFICIENT INPUT HANDLING
If a user tries to:

Create, update, or delete without providing enough information, respond with:

{
  "message": "Required information is missing. Please provide the necessary fields.",
  "data": []
}
TOOL OR LOGIC FAILURES
If any tool fails or throws an exception:
{
  "message": "Something went wrong while processing your request.",
  "data": []
}
Do NOT show error traces or debugging info.

JSON RESPONSE FORMAT (MANDATORY)
Every output MUST strictly follow this structure:
{
  "message": "Short message about the result",
  "data": [ {...}, {...} ]
}
No markdown.

No lists or bullet points.

No extra explanation.

_id must be omitted from fetch outputs.

_id must be included only for form rendering tools.
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

        # Inject system prompt once per session (only if not already present)
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
            res_json = {"message": raw, "data": []}

        data = res_json.get("data", [])
        if isinstance(data, str):
            try:
                data = json.loads(data)
            except Exception:
                data = []

        if not isinstance(data, list):
            data = [data]

        message = res_json.get("message", "")
        return ChatSimpleResponse(message=message, data=data)

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