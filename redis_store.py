import redis
import json
import os

redis_client = redis.Redis(
    host=os.getenv("REDIS_HOST", "localhost"),
    port=int(os.getenv("REDIS_PORT", 6379)),
    db=int(os.getenv("REDIS_DB", 0)),
    decode_responses=True,
)

def get_message_history(session_id: str) -> list:
    data = redis_client.get(session_id)
    return json.loads(data) if data else []

def save_message_history(session_id: str, messages: list) -> None:
    redis_client.set(session_id, json.dumps(messages))
