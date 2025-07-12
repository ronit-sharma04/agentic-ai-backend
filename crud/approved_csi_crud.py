from db.connection import get_db_connection
from pymongo.errors import PyMongoError, DuplicateKeyError
from bson import ObjectId
import re
import random

COLLECTION = "approved_csi"

def find_in_approved_csi_collection(page: int = 1, **kwargs) -> dict:
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
        print(f"[READ] Total matching records: {total_count}")
        if total_count == 0:
            return {"message": "No Approved CSI Records found.", "data": []}

        limit = 2
        offset = (page - 1) * limit

        docs = list(coll.find(query, {"_id": 0}).skip(offset).limit(limit))

        message = f"{total_count} Approved CSI Records found. Showing page {page} with {len(docs)} records."
        return {"message": message, "data": docs}

    except PyMongoError:
        return {"message": "An unexpected error occurred while fetching the Approved CSI Records.", "data": []}
    except Exception:
        return {"message": "An unexpected error occurred during the operation.", "data": []}
