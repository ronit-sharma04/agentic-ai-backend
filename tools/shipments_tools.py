from langchain_core.tools import tool
from crud.shipments_crud import read_shipments, get_latest_shipments, get_shipment_by_id
from pydantic import ValidationError, BaseModel, Field
from typing import Dict, Any, Optional, List, Union
import logging
import traceback
import json

# Define Pydantic models for tool inputs
class ShipmentsToolArgs(BaseModel, extra="allow"):
    """Arguments for Shipments tools with flexible field support"""
    pass

@tool
def read_shipments_tool(inputs: ShipmentsToolArgs) -> dict:
    """
    Retrieve shipment records from the database using advanced filtering and pagination.

    This tool searches the 'shipments' collection which contains logistics and shipping data.

    === Capabilities ===
    - Supports full-text, case-insensitive search on string fields
    - Accepts MongoDB ObjectId (`id` or `_id`) when provided
    - Filters only non-empty fields automatically
    - Paginates results using the `page` parameter (default: 1)
    - Returns a structured response with status, message, and data fields

    === Key Filterable Fields ===
    You can provide any of the following fields as filters:
    
    **Customer Information:**
    - name1_of_sold_to_party, sold_to_party, name1_of_ship_to_party, ship_to_party
    
    **Order Information:**
    - customer_po_number, ph_sales_order, sales_document, item, index
    
    **Material Information:**
    - material, customer_material, material_description, product_weight
    
    **Date Fields:**
    - customer_crd, ph_po_stat_date, actual_gi_date, gr_date_in_ph, delivery_date
    - requested_delivery_date, contractual_delivery_date_lo, planned_gi_date
    
    **Shipping Information:**
    - shipping_conditions, po_ship_condition, transport_lt, route, shipping_point
    - shipment_number, outbound_delivery_number
    
    **Financial Information:**
    - so_netprice, po_netprice, currency
    
    **Organizational:**
    - plant, sales_organization, distribution_channel, division
    
    **Quantities:**
    - ordered_quantity, confirmed_quantity, delivery_quantity, invoiced_qty
    
    **Performance Metrics:**
    - arrival_lt_crd, no_of_days_arrive_early, arrival_lt_stat_date
    
    === Returns ===
    - success: Boolean indicating if the operation succeeded
    - message: Description of the result with count of matching records
    - data: Array of matching shipment records (with `_id` converted to string)
    - error: Boolean indicating if an error occurred (only present on error)

    === Example Usage ===
    - Search by customer: {"name1_of_sold_to_party": "Schneider Electric"}
    - Search by order: {"ph_sales_order": "10101607"}
    - Search by material: {"material": "E5054NL-GB"}
    - Search with pagination: {"shipping_conditions": "Z5", "page": 2}
    """
    try:
        # Convert inputs to dict and filter out empty values
        input_dict = inputs.dict() if hasattr(inputs, 'dict') else dict(inputs)
        
        # Extract page parameter
        page = input_dict.pop('page', 1)
        
        # Filter out empty values
        filtered_inputs = {k: v for k, v in input_dict.items() if v and v != ""}
        
        print(f"[SHIPMENTS TOOL] Calling read_shipments with filters: {filtered_inputs}, page: {page}")
        
        # Call the CRUD function
        result = read_shipments(page=page, **filtered_inputs)
        
        print(f"[SHIPMENTS TOOL] CRUD result: success={result.get('success')}, count={len(result.get('data', []))}")
        
        return result
        
    except ValidationError as e:
        error_msg = f"Validation error in read_shipments_tool: {str(e)}"
        print(f"[SHIPMENTS TOOL ERROR] {error_msg}")
        return {
            "success": False,
            "error": True,
            "message": error_msg,
            "data": []
        }
    except Exception as e:
        error_msg = f"Unexpected error in read_shipments_tool: {str(e)}"
        print(f"[SHIPMENTS TOOL ERROR] {error_msg}")
        traceback.print_exc()
        return {
            "success": False,
            "error": True,
            "message": error_msg,
            "data": []
        }

read_shipments_tool.name = "read_shipments_tool"

@tool
def get_latest_shipments_tool(inputs: ShipmentsToolArgs) -> dict:
    """
    Get the latest/newest shipment records based on created_at timestamp.
    Useful when user asks for "latest shipments", "newest shipments", "recent shipments", etc.
    
    Args:
        inputs: Tool arguments (can include limit parameter, defaults to 2)
        
    Returns:
        dict: Contains success status, message, and data with latest shipments sorted by created_at desc
    """
    try:
        # Convert inputs to dict
        input_dict = inputs.dict() if hasattr(inputs, 'dict') else dict(inputs)
        
        # Extract limit parameter, default to 2
        limit = input_dict.get('limit', 2)
        
        print(f"[LATEST SHIPMENTS TOOL] Calling get_latest_shipments with limit: {limit}")
        
        # Call the CRUD function
        result = get_latest_shipments(limit=limit)
        
        print(f"[LATEST SHIPMENTS TOOL] CRUD result: success={result.get('success')}, count={len(result.get('data', []))}")
        
        return result
        
    except Exception as e:
        error_msg = f"Error in get_latest_shipments_tool: {str(e)}"
        print(f"[LATEST SHIPMENTS TOOL ERROR] {error_msg}")
        traceback.print_exc()
        return {
            "success": False,
            "error": True,
            "message": error_msg,
            "data": []
        }

get_latest_shipments_tool.name = "get_latest_shipments_tool"
get_latest_shipments_tool.description = "Get the latest/newest shipment records based on insertion order. Returns top 5 records by default."

@tool
def get_shipment_by_id_tool(inputs: ShipmentsToolArgs) -> dict:
    """
    Get a specific shipment by its ID or related identifiers.
    
    This tool can search by:
    - MongoDB ObjectId (_id)
    - PH Sales Order
    - Customer PO number
    - Shipment number
    
    Args:
        inputs: Tool arguments containing the ID to search for
        
    Returns:
        dict: Contains success status, message, and data with the found shipment
    """
    try:
        # Convert inputs to dict
        input_dict = inputs.dict() if hasattr(inputs, 'dict') else dict(inputs)
        
        # Look for various ID fields
        shipment_id = (
            input_dict.get('id') or 
            input_dict.get('_id') or 
            input_dict.get('ph_sales_order') or 
            input_dict.get('customer_po_number') or 
            input_dict.get('shipment_number') or
            input_dict.get('shipment_id')
        )
        
        if not shipment_id:
            return {
                "success": False,
                "error": True,
                "message": "No ID provided. Please provide id, ph_sales_order, customer_po_number, or shipment_number",
                "data": None
            }
        
        print(f"[SHIPMENT BY ID TOOL] Calling get_shipment_by_id with ID: {shipment_id}")
        
        # Call the CRUD function
        result = get_shipment_by_id(shipment_id)
        
        print(f"[SHIPMENT BY ID TOOL] CRUD result: success={result.get('success')}")
        
        return result
        
    except Exception as e:
        error_msg = f"Error in get_shipment_by_id_tool: {str(e)}"
        print(f"[SHIPMENT BY ID TOOL ERROR] {error_msg}")
        traceback.print_exc()
        return {
            "success": False,
            "error": True,
            "message": error_msg,
            "data": None
        }

get_shipment_by_id_tool.name = "get_shipment_by_id_tool"
get_shipment_by_id_tool.description = "Get a specific shipment by its ID, PH Sales Order, Customer PO number, or Shipment number."
