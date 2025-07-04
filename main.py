# main.py

import os
from dotenv import load_dotenv
from typing import List, Dict, Any
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import create_react_agent
from langchain_core.runnables import Runnable
from langchain_core.messages import BaseMessage
from tools.csi_tools import (
    create_csi_tool,
    read_csi_tool,
    update_csi_tool,
    delete_csi_tool,
    bulk_delete_csi_tool
)   

load_dotenv()

class AgentState(dict):
    messages: List[dict]

llm = ChatOpenAI(
    model="gpt-4o",
    temperature=0,
)

tools = [
    create_csi_tool,
    read_csi_tool,
    update_csi_tool,
    delete_csi_tool,
    bulk_delete_csi_tool,
]
agent = create_react_agent(llm, tools)
react_agent: Runnable = agent.with_config({"run_name": "ReActAgent"})

graph = StateGraph(AgentState)
graph.add_node("agent", react_agent)
graph.set_entry_point("agent")
graph.add_edge("agent", END)
app = graph.compile()

def process_messages(messages: List[Dict[str, Any]], session_id: str = None) -> Dict[str, Any]:
    """
    Stateless: Given a list of messages and a session_id, returns the next assistant message.
    """
    # If you want to use session_id for logging or tool context, you can pass it here.
    result = app.invoke({"messages": messages})
    assistant_message = result["messages"][-1]
    if not isinstance(assistant_message, dict):
        assistant_message = assistant_message.model_dump()
    return assistant_message



# Complete Sample Output:

# {
#   "response": "The new user \"Ronit\" with email \"tauhid@gmail.com\" has been successfully added to the table. The user ID is 12.",
#   "history": [
#     {
#       "role": "system",
#       "content": "You are a helpful assistant who performs CRUD operations on a PostgreSQL database of users.\n    Here is the table schema:\n\n    Table \"public.users\"\n    Column |          Type          | Collation | Nullable |              Default              \n    --------+------------------------+-----------+----------+-----------------------------------\n    id     | integer                |           | not null | nextval('users_id_seq'::regclass)\n    name   | character varying(100) |           | not null | \n    email  | character varying(150) |           | not null | \n\n    Indexes:\n        \"users_pkey\" PRIMARY KEY, btree (id)\n        \"users_email_key\" UNIQUE CONSTRAINT, btree (email)\n    "
#     },
#     {
#       "role": "user",
#       "content": "add a new user in the table with the name Ronit and gmail tauhid@gmail.com"
#     },
#     {
#       "content": "The new user \"Ronit\" with email \"tauhid@gmail.com\" has been successfully added to the table. The user ID is 12.",
#       "additional_kwargs": {
#         "refusal": null
#       },
#       "response_metadata": {
#         "token_usage": {
#           "completion_tokens": 32,
#           "prompt_tokens": 355,
#           "total_tokens": 387,
#           "completion_tokens_details": {
#             "accepted_prediction_tokens": 0,
#             "audio_tokens": 0,
#             "reasoning_tokens": 0,
#             "rejected_prediction_tokens": 0
#           },
#           "prompt_tokens_details": {
#             "audio_tokens": 0,
#             "cached_tokens": 0
#           }
#         },
#         "model_name": "gpt-4-0613",
#         "system_fingerprint": null,
#         "id": "chatcmpl-BpW5QK0BnMkAj1nMwcXJnsUABcSyl",
#         "service_tier": "default",
#         "finish_reason": "stop",
#         "logprobs": null
#       },
#       "type": "ai",
#       "name": null,
#       "id": "run--871258ae-c830-45fc-91eb-44e569112db5-0",
#       "example": false,
#       "tool_calls": [],
#       "invalid_tool_calls": [],
#       "usage_metadata": {
#         "input_tokens": 355,
#         "output_tokens": 32,
#         "total_tokens": 387,
#         "input_token_details": {
#           "audio": 0,
#           "cache_read": 0
#         },
#         "output_token_details": {
#           "audio": 0,
#           "reasoning": 0
#         }
#       }
#     }
#   ]
# }