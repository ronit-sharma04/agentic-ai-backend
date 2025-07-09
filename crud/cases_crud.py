from db.connection import get_db_connection
from pymongo.errors import PyMongoError, DuplicateKeyError
from bson import ObjectId
import re

COLLECTION = "cases"
from bson import ObjectId

def read_cases(page: int = 1, **kwargs) -> dict:
    print(f"[READ] Called with kwargs={kwargs}, page={page}")
    try:
        db = get_db_connection(COLLECTION)
        print("[READ] Got DB connection")
        coll = db[COLLECTION]

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

        print("[READ] Query:", query)

        total_count = coll.count_documents(query)
        print(f"[READ] Total matching docs: {total_count}")
        if total_count == 0:
            return {"message": "No CSI records found.", "data": []}

        limit = 5
        offset = (page - 1) * limit

        docs = list(coll.find(query, {"_id": 0}).skip(offset).limit(limit))

        message = f"{total_count} records found. Showing page {page} with {len(docs)} records."
        return {"message": message, "data": docs}

    except PyMongoError:
        return {"message": "An unexpected error occurred while fetching the records.", "data": []}
    except Exception:
        return {"message": "An unexpected error occurred during the operation.", "data": []}
    
def create_csi(**kwargs) -> str:
    print("[CREATE] Called with kwargs:", kwargs)
    try:
        db = get_db_connection(COLLECTION)
        print("[CREATE] Got DB connection")
        coll = db[COLLECTION]

        # Generate a new ObjectId
        _id = ObjectId()
        kwargs["_id"] = _id

        # Prepare document
        doc = dict(kwargs)
        print("[CREATE] Document to insert:", doc)

        # Insert document
        result = coll.insert_one(doc)
        print(f"[CREATE] Inserted with _id: {result.inserted_id}")
        return f"CSI row created with _id: {_id}"
    except DuplicateKeyError:
        print("[CREATE] DuplicateKeyError: Record with this _id already exists.")
        return '[CREATE ERROR] Record with this _id already exists.'
    except PyMongoError as e:
        print("[CREATE ERROR] PyMongoError occurred:", e)
        return "[CREATE ERROR] An unexpected error occurred while creating the record."
    except Exception as e:
        print("[CREATE ERROR] Generic error:", e)
        return "[CREATE ERROR] An unexpected error occurred during the operation."

# ...existing code...

def update_csi(csi_id: str, **kwargs) -> dict:
    print("[UPDATE] Called with csi_id:", csi_id, "kwargs:", kwargs)
    try:
        db = get_db_connection(COLLECTION)
        coll = db[COLLECTION]
        # Remove csi_id from kwargs if present
        kwargs.pop("csi_id", None)
        # Check if record exists
        existing = coll.find_one({"csi_id": csi_id})
        if not existing:
            return {"message": "Record not found. Update not performed.", "data": []}
        # Perform update
        result = coll.update_one({"csi_id": csi_id}, {"$set": kwargs})
        if result.modified_count > 0:
            return {"message": "Record updated successfully.", "data": []}
        else:
            return {"message": "No changes made to the record.", "data": []}
    except PyMongoError:
        return {"message": "An unexpected error occurred while updating the record.", "data": []}
    except Exception:
        return {"message": "An unexpected error occurred during the operation.", "data": []}

def delete_csi(**kwargs) -> dict:
    print("[DELETE] Called with kwargs:", kwargs)
    try:
        db = get_db_connection(COLLECTION)
        coll = db[COLLECTION]
        # Build query
        query = {}
        for k, v in kwargs.items():
            if v is not None:
                if k in ("id", "_id"):
                    try:
                        query["_id"] = ObjectId(v)
                    except Exception:
                        query["_id"] = v
                else:
                    query[k] = v
        # Pre-check
        found = coll.find_one(query)
        if not found:
            return {"message": "No matching record found. Deletion not performed.", "data": []}
        # Delete
        result = coll.delete_one(query)
        if result.deleted_count > 0:
            return {"message": "Record deleted successfully.", "data": []}
        else:
            return {"message": "Deletion failed.", "data": []}
    except PyMongoError:
        return {"message": "An unexpected error occurred while deleting the record.", "data": []}
    except Exception:
        return {"message": "An unexpected error occurred during the operation.", "data": []}


def get_case_object_id_by_query(query: dict) -> str:
    """
    Returns the ObjectId (as string) of the first matching case, or None.
    """
    print("[GET CASE OBJECT ID] Called with query:", query)
    db = get_db_connection(COLLECTION)
    coll = db[COLLECTION]
    doc = coll.find_one(query)
    print("[GET CASE OBJECT ID] Found document:", doc)
    if doc and "_id" in doc:
        return str(doc["_id"])
    return None