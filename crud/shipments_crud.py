from db.connection import get_db_connection, get_db_collection
from pymongo.errors import PyMongoError
from bson import ObjectId
import re
import datetime
import traceback
import logging

COLLECTION = "shipments"

def filter_timestamp_fields(data):
    """
    Remove timestamp fields from data to return only relevant business data.
    
    Args:
        data: Single dict or list of dicts containing shipment data
        
    Returns:
        Filtered data without timestamp fields
    """
    timestamp_fields = {'created_at', 'modified_at', 'approved_at', 'create_date', 'modify_date'}
    
    def filter_single_record(record):
        if isinstance(record, dict):
            return {k: v for k, v in record.items() if k not in timestamp_fields}
        return record
    
    if isinstance(data, list):
        return [filter_single_record(record) for record in data]
    else:
        return filter_single_record(data)

def read_shipments(page: int = 1, **kwargs) -> dict:
    """
    Read shipments from the database based on provided filters.
    
    Args:
        page: Page number for pagination
        **kwargs: Filter parameters (field_name=value pairs)
        
    Returns:
        dict: Contains status, message, and data with matched records
    """
    print(f"[SHIPMENTS READ] Called with kwargs={kwargs}, page={page}")
    try:
        # Use optimized connection pooling
        coll = get_db_collection(COLLECTION)
        print("[SHIPMENTS READ] Got DB collection from connection pool")
        
        # Build query from non-empty kwargs
        query = {}
        for key, value in kwargs.items():
            if value and value != "":
                # Handle ObjectId for _id field
                if key in ["id", "_id"]:
                    try:
                        query["_id"] = ObjectId(value)
                    except Exception:
                        query["_id"] = value
                else:
                    # Use regex for string fields for flexible matching
                    if isinstance(value, str):
                        query[key] = {"$regex": value, "$options": "i"}
                    else:
                        query[key] = value
        
        print(f"[SHIPMENTS READ] Built query: {query}")
        
        # Calculate pagination
        per_page = 2
        skip = (page - 1) * per_page
        
        # Execute query with pagination
        cursor = coll.find(query).skip(skip).limit(per_page)
        results = list(cursor)
        
        # Remove ObjectId from results for JSON serialization
        for result in results:
            if "_id" in result:
                result["_id"] = str(result["_id"])
        
        # Filter timestamp fields from results
        results = filter_timestamp_fields(results)
        
        count = len(results)
        print(f"[SHIPMENTS READ] Found {count} records on page {page}")
        
        return {
            "success": True,
            "message": f"Found {count} shipment records on page {page}",
            "data": results
        }
        
    except PyMongoError as e:
        error_msg = f"Database error in read_shipments: {str(e)}"
        print(f"[SHIPMENTS READ ERROR] {error_msg}")
        return {
            "success": False,
            "error": True,
            "message": error_msg,
            "data": []
        }
    except Exception as e:
        error_msg = f"Unexpected error in read_shipments: {str(e)}"
        print(f"[SHIPMENTS READ ERROR] {error_msg}")
        traceback.print_exc()
        return {
            "success": False,
            "error": True,
            "message": error_msg,
            "data": []
        }

def get_latest_shipments(limit: int = 5) -> dict:
    """
    Get the latest/newest shipments based on creation timestamp.
    
    Args:
        limit: Number of latest shipments to return (default: 5)
        
    Returns:
        dict: Contains success, message, and data with latest shipments
    """
    print(f"[SHIPMENTS LATEST] Called with limit={limit}")
    try:
        coll = get_db_collection(COLLECTION)
        
        # Get latest records sorted by created_at field in descending order
        cursor = coll.find({}).sort("created_at", -1).limit(limit)
        results = list(cursor)
        
        # Remove ObjectId from results for JSON serialization
        for result in results:
            if "_id" in result:
                result["_id"] = str(result["_id"])
        
        # Filter timestamp fields from results
        results = filter_timestamp_fields(results)
        
        count = len(results)
        print(f"[SHIPMENTS LATEST] Found {count} latest records")
        
        return {
            "success": True,
            "message": f"Found {count} latest shipment records",
            "data": results
        }
        
    except PyMongoError as e:
        error_msg = f"Database error in get_latest_shipments: {str(e)}"
        print(f"[SHIPMENTS LATEST ERROR] {error_msg}")
        return {
            "success": False,
            "error": True,
            "message": error_msg,
            "data": []
        }
    except Exception as e:
        error_msg = f"Unexpected error in get_latest_shipments: {str(e)}"
        print(f"[SHIPMENTS LATEST ERROR] {error_msg}")
        traceback.print_exc()
        return {
            "success": False,
            "error": True,
            "message": error_msg,
            "data": []
        }

def get_shipment_by_id(shipment_id: str) -> dict:
    """
    Helper function to get a shipment by its ID.
    
    Args:
        shipment_id: ID of the shipment to retrieve
        
    Returns:
        dict: Contains status, message, and data of the found shipment
    """
    print(f"[SHIPMENTS GET BY ID] Called with shipment_id={shipment_id}")
    try:
        coll = get_db_collection(COLLECTION)
        
        # Try to find by ObjectId first, then by string ID
        query = {}
        try:
            query["_id"] = ObjectId(shipment_id)
        except:
            # If not a valid ObjectId, search by any field that might contain the ID
            query = {"$or": [
                {"PH Sales Order": {"$regex": shipment_id, "$options": "i"}},
                {"Customer PO number": {"$regex": shipment_id, "$options": "i"}},
                {"Shipment number": {"$regex": shipment_id, "$options": "i"}}
            ]}
        
        result = coll.find_one(query)
        
        if result:
            if "_id" in result:
                result["_id"] = str(result["_id"])
            
            # Filter timestamp fields from result
            result = filter_timestamp_fields(result)
            
            return {
                "success": True,
                "message": f"Found shipment with ID: {shipment_id}",
                "data": result
            }
        else:
            return {
                "success": False,
                "message": f"No shipment found with ID: {shipment_id}",
                "data": None
            }
            
    except Exception as e:
        error_msg = f"Error in get_shipment_by_id: {str(e)}"
        print(f"[SHIPMENTS GET BY ID ERROR] {error_msg}")
        traceback.print_exc()
        return {
            "success": False,
            "error": True,
            "message": error_msg,
            "data": None
        }
