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
    approve_cases_tool,
    update_cases_tool
)
from tools.send_email_tool import bdm_send_email_tool
from tools.approved_csi_tools import read_approved_csi_tool
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
    create_cases_tool,
    read_cases_tool,
    approve_cases_tool,
    read_approved_csi_tool,
    update_cases_tool,
    bdm_send_email_tool
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
