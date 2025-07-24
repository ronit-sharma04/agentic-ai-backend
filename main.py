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
    create_cases_tool,
    read_cases_tool,
    approve_case_tool,
    update_case_tool,
    delete_case_tool,
    get_latest_cases_tool
)
from tools.approved_csi_tools import (
    read_approved_csi_tool,
    get_latest_approved_csi_tool
)
from tools.send_email_tool import bdm_send_email_tool
from tools.dynamic_updates_tool import fetch_mandatory_fields_tool, fetch_process_activity_tool
from langchain_core.output_parsers import JsonOutputKeyToolsParser
from pydantic import BaseModel
from typing import Literal, Optional


load_dotenv()

class CasesAgentState(dict):
    messages: List[dict]

class ChatSimpleMessage(BaseModel):
    text: str
    action: Literal["show-message", "render-create-csi-form", "render-update-csi-form"]
    data: Optional[List[Dict[str, Any]]] = []

class ChatSimpleResponse(BaseModel):
    role: Literal["assistant"]
    message: ChatSimpleMessage

llm = ChatOpenAI(
    model="gpt-4o",
    temperature=0,
)
tools = [
    # CSI Case operations (draft/pending records)
    create_cases_tool,  # Create new draft CSI cases
    read_cases_tool,    # Read/search draft CSI cases
    update_case_tool,   # Update existing draft CSI cases
    delete_case_tool,   # Delete draft CSI cases
    approve_case_tool,  # Approve a case and move to approved_csi collection
    get_latest_cases_tool,  # Get latest/newest CSI cases by creation timestamp
    
    # Approved CSI operations (final/read-only records)
    read_approved_csi_tool,  # Read/search approved CSI records
    get_latest_approved_csi_tool,  # Get latest/newest approved CSI records by creation timestamp
    
    # Support tools
    bdm_send_email_tool,      # Send email notifications
    fetch_mandatory_fields_tool,  # Get required fields for case creation
    fetch_process_activity_tool   # Get current process activity status
]

cases_agent = create_react_agent(llm, tools)

cases_react_agent: Runnable = cases_agent.with_config({"run_name": "ReActAgent"})


graph = StateGraph(CasesAgentState)
graph.add_node("agent", cases_react_agent)
graph.set_entry_point("agent")  # Start with intent extraction and form rendering
graph.add_edge("agent", END)
app = graph.compile()
# import logging

# # Configure logging
# logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
def process_messages(
    messages: List[Dict[str, Any]],
    session_id: str = None
) -> Dict[str, Any]:
    try:
        result = app.invoke({"messages": messages})
        # print("Agent final Result:", result)

        assistant_message = result["messages"][-1]

        if not isinstance(assistant_message, dict):
            assistant_message = assistant_message.model_dump()

        return assistant_message

    except Exception as e:
        raise Exception(f"Error processing messages: {e}") from e
