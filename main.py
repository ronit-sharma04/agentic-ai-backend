import os
from dotenv import load_dotenv
from typing import TypedDict, List, Union
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import create_react_agent
from langchain_core.runnables import Runnable
from langchain_core.messages import BaseMessage
from tools.user_tools import (
    create_user_tool,
    read_user_tool,
    update_user_tool,
    delete_user_tool,
)
from redis_store import get_message_history, save_message_history

load_dotenv()

# Define the type of agent state
class AgentState(TypedDict):
    messages: List[dict]

# Load model
llm = ChatOpenAI(
    model="gpt-4",
    temperature=0,
)

# Define tools and create agent
tools = [create_user_tool, read_user_tool, update_user_tool, delete_user_tool]
agent = create_react_agent(llm, tools)
react_agent: Runnable = agent.with_config({"run_name": "ReActAgent"})

# Create the LangGraph
graph = StateGraph(AgentState)
graph.add_node("agent", react_agent)
graph.set_entry_point("agent")
graph.add_edge("agent", END)
app = graph.compile()

# Helper: Convert all messages to dicts for Redis storage
def serialize_messages(messages: List[Union[dict, BaseMessage]]) -> List[dict]:
    return [
        msg if isinstance(msg, dict) else msg.model_dump()
        for msg in messages
    ]

if __name__ == "__main__":
    session_id = "demo-session"  # Replace this with dynamic session/user ID in production

    while True:
        try:
            user_input = input("\n> ")
            if user_input.lower() in ["exit", "quit"]:
                print("[System] Exiting...")
                break

            # Load conversation history from Redis
            chat_history = get_message_history(session_id)

            # Inject system prompt only once
            if not chat_history:
                chat_history.append({
                    "role": "system",
                    "content": """You are a helpful assistant who performs CRUD operations on a PostgreSQL database of users.
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
                    """
                })

            # Add user message
            chat_history.append({"role": "user", "content": user_input})

            # Run through the agent
            result = app.invoke({"messages": chat_history})

            # Get assistant's reply
            assistant_message = result["messages"][-1]
            if not isinstance(assistant_message, dict):
                assistant_message = assistant_message.model_dump()

            # Append and persist the message
            chat_history.append(assistant_message)
            save_message_history(session_id, serialize_messages(chat_history))

            # Output final reply
            print("[OUTPUT]", assistant_message["content"])

        except Exception as e:
            print("[ERROR]", e)