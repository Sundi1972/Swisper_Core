#!/usr/bin/env python3
"""
Swisper MCP Server - Model Context Protocol implementation for tool discovery
"""

import json
import os
import sys
from typing import Dict, Any, List

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def create_mcp_server():
    """Create a simple MCP-compatible server without external dependencies"""
    
    class SwisperMCPServer:
        def __init__(self):
            self.tools = {
                "search_products": {
                    "description": "Search for products using SearchAPI.io with fallback to mock data",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "Product search query"}
                        },
                        "required": ["query"]
                    }
                },
                "analyze_product_attributes": {
                    "description": "Analyze products to extract key differentiating attributes",
                    "parameters": {
                        "type": "object", 
                        "properties": {
                            "products": {"type": "array", "description": "List of product objects"},
                            "product_type": {"type": "string", "description": "Product category"}
                        },
                        "required": ["products"]
                    }
                },
                "check_compatibility": {
                    "description": "Check product compatibility against user constraints",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "products": {"type": "array", "description": "List of products"},
                            "constraints": {"type": "object", "description": "User constraints"},
                            "product_type": {"type": "string", "description": "Product category"}
                        },
                        "required": ["products", "constraints"]
                    }
                },
                "filter_products_by_preferences": {
                    "description": "Filter products based on user preferences",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "products": {"type": "array", "description": "List of products"},
                            "preferences": {"type": "array", "description": "User preferences"}
                        },
                        "required": ["products", "preferences"]
                    }
                },
                "websearch": {
                    "description": "Search the web for current information using SearchAPI with T5 summarization",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "Web search query"}
                        },
                        "required": ["query"]
                    }
                }
            }
        
        def list_tools(self) -> Dict[str, Any]:
            """List available tools"""
            return {"tools": self.tools}
        
        def call_tool(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
            """Call a specific tool"""
            try:
                if name == "search_products":
                    return self._search_products(arguments.get("query", ""))
                elif name == "analyze_product_attributes":
                    return self._analyze_attributes(arguments.get("products", []), arguments.get("product_type"))
                elif name == "check_compatibility":
                    return self._check_compatibility(arguments.get("products", []), arguments.get("constraints", {}), arguments.get("product_type"))
                elif name == "filter_products_by_preferences":
                    return self._filter_products(arguments.get("products", []), arguments.get("preferences", []))
                elif name == "websearch":
                    return self._websearch(arguments.get("query", ""))
                else:
                    return {"success": False, "error": f"Unknown tool: {name}"}
            except Exception as e:
                return {"success": False, "error": str(e)}
        
        def _search_products(self, query: str) -> Dict[str, Any]:
            """Search for products using SearchAPI"""
            try:
                from tool_adapter.mock_google import google_shopping_search
                results = google_shopping_search(query)
                return {
                    "success": True,
                    "products": results,
                    "count": len(results) if results else 0
                }
            except Exception as e:
                return {"success": False, "error": str(e), "products": []}
        
        def _analyze_attributes(self, products: List[Dict[str, Any]], product_type: str = None) -> Dict[str, Any]:
            """Analyze products to extract attributes"""
            try:
                from contract_engine.llm_helpers import analyze_product_differences
                analysis = analyze_product_differences(products)
                return {"success": True, "analysis": analysis, "product_count": len(products)}
            except Exception as e:
                return {"success": False, "error": str(e), "analysis": ""}
        
        def _check_compatibility(self, products: List[Dict[str, Any]], constraints: Dict[str, Any], product_type: str = None) -> Dict[str, Any]:
            """Check product compatibility"""
            try:
                from contract_engine.llm_helpers import check_product_compatibility
                results = check_product_compatibility(products, constraints, product_type)
                return {
                    "success": True,
                    "compatibility_results": results,
                    "compatible_count": sum(1 for r in results if r.get("compatible", False))
                }
            except Exception as e:
                return {"success": False, "error": str(e), "compatibility_results": []}
        
        def _filter_products(self, products: List[Dict[str, Any]], preferences: List[str]) -> Dict[str, Any]:
            """Filter products by preferences"""
            try:
                from contract_engine.llm_helpers import filter_products_with_llm
                filtered = filter_products_with_llm(products, preferences, [])
                return {
                    "success": True,
                    "filtered_products": filtered,
                    "original_count": len(products),
                    "filtered_count": len(filtered)
                }
            except Exception as e:
                return {"success": False, "error": str(e), "filtered_products": products}
        
        def _websearch(self, query: str) -> Dict[str, Any]:
            """Search the web using websearch pipeline"""
            try:
                from websearch_pipeline.websearch_pipeline import create_websearch_pipeline
                pipeline = create_websearch_pipeline()
                if pipeline:
                    result = pipeline.run(query=query)
                    return {
                        "success": True,
                        "summary": result.get("summary", "No information found."),
                        "sources": result.get("sources", []),
                        "query": query
                    }
                else:
                    return {"success": False, "error": "WebSearch pipeline not available"}
            except Exception as e:
                return {"success": False, "error": str(e), "summary": ""}
    
    return SwisperMCPServer()

def main():
    """Main entry point for MCP server"""
    server = create_mcp_server()
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        if command == "list":
            print(json.dumps(server.list_tools(), indent=2))
        elif command == "call" and len(sys.argv) > 3:
            tool_name = sys.argv[2]
            try:
                args = json.loads(sys.argv[3])
                result = server.call_tool(tool_name, args)
                print(json.dumps(result, indent=2))
            except json.JSONDecodeError:
                print(json.dumps({"success": False, "error": "Invalid JSON arguments"}, indent=2))
        else:
            print("Usage: python swisper_mcp.py [list|call <tool_name> <json_args>]")
    else:
        print("Swisper MCP Server - Available commands:")
        print("  list - List available tools")
        print("  call <tool_name> <json_args> - Call a specific tool")

if __name__ == "__main__":
    main()
