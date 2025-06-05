import json
import logging
from typing import Dict, Any, List

from .llm_adapter import get_llm_adapter
from swisper_core import get_logger

logger = get_logger(__name__)

def orchestrate_tools(user_message: str, tools_needed: List[str]) -> str:
    """Orchestrate tool usage using LLM reasoning"""
    
    try:
        from mcp_server.swisper_mcp import create_mcp_server
        mcp_server = create_mcp_server()
        available_tools = mcp_server.list_tools()["tools"]
        
        system_prompt = f"""You are a tool orchestrator for the Swisper AI assistant. 
        
Available tools:
{json.dumps(available_tools, indent=2)}

The user has made a request that requires tool usage. Plan and execute the appropriate sequence of tool calls to fulfill their request.

Respond with a plan and execute it step by step. For each tool call, use this format:
TOOL_CALL: tool_name(arguments)
RESULT: [tool result]

Then provide a final summary of what was accomplished."""

        user_prompt = f"User request: {user_message}\nSuggested tools: {tools_needed}"
        
        llm_adapter = get_llm_adapter()
        response = llm_adapter.chat_completion([
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ])
        
        executed_response = _execute_tool_calls(response, mcp_server)
        
        return executed_response
        
    except Exception as e:
        logger.error(f"Tool orchestration failed: {e}")
        return f"Sorry, I couldn't complete your request using the available tools. Error: {str(e)}"

def _execute_tool_calls(llm_response: str, mcp_server) -> str:
    """Execute tool calls mentioned in LLM response"""
    
    lines = llm_response.split('\n')
    result_lines = []
    
    for line in lines:
        if line.startswith('TOOL_CALL:'):
            tool_call = line[10:].strip()
            try:
                if '(' in tool_call and ')' in tool_call:
                    tool_name = tool_call.split('(')[0].strip()
                    args_str = tool_call.split('(')[1].split(')')[0]
                    
                    try:
                        args = json.loads(f'{{{args_str}}}')
                    except:
                        args = {"query": args_str.strip('"')}
                    
                    result = mcp_server.call_tool(tool_name, args)
                    result_lines.append(f"TOOL_CALL: {tool_call}")
                    result_lines.append(f"RESULT: {json.dumps(result, indent=2)}")
                else:
                    result_lines.append(line)
            except Exception as e:
                result_lines.append(f"TOOL_CALL: {tool_call}")
                result_lines.append(f"RESULT: Error - {str(e)}")
        else:
            result_lines.append(line)
    
    return '\n'.join(result_lines)
