from db.connection import get_db_connection
from pymongo.errors import PyMongoError, DuplicateKeyError
from bson import ObjectId
import re
import random
import datetime
import traceback
import uuid
from fetch_process_activity_status import fetch_process_activity_status

COLLECTION = "cases"

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

        message = f"{total_count} Cases found. Showing page {page} with {len(cleaned_docs)} Cases."
        return {"status": "success", "message": message, "data": cleaned_docs}

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

        return {
            "status": "success",
            "message": f"Case opened successfully with ID: {case_id}",
            "case_id": case_id,
            "data": inserted_doc
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

def update_case(query_fields: dict, update_fields: dict) -> dict:
    """
    Update a CSI case record based on query and update fields.
    
    Args:
        query_fields: Dictionary of fields to identify the record
        update_fields: Dictionary of fields to update
        
    Returns:
        dict: Contains status, message, and updated data if successful
    """
    print(f"[CASES UPDATE] Query fields: {query_fields}")
    print(f"[CASES UPDATE] Update fields: {update_fields}")
    try:
        db = get_db_connection(COLLECTION)
        coll = db[COLLECTION]
        print("[CASES UPDATE] Got DB connection")

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

        print("[CASES UPDATE] Parsed query fields:", parsed_query)
        
        if not parsed_query:
            return {"status": "error", "message": "No query fields provided for update.", "data": []}
            
        if not update_fields:
            return {"status": "error", "message": "No update fields provided.", "data": []}

        # Check if record exists
        existing_doc = coll.find_one(parsed_query)
        if not existing_doc:
            return {"status": "error", "message": "No matching Case found. Update not performed.", "data": []}

        # Update modification timestamp
        update_fields["modified_at"] = datetime.datetime.now(datetime.timezone.utc)

        # Perform update
        result = coll.update_one({"_id": existing_doc["_id"]}, {"$set": update_fields})
        if result.modified_count > 0:
            updated_doc = coll.find_one({"_id": existing_doc["_id"]}, {"_id": 0})
            return {"status": "success", "message": "Case updated successfully.", "data": updated_doc}
        else:
            return {"status": "warning", "message": "No changes made to the Case.", "data": existing_doc}

    except PyMongoError as e:
        print(f"[CASES UPDATE ERROR] PyMongoError: {e}")
        traceback.print_exc()
        return {"status": "error", "message": "An unexpected error occurred while updating the Case.", "data": []}
    except Exception as e:
        print(f"[CASES UPDATE ERROR] Exception: {e}")
        traceback.print_exc()
        return {"status": "error", "message": "An unexpected error occurred during the operation.", "data": []}

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
        dict: Contains status, message, and data of the approved case
    """
    print(f"[CASES APPROVE] Called with case_id: {case_id}, kwargs: {kwargs}")
    try:
        db = get_db_connection(COLLECTION)
        print("[CASES APPROVE] Got DB connection")
        coll = db[COLLECTION]

        # Get case_id
        if not case_id:
            return {"status": "error", "message": "case_id is required for approval.", "data": []}

        # Find the case
        case = coll.find_one({"case_id": case_id})
        if not case:
            return {"status": "error", "message": f"Case with ID {case_id} not found.", "data": []}

        # Update the case status
        approval_time = datetime.datetime.now(datetime.timezone.utc)
        update_data = {
            "csi_status": "approved", 
            "approved_at": approval_time,
            "modified_at": approval_time
        }
        
        # Add any additional fields from kwargs
        update_data.update(kwargs)
        
        coll.update_one(
            {"case_id": case_id},
            {"$set": update_data}
        )

        # Get updated case
        updated_case = coll.find_one({"case_id": case_id})
        if not updated_case:
            return {"status": "error", "message": f"Failed to retrieve updated case after approval.", "data": []}

        # Copy to approved_csi collection
        approved_coll = db["approved_csi"]
        case_copy = dict(updated_case)
        case_copy.pop("_id")  # Remove MongoDB _id
        
        try:
            approved_coll.insert_one(case_copy)
        except DuplicateKeyError:
            # If case already exists in approved_csi, update it instead
            approved_coll.replace_one({"case_id": case_id}, case_copy, upsert=True)
            print(f"[CASES APPROVE] Case {case_id} already existed in approved_csi, updated instead")

        # Return the case without MongoDB _id
        case_data = dict(updated_case)
        case_data.pop("_id", None)
        
        return {
            "status": "success", 
            "message": f"Case {case_id} has been approved and moved to approved_csi collection.",
            "data": case_data
        }

    except PyMongoError as e:
        print(f"[CASES APPROVE ERROR] PyMongoError: {e}")
        traceback.print_exc()
        return {"status": "error", "message": f"An error occurred during approval: {str(e)}", "data": []}
    except Exception as e:
        print(f"[CASES APPROVE ERROR] Exception: {e}")
        traceback.print_exc()
        return {"status": "error", "message": f"An unexpected error occurred during the operation.", "data": []}


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