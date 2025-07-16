from fastapi import Body, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy import true,false
from db.connection import get_db_connection
from main import process_messages
import datetime
import json
from typing import Collection, Dict, List, Any, Optional, Literal
import re
from fetch_business_ruleset import fetch_business_ruleset
from system_prompt import fetch_system_prompt

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
    action: Literal["show-message", "render-create-csi-form", "render-update-csi-form","render-vertical-table"]
    data: Optional[List[Dict[str, Any]]] = []

class ChatSimpleResponse(BaseModel):
    role: Literal["assistant"]
    message: ChatSimpleMessage

session_histories: Dict[str, List[Dict[str, str]]] = {}

from fetch_process_activity import fetch_process_activity

def log(msg: str):
    print(f"[{datetime.datetime.now().isoformat()}] {msg}")
@app.post("/chat", response_model=ChatSimpleResponse)
async def chat_endpoint(req: ChatRequest):
    process_id = f"{req.session_id}-{datetime.datetime.now().strftime('%Y%m%d%H%M%S%f')}"
    log(f"=== PROCESS START [{process_id}] ===")

    try:
        fetched_ruleset = fetch_business_ruleset() 
        SYSTEM_PROMPT = {
            "role": "system",
            "content": fetch_system_prompt()
        }
        # log(SYSTEM_PROMPT["content"])
        chat_history = session_histories.get(req.session_id, [])
        log(f"[{process_id}] Loaded {len(chat_history)} messages for session '{req.session_id}'")

        if chat_history and chat_history[0]["role"] == "system":
            log(f"[{process_id}] Refreshing system prompt to latest version")
            chat_history[0]["content"] = SYSTEM_PROMPT["content"]
        else:
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
  "Customer Information": [
    {
      "label": "Customer Segment",
      "editable": "false",
      "input_type": "text",
      "key": "customer_segment"
    },
    {
      "label": "Sourcing Country",
      "editable": "true",
      "input_type": "text",
      "key": "source_country"
    },
    {
      "label": "UAPL Sold-To Code",
      "editable": "false",
      "input_type": "text",
      "key": "sold_to_code"
    },
    {
      "label": "Company Name",
      "editable": "true",
      "input_type": "text",
      "key": "sold_to_comp_name"
    },
    {
      "label": "Incoterm",
      "editable": "false",
      "input_type": "text",
      "key": "incoterm_1"
    },
    {
      "label": "UAPL Ship-To Code",
      "editable": "false",
      "input_type": "text",
      "key": "ship_to_code"
    },
    {
      "label": "Ship-To Company Name",
      "editable": "true",
      "input_type": "text",
      "key": "ship_to_comp1_name"
    },
    {
      "label": "Port of Destination",
      "editable": "true",
      "input_type": "text",
      "key": "port_of_destination"
    },
    {
      "label": "Customer Name",
      "editable": "true",
      "input_type": "text",
      "key": "customer_name"
    },
    {
      "label": "Email Address",
      "editable": "true",
      "input_type": "text",
      "key": "customer_email"
    },
    {
      "label": "Product Type",
      "editable": "true",
      "input_type": "text",
      "key": "product_type"
    },
    {
      "label": "BDM Name",
      "editable": "false",
      "input_type": "text",
      "key": "bdm_name"
    },
    {
      "label": "Appointed Carrier Name",
      "editable": "true",
      "input_type": "text",
      "key": "appointed_carrier_name"
    },
    {
      "label": "Customer Service Name",
      "editable": "false",
      "input_type": "text",
      "key": "customer_service_name"
    },
    {
      "label": "Attention To",
      "editable": "true",
      "input_type": "text",
      "key": "attention_to"
    },
    {
      "label": "Tax Identification Number",
      "editable": "true",
      "input_type": "text",
      "key": "tax_identification_number"
    },
    {
      "label": "Sourcing Cluster",
      "editable": "false",
      "input_type": "text",
      "key": "sourcing_cluster"
    },
    {
      "label": "Payment Term",
      "editable": "false",
      "input_type": "text",
      "key": "payment_term"
    },
    {
      "label": "Company Address",
      "editable": "true",
      "input_type": "text",
      "key": "sold_to_comp_add1"
    },
    {
      "label": "Bank Details",
      "editable": "true",
      "input_type": "text",
      "key": "bank_details"
    }
  ],
  "Bill of Lading": [
    {
      "label": "Consignee",
      "editable": "true",
      "input_type": "text",
      "key": "consignee"
    },
    {
      "label": "Notify Party",
      "editable": "true",
      "input_type": "text",
      "key": "notify_party"
    },
    {
      "label": "UAPL Ship-To Code",
      "editable": "true",
      "input_type": "text",
      "key": "ship_to_code"
    },
    {
      "label": "Attention To",
      "editable": "true",
      "input_type": "text",
      "key": "bl_attention_to"
    },
    {
      "label": "Freight Status",
      "editable": "true",
      "input_type": "text",
      "key": "freight_status"
    },
    {
      "label": "Origin Charges",
      "editable": "true",
      "input_type": "text",
      "key": "origin_charges"
    },
    {
      "label": "Freight",
      "editable": "true",
      "input_type": "text",
      "key": "freight_charges"
    },
    {
      "label": "Destination Charges",
      "editable": "true",
      "input_type": "text",
      "key": "destination_charges"
    },
    {
      "label": "Incoterm",
      "editable": "false",
      "input_type": "text",
      "key": "incoterm_1"
    },
    {
      "label": "Shipping Line or Agent Name",
      "editable": "true",
      "input_type": "text",
      "key": "appointed_carrier_name"
    },
    {
      "label": "Address",
      "editable": "true",
      "input_type": "text",
      "key": "appointed_carrier_add1"
    },
    {
      "label": "Telephone",
      "editable": "true",
      "input_type": "text",
      "key": "telephone"
    },
    {
      "label": "Fax",
      "editable": "true",
      "input_type": "text",
      "key": "fax"
    },
    {
      "label": "Contact Person",
      "editable": "true",
      "input_type": "text",
      "key": "notify_name"
    },
    {
      "label": "Container Load Type",
      "editable": "true",
      "input_type": "select",
      "options": ["FCL", "LCL", "FTL"],
      "key": "container_load_type"
    }
  ],
  "Shipping Documents": [
    {
      "label": "Factory or Warehouse Packing List",
      "editable": "true",
      "input_type": "text",
      "key": "factory_packing_list"
    },
    {
      "label": "Order Submission",
      "editable": "true",
      "input_type": "text",
      "key": "order_submission"
    },
    {
      "label": "Invoice and Documentation",
      "editable": "true",
      "input_type": "text",
      "key": "inv_doc"
    }
  ],
  "Mailing Information": [
    {
      "label": "Company Name",
      "editable": "true",
      "input_type": "text",
      "key": "mail_comp_name"
    },
    {
      "label": "Company Address",
      "editable": "true",
      "input_type": "text",
      "key": "mail_comp_add1"
    },
    {
      "label": "Postal Code",
      "editable": "true",
      "input_type": "text",
      "key": "postal_code"
    },
    {
      "label": "Attention To",
      "editable": "true",
      "input_type": "text",
      "key": "attention_to"
    },
    {
      "label": "Telephone",
      "editable": "true",
      "input_type": "text",
      "key": "telephone"
    },
    {
      "label": "Fax",
      "editable": "true",
      "input_type": "text",
      "key": "fax"
    },
    {
      "label": "Email",
      "editable": "true",
      "input_type": "text",
      "key": "notify_email"
    }
  ],
  "Delivery Instruction": [
    {
      "label": "Delivery Time Slot",
      "editable": "true",
      "input_type": "text",
      "key": "delivery_time_slot"
    },
    {
      "label": "Delivery Days",
      "editable": "true",
      "input_type": "text",
      "key": "delivery_days"
    },
    {
      "label": "Maximum Trips Per Day",
      "editable": "true",
      "input_type": "text",
      "key": "max_trips_per_day"
    },
    {
      "label": "Contact Person",
      "editable": "true",
      "input_type": "text",
      "key": "notify_attention_to1"
    },
    {
      "label": "Telephone Number",
      "editable": "true",
      "input_type": "text",
      "key": "telephone_number"
    },
    {
      "label": "Email Address",
      "editable": "true",
      "input_type": "text",
      "key": "notify_email"
    },
    {
      "label": "Are Documents Needed Upon Delivery",
      "editable": "true",
      "input_type": "text",
      "key": "docs_needed_upon_delivery"
    },
    {
      "label": "Other Instructions",
      "editable": "true",
      "input_type": "text",
      "key": "other_instructions"
    }
  ],
  "Shipment Packing Instruction": [
    {
      "label": "Packing Instruction",
      "editable": "true",
      "input_type": "text",
      "key": "packing_instruction"
    },
    {
      "label": "Specific Packing Instruction",
      "editable": "true",
      "input_type": "text",
      "key": "specific_packing_instru"
    },
    {
      "label": "Pre-loading Photos",
      "editable": "true",
      "input_type": "text",
      "key": "preloading_photos"
    },
    {
      "label": "Pallet Size",
      "editable": "true",
      "input_type": "text",
      "key": "pallet_dimension"
    },
    {
      "label": "Pallet Type",
      "editable": "true",
      "input_type": "text",
      "key": "pallet_type"
    },
    {
      "label": "Shipping Mark on Pallet",
      "editable": "true",
      "input_type": "text",
      "key": "shipping_mark_on_pallet"
    }
  ]
}

    return {"message": "Form field definitions loaded successfully", "data": [form_fields]}

COLLECTION_NAME = "cases"

@app.post("/submit_case")
def upsert_case(case: Dict[str, Any] = Body(...)):
    print("Received request body:", case)

    if "case_id" not in case:
        print("Error: 'case_id' missing from request body")
        raise HTTPException(status_code=400, detail="Missing 'case_id' in request body")

    print("Connecting to DB...")
    db = get_db_connection(COLLECTION_NAME)
    collection: Collection = db[COLLECTION_NAME]
    print("Connected to collection:", COLLECTION_NAME)

    case_id = case["case_id"]
    print(f"Processing case_id: {case_id}")

    if "_id" in case:
        print("Removing '_id' from case to avoid MongoDB conflict")
        case.pop("_id", None)

    print("Performing upsert operation...")
    result = collection.update_one(
        {"case_id": case_id},
        {"$set": case},
        upsert=True
    )
    updated_case = collection.find_one({"case_id": case_id})
    print("Fetched updated case:", updated_case)

    if updated_case and "_id" in updated_case:
        updated_case["_id"] = str(updated_case["_id"])
        print("Converted '_id' to string for JSON serialization")

    response = {
        "text": "Final Case Details Submitted",
        "action": "show-message",
        "data": [updated_case]
    }

    print("Returning response:", response)
    return response