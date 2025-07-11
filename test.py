import re
from bson import ObjectId

def build_mongo_query(**kwargs) -> dict:
    query = {}
    for k, v in kwargs.items():
        if v is not None:
            if k in ("id", "_id"):
                try:
                    query["_id"] = ObjectId(v)
                except Exception:
                    query["_id"] = v  # fallback if invalid ObjectId
            elif isinstance(v, str):
                pattern = re.escape(v)
                query[k] = {"$regex": pattern, "$options": "i"}
            else:
                query[k] = v
    return query
print(build_mongo_query(_id="686fc60bf19d4a058f9000cb", name="john"))
