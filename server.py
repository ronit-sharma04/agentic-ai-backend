from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any
from main import process_messages
from redis_store import get_message_history, save_message_history

import datetime

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

class ChatSimpleResponse(BaseModel):
    response: str

SYSTEM_PROMPT = {
    "role": "system",
    "content": """
You are a helpful, conversational assistant that performs CRUD operations on a PostgreSQL database of users.
You have access to the full conversation history and should use it to provide context-aware, helpful responses.
If the user asks about previous actions or updates, summarize or reference what happened earlier in this session.

Here is the table schema:

Table "public.users"
Column |          Type          | Collation | Nullable |              Default              
--------+------------------------+-----------+----------+-----------------------------------
id     | integer                |           | not null | nextval('users_id_seq'::regclass)
name   | character varying(100) |           | not null | 
email  | character varying(150) |           | not null | 

Indexes:
    "users_pkey" PRIMARY KEY, btree (id)
    "users_email_key" UNIQUE CONSTRAINT, btree (email)

You can respond to past interactions by referencing the chat history that i provide you in the system prompt.
"""
}

def log(msg: str):
    print(f"[{datetime.datetime.now().isoformat()}] {msg}")

@app.post("/chat", response_model=ChatSimpleResponse)
async def chat_endpoint(req: ChatRequest):
    process_id = f"{req.session_id}-{datetime.datetime.now().strftime('%Y%m%d%H%M%S%f')}"
    log(f"=== PROCESS START [{process_id}] ===")
    try:
        log(f"[{process_id}] Loading chat history for session: {req.session_id}")

        chat_history = get_message_history(req.session_id)
        log(f"[{process_id}] History loaded: {chat_history}")

        if not chat_history:
            log(f"[{process_id}] No history found, injecting system prompt.")
            chat_history = [SYSTEM_PROMPT]
        else:
            log(f"[{process_id}] Loaded {len(chat_history)} previous messages.")

        log(f"[{process_id}] Appending user message: {req.message}")
        chat_history.append({"role": "user", "content": req.message})

        log(f"[{process_id}] Calling LangGraph process_messages()")
        assistant_message = process_messages(chat_history, session_id=req.session_id)
        log(f"[{process_id}] Assistant response: {assistant_message.get('content', '')}")

        chat_history.append(assistant_message)

        log(f"[{process_id}] Saving updated chat history ({len(chat_history)} messages)")
        save_message_history(req.session_id, chat_history)

        log(f"=== PROCESS END [{process_id}] ===\n")
        return ChatSimpleResponse(
            response=assistant_message["content"]
        )
    except Exception as e:
        log(f"=== PROCESS ERROR [{process_id}] === {e}\n")
        raise HTTPException(status_code=500, detail=str(e))