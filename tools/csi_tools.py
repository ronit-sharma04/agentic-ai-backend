from langchain_core.tools import tool
from crud.cases_crud import read_cases, create_case, update_case, delete_case, approve_case, get_case_by_id
from crud.approved_csi_crud import read_approved_csi, create_approved_csi, update_approved_csi, delete_approved_csi
from pydantic import ValidationError, BaseModel, Field
from typing import Dict, Any, Optional, List, Union
import logging
import traceback
import json

# Define Pydantic models for tool inputs
class CSIToolArgs(BaseModel, extra="allow"):
    """Arguments for CSI tools with flexible field support"""
    def model_dump(self):
        # Return all fields except private ones
        return {k: v for k, v in self.__dict__.items() if not k.startswith("_")}


class UpdateCaseArgs(BaseModel):
    """Arguments for update case tool"""
    query_fields: Dict[str, Any] = Field(..., description="Fields to identify the case to update")
    update_fields: Dict[str, Any] = Field(..., description="Fields to update in the case")

class DeleteCaseArgs(BaseModel):
    """Arguments for delete case tool"""
    query_fields: Dict[str, Any] = Field(..., description="Fields to identify the case to delete")


@tool
def read_cases_tool(inputs: CSIToolArgs) -> dict:
    """
    Retrieve CSI Cases (draft/pending Customer Shipment Instruction records) from the database using advanced filtering and pagination.

    This tool searches the 'cases' collection which contains draft/pending CSI records that have not yet been approved.
    For approved/historical CSI records, use the read_approved_csi_tool instead.

    === Capabilities ===
    - Supports full-text, case-insensitive search on string fields
    - Accepts MongoDB ObjectId (`id` or `_id`) when provided
    - Filters only non-empty fields automatically
    - Paginates results using the `page` parameter (default: 1)
    - Returns a structured response with status, message, and data fields

    === Filterable Fields ===
    You can provide any of the following fields as filters:
    
    case_id, sold_to_code, sold_to_comp_name, ship_to_code, ship_to_comp1_name, 
    source_country, customer_segment, bdm_name, bdm_email, customer_service_email,
    consignee, notify_party, port_of_destination, freight_status, incoterm_1,
    invoice_signed_and_hc, bill_of_lading, insurance_certificate, product_type,
    packing_instruction, csi_status, created_at, modified_at, approved_at, process_activity
    
    And many other fields from the CSI schema.

    === Returns ===
    - success: Boolean indicating if the operation succeeded
    - message: Description of the result with count of matching records
    - data: Array of matching CSI case documents (with `_id` removed)
    - error: Boolean indicating if an error occurred (only present on error)

    Example Usage:
    Use this tool to search for draft/pending CSI cases that have not yet been approved.
    """
    try:
        # Extract page parameter if present, otherwise use default
        data = inputs.model_dump()
        page = data.pop('page', 1) if 'page' in data else 1
        
        # Log the tool invocation
        logging.info(f"[READ_CASES_TOOL] Called with filters={data}, page={page}")
        
        # Call the underlying CRUD function
        result = read_cases(page=page, **data)
        
        # Log the result summary
        logging.info(f"[READ_CASES_TOOL] Found {len(result.get('data', []))} records")
        
        return result
    except Exception as e:
        # Log the full error with traceback
        logging.error(f"[READ_CASES_TOOL] Error: {str(e)}")
        logging.error(traceback.format_exc())
        
        # Return a structured error response
        return {
            "success": False,
            "message": f"Error reading cases: {str(e)}",
            "data": [],
            "error": True
        }

read_cases_tool.name = "csi_read_tool"


@tool
def create_cases_tool(inputs: CSIToolArgs) -> dict:
    """
    Create a new CSI Case (draft/pending Customer Shipment Instruction record) in the database.

    This tool creates a new record in the 'cases' collection which stores draft/pending CSI records.
    The case will initially have 'pending' status and can later be approved using the approve_case_tool.

    === Capabilities ===
    - Accepts any combination of valid CSI fields as input
    - Automatically generates a unique `case_id` for the record (format: CSI-XXXXXXXX)
    - Sets default status `csi_status = "pending"` for every new record
    - Adds creation timestamp and fetches current process activity status
    - Returns the complete created case with all fields

    === Key Fields ===
    You can provide values for any of the following fields (and many others):
    
    sold_to_code, sold_to_comp_name, ship_to_code, ship_to_comp1_name,
    source_country, customer_segment, bdm_name, bdm_email,
    customer_service_email, consignee, notify_party, port_of_destination,
    freight_status, incoterm_1, invoice_signed_and_hc, bill_of_lading,
    insurance_certificate, product_type, packing_instruction

    === Returns ===
    - success: Boolean indicating if the operation succeeded
    - message: Description of the result with the generated case_id
    - case_id: The unique identifier for the created case
    - data: The complete created case document
    - error: Boolean indicating if an error occurred (only present on error)

    Example Usage:
    Use this tool to create a new draft CSI case. You do not need to provide `case_id`, `csi_status`,
    `created_at`, or `process_activity` as these are handled automatically.
    """
    try:
        # Extract case data from inputs
        case_data = inputs.model_dump()
        
        # Log the tool invocation
        logging.info(f"[CREATE_CASE_TOOL] Creating new case with data: {json.dumps(case_data, default=str)}")
        
        # Call the underlying CRUD function
        result = create_case(**case_data)
        
        # Log the result summary
        if result.get("case_id"):
            logging.info(f"[CREATE_CASE_TOOL] Successfully created case with ID: {result.get('case_id')}")
        else:
            logging.warning(f"[CREATE_CASE_TOOL] Creation result without case_id: {result}")
        
        return result
    except ValidationError as e:
        # Log validation errors
        logging.error(f"[CREATE_CASE_TOOL] Validation error: {str(e)}")
        logging.error(traceback.format_exc())
        
        return {
            "success": False,
            "message": f"Validation error: {str(e)}",
            "error": True
        }
    except Exception as e:
        # Log any other exceptions
        logging.error(f"[CREATE_CASE_TOOL] Error: {str(e)}")
        logging.error(traceback.format_exc())
        
        return {
            "success": False,
            "message": f"Error creating case: {str(e)}",
            "error": True
        }
create_cases_tool.name = "create_cases_tool"


@tool
def approve_case_tool(inputs: CSIToolArgs) -> dict:
    """
    Approve a CSI Case, changing its status to 'approved' and copying it to the approved_csi collection.

    This tool transitions a draft/pending CSI case to an approved state by:
    1. Updating its status to 'approved' in the cases collection
    2. Adding an approval timestamp
    3. Copying the complete record to the approved_csi collection (final/read-only state)

    === Capabilities ===
    - Requires case_id to identify the specific case to approve
    - Validates the case exists before approval
    - Updates case status to "approved" with timestamp
    - Creates a copy in the approved_csi collection (historical record)
    - Returns both the updated case and the new approved_csi record

    === Required Parameters ===
    - case_id: The unique identifier of the case to approve (format: CSI-XXXXXXXX)

    === Returns ===
    - success: Boolean indicating if the operation succeeded
    - message: Description of the approval result
    - data: The approved case document
    - error: Boolean indicating if an error occurred (only present on error)

    Example Usage:
    Use this tool to approve a specific CSI case that has been reviewed and is ready for final approval.
    This moves the case to approved status and creates a historical record in the approved_csi collection.
    """
    try:
        # Extract case_id from inputs
        data = inputs.model_dump()
        case_id = data.get('case_id')
        
        if not case_id:
            return {
                "success": False,
                "message": "Error: case_id is required for approval",
                "error": True
            }
        
        # Log the tool invocation
        logging.info(f"[APPROVE_CASE_TOOL] Approving case with ID: {case_id}")
        
        # Call the underlying CRUD function
        result = approve_case(case_id=case_id)
        
        # Log the result summary
        if result.get("success", False):
            logging.info(f"[APPROVE_CASE_TOOL] Successfully approved case: {case_id}")
        else:
            logging.warning(f"[APPROVE_CASE_TOOL] Failed to approve case: {case_id}. {result.get('message')}")
        
        return result
    except ValidationError as e:
        # Log validation errors
        logging.error(f"[APPROVE_CASE_TOOL] Validation error: {str(e)}")
        logging.error(traceback.format_exc())
        
        return {
            "success": False,
            "message": f"Validation error: {str(e)}",
            "error": True
        }
    except Exception as e:
        # Log any other exceptions
        logging.error(f"[APPROVE_CASE_TOOL] Error: {str(e)}")
        logging.error(traceback.format_exc())
        
        return {
            "success": False,
            "message": f"Error approving case: {str(e)}",
            "error": True
        }


approve_case_tool.name = "approve_case_tool"

from langchain_core.tools import tool
from crud.cases_crud import update_case
from pydantic import ValidationError
from tools.cases_args import CSIToolArgs
import logging


@tool
def update_case_tool(inputs: UpdateCaseArgs) -> dict:
    """
    Update a CSI Case (draft/pending Customer Shipment Instruction record) in the database.

    This tool updates records in the 'cases' collection which contains draft/pending CSI records.
    It uses a two-part structure with query_fields to identify the case and update_fields to specify changes.

    === Capabilities ===
    - Uses query_fields to identify which case(s) to update
    - Applies update_fields to modify the matched case(s)
    - Supports flexible querying with regex for string fields
    - Automatically adds modification timestamp
    - Returns the updated case document
    - Skips empty or null fields automatically
    - Adds modification timestamp automatically

    === Input Structure ===
    {
        "query_fields": { ... },   # Fields to identify the case to update
        "update_fields": { ... }   # Fields and values to update
    }

    === Filterable & Updatable Fields ===
    You can use any CSI field for both filtering and updating, including:
    case_id, sold_to_code, customer_segment, bdm_email, ship_to_code, etc.

    === Returns ===
    - success: Boolean indicating if the operation succeeded
    - message: Description of the update result
    - data: The updated case document (if successful)
    - error: Boolean indicating if an error occurred (only present on error)

    Example Usage:
    Use this tool to update specific fields in a draft CSI case while keeping other fields unchanged.
    This is useful for correcting information or adding additional details to an existing case.
    """

    try:
        # Extract query and update fields
        query_fields = inputs.query_fields
        update_fields = inputs.update_fields
        
        # Filter out empty values
        query_fields = {k: v for k, v in query_fields.items() if v not in ("", None)}
        update_fields = {k: v for k, v in update_fields.items() if v not in ("", None)}

        if not query_fields or not update_fields:
            return {
                "success": False,
                "message": "Both 'query_fields' and 'update_fields' must be provided and non-empty.",
                "error": True
            }

        # Log the tool invocation
        logging.info(f"[UPDATE_CASE_TOOL] Updating case with query: {json.dumps(query_fields, default=str)}")
        logging.info(f"[UPDATE_CASE_TOOL] Update fields: {json.dumps(update_fields, default=str)}")
        
        # Call the underlying CRUD function
        result = update_case(query_fields=query_fields, update_fields=update_fields)
        
        # Log the result summary
        if result.get("success", False):
            logging.info(f"[UPDATE_CASE_TOOL] Successfully updated case matching: {json.dumps(query_fields, default=str)}")
        else:
            logging.warning(f"[UPDATE_CASE_TOOL] Failed to update case: {result.get('message')}")
        
        return result
    except ValidationError as e:
        # Log validation errors
        logging.error(f"[UPDATE_CASE_TOOL] Validation error: {str(e)}")
        logging.error(traceback.format_exc())
        
        return {
            "success": False,
            "message": f"Validation error: {str(e)}",
            "error": True
        }
    except Exception as e:
        # Log any other exceptions
        logging.error(f"[UPDATE_CASE_TOOL] Error: {str(e)}")
        logging.error(traceback.format_exc())
        
        return {
            "success": False,
            "message": f"Error updating case: {str(e)}",
            "error": True
        }



@tool
def delete_case_tool(inputs: DeleteCaseArgs) -> dict:
    """
    Delete a CSI Case (draft/pending Customer Shipment Instruction record) from the database.
    
    This tool removes records from the 'cases' collection which contains draft/pending CSI records.
    It uses query_fields to identify which case(s) to delete.
    
    === Capabilities ===
    - Uses query_fields to identify which case(s) to delete
    - Supports flexible querying with regex for string fields
    - Returns information about the deleted case(s)
    - Provides detailed error messages if deletion fails
    
    === Input Structure ===
    {
        "query_fields": { ... }   # Fields to identify the case(s) to delete
    }
    
    === Filterable Fields ===
    You can use any CSI field for filtering, including:
    case_id, sold_to_code, customer_segment, bdm_email, ship_to_code, etc.
    
    === Returns ===
    - success: Boolean indicating if the operation succeeded
    - message: Description of the deletion result with count of deleted records
    - data: Information about the deleted case(s) if available
    - error: Boolean indicating if an error occurred (only present on error)
    
    Example Usage:
    Use this tool to delete draft CSI cases that are no longer needed.
    This operation cannot be undone, so use it carefully.
    """
    
    try:
        # Extract query fields
        query_fields = inputs.query_fields
        
        # Filter out empty values
        query_fields = {k: v for k, v in query_fields.items() if v not in ("", None)}
        
        if not query_fields:
            return {
                "success": False,
                "message": "Query fields must be provided and non-empty.",
                "error": True
            }
        
        # Log the tool invocation
        logging.info(f"[DELETE_CASE_TOOL] Deleting case with query: {json.dumps(query_fields, default=str)}")
        
        # Call the underlying CRUD function
        result = delete_case(query_fields=query_fields)
        
        # Log the result summary
        if result.get("success", False):
            logging.info(f"[DELETE_CASE_TOOL] Successfully deleted case(s) matching: {json.dumps(query_fields, default=str)}")
        else:
            logging.warning(f"[DELETE_CASE_TOOL] Failed to delete case: {result.get('message')}")
        
        return result
    except ValidationError as e:
        # Log validation errors
        logging.error(f"[DELETE_CASE_TOOL] Validation error: {str(e)}")
        logging.error(traceback.format_exc())
        
        return {
            "success": False,
            "message": f"Validation error: {str(e)}",
            "error": True
        }
    except Exception as e:
        # Log any other exceptions
        logging.error(f"[DELETE_CASE_TOOL] Error: {str(e)}")
        logging.error(traceback.format_exc())
        
        return {
            "success": False,
            "message": f"Error deleting case: {str(e)}",
            "error": True
        }


delete_case_tool.name = "delete_case_tool"


@tool
def read_approved_csi_tool(inputs: CSIToolArgs) -> dict:
    """
    Retrieve Approved CSI records (final/read-only Customer Shipment Instruction records) from the database.
    
    This tool searches the 'approved_csi' collection which contains final approved CSI records.
    For draft/pending CSI records that have not yet been approved, use the read_cases_tool instead.
    
    === Capabilities ===
    - Supports full-text, case-insensitive search on string fields
    - Accepts MongoDB ObjectId (`id` or `_id`) when provided
    - Filters only non-empty fields automatically
    - Paginates results using the `page` parameter (default: 1)
    - Returns a structured response with status, message, and data fields
    
    === Filterable Fields ===
    You can provide any of the following fields as filters:
    
    case_id, sold_to_code, sold_to_comp_name, ship_to_code, ship_to_comp1_name, 
    source_country, customer_segment, bdm_name, bdm_email, customer_service_email,
    consignee, notify_party, port_of_destination, freight_status, incoterm_1,
    invoice_signed_and_hc, bill_of_lading, insurance_certificate, product_type,
    packing_instruction, csi_status, created_at, modified_at, approved_at, process_activity
    
    === Returns ===
    - success: Boolean indicating if the operation succeeded
    - message: Description of the result with count of matching records
    - data: Array of matching approved CSI records (with `_id` removed)
    - error: Boolean indicating if an error occurred (only present on error)
    
    Example Usage:
    Use this tool to search for historical approved CSI records that have completed the approval process.
    These records are read-only and represent the final state of each CSI case.
    """
    
    try:
        # Extract fields from inputs
        fields = inputs.model_dump()
        
        # Extract page parameter if present, default to 1
        page = fields.pop('page', 1) if isinstance(fields, dict) else 1
        
        # Filter out empty values
        if isinstance(fields, dict):
            fields = {k: v for k, v in fields.items() if v not in ("", None)}
        
        # Log the tool invocation
        logging.info(f"[READ_APPROVED_CSI_TOOL] Searching approved CSI with filters: {json.dumps(fields, default=str)}")
        
        # Call the underlying CRUD function
        result = read_approved_csi(page=page, **fields)
        
        # Add success flag for consistency
        if "error" not in result:
            result["success"] = True
        
        # Log the result summary
        record_count = len(result.get("data", []))
        logging.info(f"[READ_APPROVED_CSI_TOOL] Found {record_count} approved CSI records")
        
        return result
    except ValidationError as e:
        # Log validation errors
        logging.error(f"[READ_APPROVED_CSI_TOOL] Validation error: {str(e)}")
        logging.error(traceback.format_exc())
        
        return {
            "success": False,
            "message": f"Validation error: {str(e)}",
            "error": True
        }
    except Exception as e:
        # Log any other exceptions
        logging.error(f"[READ_APPROVED_CSI_TOOL] Error: {str(e)}")
        logging.error(traceback.format_exc())
        
        return {
            "success": False,
            "message": f"Error reading approved CSI records: {str(e)}",
            "error": True
        }


read_approved_csi_tool.name = "read_approved_csi_tool"
