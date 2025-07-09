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
    read_cases_tool,
    update_csi_tool,
    delete_csi_tool,
)

from tools.render_components_tool import (
    render_create_form_tool,
    render_update_form_tool,
    render_delete_confirmation_tool,
)

load_dotenv()

class CasesAgentState(dict):
    messages: List[dict]

llm = ChatOpenAI(
    model="gpt-4o",
    temperature=0,
)

tools = [
    create_csi_tool,
    read_cases_tool,
    update_csi_tool,
    delete_csi_tool,
]

form_tools_agent = create_react_agent(llm, [
    render_create_form_tool,
    render_update_form_tool,
    render_delete_confirmation_tool,
])
form_tools_react_agent: Runnable = form_tools_agent.with_config({"run_name": "FormToolsAgent"})
cases_agent = create_react_agent(llm, tools)
cases_react_agent: Runnable = cases_agent.with_config({"run_name": "ReActAgent"})


graph = StateGraph(CasesAgentState)
graph.add_node("form_tools", form_tools_react_agent)
graph.add_node("agent", cases_react_agent)
graph.set_entry_point("form_tools")  # Start with intent extraction and form rendering
graph.add_edge("form_tools", "agent")
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
        raise