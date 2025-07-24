from db.connection import get_db_connection
from pymongo.errors import PyMongoError, DuplicateKeyError
from bson import ObjectId
import re
import random
import datetime
import traceback
import uuid
import logging
from fetch_process_activity_status import fetch_process_activity_status

COLLECTION = "cases"

def filter_timestamp_fields(data):
    """
    Remove timestamp fields from data to return only relevant business data.
    
    Args:
        data: Single dict or list of dicts containing case data
        
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

def read_cases(page: int = 1, **kwargs) -> dict:
    """
    Read CSI cases from the database based on provided filters.
    
    Args:
        page: Page number for pagination
        **kwargs: Filter parameters (field_name=value pairs)
        
    Returns:
        dict: Contains status, message, and data with matched records
    """
    print(f"[CASES READ] Called with kwargs={kwargs}, page={page}")
    try:
        db = get_db_connection(COLLECTION)
        print("[CASES READ] Got DB connection")
        coll = db[COLLECTION]

        # Extract special parameters
        sort_params = kwargs.pop('sort', None)
        limit_param = kwargs.pop('limit', None)
        
        # Build query
        query = {}
        for k, v in kwargs.items():
            if v is not None:
                if k in ("id", "_id"):
                    try:
                        query["_id"] = ObjectId(v)
                    except Exception:
                        query["_id"] = v
                elif isinstance(v, str):
                    pattern = re.escape(v)
                    query[k] = {"$regex": pattern, "$options": "i"}
                else:
                    query[k] = v

        print("[CASES READ] Query:", query)

        total_count = coll.count_documents(query)
        print(f"[CASES READ] Total matching docs: {total_count}")
        
        if total_count == 0:
            return {"status": "success", "message": "No CSI Cases found.", "data": []}

        # Use provided limit or default to pagination limit
        if limit_param:
            limit = int(limit_param)
        else:
            limit = 5
            
        offset = (page - 1) * limit

        # Apply sorting if provided
        if sort_params:
            cursor = coll.find(query, {"_id": 0}).sort(sort_params).skip(offset).limit(limit)
        else:
            cursor = coll.find(query, {"_id": 0}).skip(offset).limit(limit)
            
        docs = list(cursor)

        # Remove empty fields from each document
        cleaned_docs = [
            {k: v for k, v in doc.items() if v not in (None, "", [], {}, ())}
            for doc in docs
        ]
        
        # Filter out timestamp fields from response data
        filtered_docs = filter_timestamp_fields(cleaned_docs)

        message = f"{total_count} Cases found. Showing page {page} with {len(filtered_docs)} Cases."
        return {"status": "success", "message": message, "data": filtered_docs}

    except PyMongoError as e:
        print(f"[CASES READ ERROR] PyMongoError: {e}")
        traceback.print_exc()
        return {"status": "error", "message": "An unexpected error occurred while fetching the Cases.", "data": []}
    except Exception as e:
        print(f"[CASES READ ERROR] Exception: {e}")
        traceback.print_exc()
        return {"status": "error", "message": "An unexpected error occurred during the operation.", "data": []}

def create_case(**kwargs) -> dict:
    """
    Create a new CSI case record in the database.
    
    Args:
        **kwargs: Fields for the new CSI case
        
    Returns:
        dict: Contains status, message, case_id, and the created record data
    """
    print("[CASES CREATE] Called with kwargs:", kwargs)
    try:
        db = get_db_connection(COLLECTION)
        print("[CASES CREATE] Got DB connection")
        coll = db[COLLECTION]

        # Add default fields if not provided
        if "case_id" not in kwargs:
            case_id = f"CSI-{uuid.uuid4().hex[:8].upper()}"
            kwargs["case_id"] = case_id
        else:
            case_id = kwargs["case_id"]
            
        kwargs["csi_status"] = "pending"

        # Add process_activity from n8n
        process_activity = fetch_process_activity_status()
        kwargs["process_activity"] = process_activity

        # Add created_at timestamp (timezone-aware UTC)
        kwargs["created_at"] = datetime.datetime.now(datetime.timezone.utc)

        # Prepare document
        doc = dict(kwargs)
        print("[CASES CREATE] Document to insert:", doc)

        # Insert document
        result = coll.insert_one(doc)
        print(f"[CASES CREATE] Inserted with _id: {result.inserted_id}")

        # Retrieve the inserted document (excluding Mongo _id)
        inserted_doc = coll.find_one({"_id": result.inserted_id}, {"_id": 0})
        
        # Filter out timestamp fields from response data
        filtered_doc = filter_timestamp_fields(inserted_doc)

        return {
            "status": "success",
            "message": f"Case opened successfully with ID: {case_id}",
            "case_id": case_id,
            "data": filtered_doc
        }

    except DuplicateKeyError:
        print("[CASES CREATE] DuplicateKeyError: Case with this case_id already exists.")
        traceback.print_exc()
        return {
            "status": "error",
            "message": "Case with this case_id already exists."
        }
    except PyMongoError as e:
        print("[CASES CREATE ERROR] PyMongoError occurred:", e)
        traceback.print_exc()
        return {
            "status": "error",
            "message": "An unexpected error occurred while creating the Case."
        }
    except Exception as e:
        print("[CASES CREATE ERROR] Generic error:", e)
        traceback.print_exc()
        return {
            "status": "error",
            "message": "An unexpected error occurred during the operation."
        }

def update_case(query_fields: dict = None, update_fields: dict = None, **kwargs) -> dict:
    """
    Update a CSI case record based on query and update fields with maximum flexibility.
    
    Args:
        query_fields: Dictionary of fields to identify the record (optional if using kwargs)
        update_fields: Dictionary of fields to update (optional if using kwargs)
        **kwargs: Additional parameters - can include both query and update fields
                 Use 'query_' prefix for query fields, 'update_' prefix for update fields
        
    Returns:
        dict: Contains status, message, and updated data if successful
    
    Examples:
        # Method 1: Using separate dictionaries
        update_case({"case_id": "CSI-123"}, {"customer_name": "John Doe"})
        
        # Method 2: Using kwargs with prefixes
        update_case(query_case_id="CSI-123", update_customer_name="John Doe")
        
        # Method 3: Mixed approach
        update_case(query_fields={"case_id": "CSI-123"}, update_customer_name="John Doe")
    """
    print(f"[CASES UPDATE] Query fields: {query_fields}")
    print(f"[CASES UPDATE] Update fields: {update_fields}")
    print(f"[CASES UPDATE] Additional kwargs: {kwargs}")
    
    try:
        db = get_db_connection(COLLECTION)
        coll = db[COLLECTION]
        print("[CASES UPDATE] Got DB connection")

        # Build query from multiple sources
        parsed_query = {}
        
        # Add query_fields if provided
        if query_fields:
            for k, v in query_fields.items():
                if v is not None and v != "":
                    parsed_query[k] = v
        
        # Add query fields from kwargs (with query_ prefix)
        for k, v in kwargs.items():
            if k.startswith("query_") and v is not None and v != "":
                field_name = k[6:]  # Remove 'query_' prefix
                parsed_query[field_name] = v
        
        # Process query fields for MongoDB
        final_query = {}
        for k, v in parsed_query.items():
            if k in ("id", "_id"):
                try:
                    final_query["_id"] = ObjectId(v)
                except Exception:
                    final_query["_id"] = v
            elif isinstance(v, str) and k not in ["case_id", "csi_status"]:
                # Use exact match for case_id and csi_status, regex for others
                pattern = re.escape(v)
                final_query[k] = {"$regex": pattern, "$options": "i"}
            else:
                final_query[k] = v

        print("[CASES UPDATE] Final query:", final_query)
        
        if not final_query:
            return {"status": "error", "message": "No query fields provided for update. Please specify which case to update.", "data": []}
        
        # Build update fields from multiple sources
        final_update = {}
        
        # Add update_fields if provided
        if update_fields:
            for k, v in update_fields.items():
                if v is not None and v != "":
                    final_update[k] = v
        
        # Add update fields from kwargs (with update_ prefix)
        for k, v in kwargs.items():
            if k.startswith("update_") and v is not None and v != "":
                field_name = k[7:]  # Remove 'update_' prefix
                final_update[field_name] = v
        
        # Add direct field updates from kwargs (no prefix)
        for k, v in kwargs.items():
            if not k.startswith(("query_", "update_")) and v is not None and v != "":
                # Only add if it's not already in final_update and not a query field
                if k not in final_update and k not in parsed_query:
                    final_update[k] = v
            
        if not final_update:
            return {"status": "error", "message": "No update fields provided. Please specify what to update.", "data": []}

        # Check if record exists
        existing_doc = coll.find_one(final_query)
        if not existing_doc:
            query_desc = ", ".join([f"{k}={v}" for k, v in parsed_query.items()])
            return {"status": "error", "message": f"No matching Case found with {query_desc}. Update not performed.", "data": []}

        # Add modification timestamp
        final_update["modified_at"] = datetime.datetime.now(datetime.timezone.utc)
        
        print("[CASES UPDATE] Final update fields:", final_update)

        # Perform update
        result = coll.update_one({"_id": existing_doc["_id"]}, {"$set": final_update})
        
        if result.modified_count > 0:
            updated_doc = coll.find_one({"_id": existing_doc["_id"]}, {"_id": 0})
            # Clean up empty fields
            cleaned_doc = {k: v for k, v in updated_doc.items() if v not in (None, "", [], {}, ())}
            
            # Filter out timestamp fields from response data
            filtered_doc = filter_timestamp_fields(cleaned_doc)
            
            updated_fields = ", ".join(final_update.keys())
            return {
                "status": "success", 
                "message": f"Case updated successfully. Modified fields: {updated_fields}", 
                "data": filtered_doc
            }
        else:
            # No actual changes made (values were the same)
            existing_clean = {k: v for k, v in existing_doc.items() if k != "_id" and v not in (None, "", [], {}, ())}
            
            # Filter out timestamp fields from response data
            filtered_existing = filter_timestamp_fields(existing_clean)
            
            return {
                "status": "warning", 
                "message": "No changes made to the Case (values were already the same).", 
                "data": filtered_existing
            }

    except PyMongoError as e:
        print(f"[CASES UPDATE ERROR] PyMongoError: {e}")
        traceback.print_exc()
        return {"status": "error", "message": "Database error occurred while updating the Case.", "data": []}
    except Exception as e:
        print(f"[CASES UPDATE ERROR] Exception: {e}")
        traceback.print_exc()
        return {"status": "error", "message": "An unexpected error occurred during the update operation.", "data": []}

def delete_case(query_fields: dict) -> dict:
    """
    Delete a CSI case record based on query fields.
    
    Args:
        query_fields: Dictionary of fields to identify the record to delete
        
    Returns:
        dict: Contains status and message
    """
    print("[CASES DELETE] Called with query_fields:", query_fields)
    try:
        db = get_db_connection(COLLECTION)
        coll = db[COLLECTION]
        print("[CASES DELETE] Got DB connection")
        
        # Build query
        parsed_query = {}
        for k, v in query_fields.items():
            if v is not None:
                if k in ("id", "_id"):
                    try:
                        parsed_query["_id"] = ObjectId(v)
                    except Exception:
                        parsed_query["_id"] = v
                elif isinstance(v, str):
                    pattern = re.escape(v)
                    parsed_query[k] = {"$regex": pattern, "$options": "i"}
                else:
                    parsed_query[k] = v
                    
        if not parsed_query:
            return {"status": "error", "message": "No query fields provided for deletion.", "data": []}
            
        # Pre-check
        found = coll.find_one(parsed_query)
        if not found:
            return {"status": "error", "message": "No matching Case found. Deletion not performed.", "data": []}
        
        # Delete
        result = coll.delete_one(parsed_query)
        if result.deleted_count > 0:
            return {"status": "success", "message": "Case deleted successfully.", "data": []}
        else:
            return {"status": "error", "message": "Deletion failed.", "data": []}
    
    except PyMongoError as e:
        print(f"[CASES DELETE ERROR] PyMongoError: {e}")
        traceback.print_exc()
        return {"status": "error", "message": "An unexpected error occurred while deleting the Case.", "data": []}
    except Exception as e:
        print(f"[CASES DELETE ERROR] Exception: {e}")
        traceback.print_exc()
        return {"status": "error", "message": "An unexpected error occurred during the operation.", "data": []}

def approve_case(case_id: str = None, **kwargs) -> dict:
    """
    Approve a CSI case and move it to the approved_csi collection.
    
    Args:
        case_id: ID of the case to approve
        **kwargs: Additional fields to update during approval
        
    Returns:
        dict: Contains success, message, and data of the approved case
    """
    logging.info(f"[CASES APPROVE] Called with case_id: {case_id}, kwargs: {kwargs}")
    try:
        db = get_db_connection(COLLECTION)
        logging.info("[CASES APPROVE] Got DB connection")
        coll = db[COLLECTION]

        # Validate case_id
        if not case_id:
            logging.error("[CASES APPROVE] case_id is required for approval")
            return {"success": False, "message": "case_id is required for approval.", "data": []}

        # Find the case
        logging.info(f"[CASES APPROVE] Looking for case: {case_id}")
        case = coll.find_one({"case_id": case_id})
        if not case:
            logging.error(f"[CASES APPROVE] Case {case_id} not found")
            return {"success": False, "message": f"Case with ID {case_id} not found.", "data": []}

        logging.info(f"[CASES APPROVE] Found case: {case_id}, current status: {case.get('csi_status')}")

        # Check if already approved
        if case.get('csi_status') == 'approved':
            logging.warning(f"[CASES APPROVE] Case {case_id} is already approved")
            case_data = dict(case)
            case_data.pop("_id", None)
            
            # Filter out timestamp fields from response data
            filtered_case_data = filter_timestamp_fields(case_data)
            
            return {
                "success": True, 
                "message": f"Case {case_id} is already approved.",
                "data": filtered_case_data
            }

        # Update the case status
        approval_time = datetime.datetime.now(datetime.timezone.utc)
        update_data = {
            "csi_status": "approved", 
            "approved_at": approval_time,
            "modified_at": approval_time
        }
        
        # Add any additional fields from kwargs
        update_data.update(kwargs)
        
        logging.info(f"[CASES APPROVE] Updating case {case_id} with approval data")
        result = coll.update_one(
            {"case_id": case_id},
            {"$set": update_data}
        )
        
        if result.modified_count == 0:
            logging.error(f"[CASES APPROVE] Failed to update case {case_id}")
            return {"success": False, "message": f"Failed to update case {case_id} status.", "data": []}

        # Get updated case
        updated_case = coll.find_one({"case_id": case_id})
        if not updated_case:
            logging.error(f"[CASES APPROVE] Failed to retrieve updated case {case_id}")
            return {"success": False, "message": f"Failed to retrieve updated case after approval.", "data": []}

        # Copy to approved_csi collection
        logging.info(f"[CASES APPROVE] Copying case {case_id} to approved_csi collection")
        approved_coll = db["approved_csi"]
        case_copy = dict(updated_case)
        case_copy.pop("_id")  # Remove MongoDB _id
        
        try:
            approved_coll.insert_one(case_copy)
            logging.info(f"[CASES APPROVE] Successfully inserted case {case_id} into approved_csi")
        except DuplicateKeyError:
            # If case already exists in approved_csi, update it instead
            approved_coll.replace_one({"case_id": case_id}, case_copy, upsert=True)
            logging.info(f"[CASES APPROVE] Case {case_id} already existed in approved_csi, updated instead")
        except Exception as e:
            logging.error(f"[CASES APPROVE] Error copying to approved_csi: {str(e)}")
            return {"success": False, "message": f"Case approved but failed to copy to approved_csi: {str(e)}", "data": []}

        # Return the case without MongoDB _id
        case_data = dict(updated_case)
        case_data.pop("_id", None)
        
        # Filter out timestamp fields from response data
        filtered_case_data = filter_timestamp_fields(case_data)
        
        logging.info(f"[CASES APPROVE] Successfully approved case {case_id}")
        return {
            "success": True, 
            "message": f"Case {case_id} has been approved and moved to approved_csi collection.",
            "data": filtered_case_data
        }

    except PyMongoError as e:
        logging.error(f"[CASES APPROVE ERROR] PyMongoError: {e}")
        logging.error(traceback.format_exc())
        return {"success": False, "message": f"Database error during approval: {str(e)}", "data": []}
    except Exception as e:
        logging.error(f"[CASES APPROVE ERROR] Exception: {e}")
        logging.error(traceback.format_exc())
        return {"success": False, "message": f"An unexpected error occurred during approval: {str(e)}", "data": []}


def get_latest_cases(limit: int = 2) -> dict:
    """
    Get the latest/newest CSI cases based on created_at timestamp.
    
    Args:
        limit: Number of latest cases to return (default: 2)
        
    Returns:
        dict: Contains success, message, and data with latest cases
    """
    logging.info(f"[GET LATEST CASES] Called with limit: {limit}")
    try:
        db = get_db_connection(COLLECTION)
        logging.info("[GET LATEST CASES] Got DB connection")
        coll = db[COLLECTION]
        
        # Query for latest cases sorted by created_at descending
        cursor = coll.find({}).sort("created_at", -1).limit(limit)
        cases = list(cursor)
        
        if not cases:
            logging.info("[GET LATEST CASES] No cases found")
            return {
                "success": True,
                "message": "No cases found in the database.",
                "data": []
            }
        
        # Remove MongoDB _id from results
        for case in cases:
            case.pop("_id", None)
        
        # Filter out timestamp fields from response data
        filtered_cases = filter_timestamp_fields(cases)
        
        logging.info(f"[GET LATEST CASES] Found {len(filtered_cases)} latest cases")
        return {
            "success": True,
            "message": f"Found {len(filtered_cases)} latest cases.",
            "data": filtered_cases
        }
        
    except PyMongoError as e:
        logging.error(f"[GET LATEST CASES ERROR] PyMongoError: {e}")
        logging.error(traceback.format_exc())
        return {"success": False, "message": f"Database error: {str(e)}", "data": []}
    except Exception as e:
        logging.error(f"[GET LATEST CASES ERROR] Exception: {e}")
        logging.error(traceback.format_exc())
        return {"success": False, "message": f"An unexpected error occurred: {str(e)}", "data": []}


def get_case_by_id(case_id: str) -> dict:
    """
    Helper function to get a case by its case_id.
    
    Args:
        case_id: ID of the case to retrieve
        
    Returns:
        dict: Contains status, message, and data of the found case
    """
    print(f"[CASES GET_BY_ID] Called with case_id: {case_id}")
    try:
        db = get_db_connection(COLLECTION)
        coll = db[COLLECTION]
        case = coll.find_one({"case_id": case_id})
        if not case:
            return {"status": "error", "message": f"Case with ID {case_id} not found.", "data": []}
            
        # Convert ObjectId to string and prepare response
        case_data = dict(case)
        case_data["_id"] = str(case_data["_id"])  # Convert ObjectId to string
        
        return {"status": "success", "message": "Case found.", "data": case_data}
        
    except PyMongoError as e:
        print(f"[CASES GET_BY_ID ERROR] PyMongoError: {e}")
        traceback.print_exc()
        return {"status": "error", "message": f"An error occurred while retrieving the case: {str(e)}", "data": []}
    except Exception as e:
        print(f"[CASES GET_BY_ID ERROR] Exception: {e}")
        traceback.print_exc()
        return {"status": "error", "message": f"An unexpected error occurred during the operation.", "data": []}


def get_case_object_id_by_query(query: dict) -> str:
    """
    Returns the ObjectId (as string) of the first matching case, or None.
    
    Args:
        query: Dictionary of fields to identify the record
        
    Returns:
        str: String representation of the ObjectId or None if not found
    """
    print("[CASES GET_OBJECT_ID] Called with query:", query)
    try:
        db = get_db_connection(COLLECTION)
        coll = db[COLLECTION]
        doc = coll.find_one(query)
        print("[CASES GET_OBJECT_ID] Found document:", doc)
        
        if doc and "_id" in doc:
            return str(doc["_id"])
        return None
        
    except PyMongoError as e:
        print(f"[CASES GET_OBJECT_ID ERROR] PyMongoError: {e}")
        traceback.print_exc()
        return None
    except Exception as e:
        print(f"[CASES GET_OBJECT_ID ERROR] Exception: {e}")
        traceback.print_exc()
        return None