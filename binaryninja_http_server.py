#!/usr/bin/env python3
"""
Binary Ninja MCP Server (HTTP Client Version)

This server provides an interface for Cline to analyze binary files using the Binary Ninja HTTP API.
It connects to a running Binary Ninja instance (personal license) on localhost:9009.
"""

import sys
import json
import traceback
import os
import logging
from binaryninja_http_client import BinaryNinjaHTTPClient

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('BinaryNinjaMCPServer')

def read_json():
    """Read a JSON object from stdin."""
    line = sys.stdin.readline()
    if not line:
        sys.exit(0)
    return json.loads(line)

def write_json(response):
    """Write a JSON object to stdout."""
    print(json.dumps(response), flush=True)

def handle_request(request, client):
    """Handle an MCP request using the Binary Ninja HTTP client."""
    try:
        method = request.get("method")
        params = request.get("params", {})

        if method == "ping":
            ping_result = client.ping()
            if ping_result["status"] == "connected":
                return {"result": "pong"}
            else:
                return {"error": f"Failed to connect to Binary Ninja server: {ping_result.get('error', 'Unknown error')}"}

        elif method == "list_functions":
            path = params.get("path")
            if not path:
                return {"error": "Path parameter is required"}
                
            functions = client.list_functions(path)
            func_names = [f["name"] for f in functions]
            return {"result": func_names}

        elif method == "disassemble_function":
            path = params.get("path")
            func_name = params.get("function")
            if not path or not func_name:
                return {"error": "Path and function parameters are required"}
                
            disasm = client.get_disassembly(path, function_name=func_name)
            return {"result": disasm}
            
        elif method == "get_binary_info":
            path = params.get("path")
            if not path:
                return {"error": "Path parameter is required"}
                
            file_info = client.get_file_info(path)
            
            # Format the response to match the original API
            info = {
                "filename": file_info.get("filename", ""),
                "architecture": file_info.get("arch", {}).get("name", "unknown"),
                "platform": file_info.get("platform", {}).get("name", "unknown"),
                "entry_point": hex(file_info.get("entry_point", 0)),
                "file_size": file_info.get("file_size", 0),
                "is_executable": file_info.get("executable", False),
                "is_relocatable": file_info.get("relocatable", False),
                "address_size": file_info.get("address_size", 0)
            }
            return {"result": info}
            
        elif method == "list_sections":
            path = params.get("path")
            if not path:
                return {"error": "Path parameter is required"}
                
            sections_data = client.get_sections(path)
            
            # Format the response to match the original API
            sections = []
            for section in sections_data:
                sections.append({
                    "name": section.get("name", ""),
                    "start": hex(section.get("start", 0)),
                    "end": hex(section.get("end", 0)),
                    "size": section.get("length", 0),
                    "semantics": section.get("semantics", "")
                })
            return {"result": sections}
            
        elif method == "get_xrefs":
            path = params.get("path")
            func_name = params.get("function")
            if not path or not func_name:
                return {"error": "Path and function parameters are required"}
                
            # First get the function info to get its address
            function = client.get_function(path, function_name=func_name)
            if not function:
                return {"error": f"Function '{func_name}' not found"}
                
            # Then get the xrefs to that address
            xrefs_data = client.get_xrefs(path, function.get("start", 0))
            
            # Format the response to match the original API
            refs = []
            for xref in xrefs_data:
                # Get the function that contains this xref
                caller_addr = xref.get("from", 0)
                try:
                    # This is a simplification - in a real implementation we would
                    # need to find the function that contains this address
                    caller_func = client.get_function(path, function_address=caller_addr)
                    refs.append({
                        "from_function": caller_func.get("name", "unknown"),
                        "from_address": hex(caller_addr),
                        "to_address": hex(xref.get("to", 0))
                    })
                except Exception:
                    # Skip this xref if we can't get the caller function
                    pass
            
            return {"result": refs}
            
        elif method == "get_strings":
            path = params.get("path")
            min_length = params.get("min_length", 4)
            if not path:
                return {"error": "Path parameter is required"}
                
            strings_data = client.get_strings(path, min_length=min_length)
            
            # Format the response to match the original API
            strings = []
            for string in strings_data:
                strings.append({
                    "value": string.get("value", ""),
                    "address": hex(string.get("address", 0)),
                    "length": len(string.get("value", "")),
                    "type": string.get("type", "")
                })
            
            return {"result": strings}
            
        elif method == "decompile_function":
            path = params.get("path")
            func_name = params.get("function")
            if not path or not func_name:
                return {"error": "Path and function parameters are required"}
                
            # Get the function info
            function = client.get_function(path, function_name=func_name)
            if not function:
                return {"error": f"Function '{func_name}' not found"}
                
            # Get the decompiled code
            hlil = client.get_hlil(path, function_name=func_name)
            
            # Format the response to match the original API
            return {
                "result": {
                    "name": function.get("name", ""),
                    "signature": function.get("type", ""),
                    "decompiled_code": "\n".join(hlil) if isinstance(hlil, list) else str(hlil),
                    "address": hex(function.get("start", 0))
                }
            }
            
        elif method == "get_types":
            path = params.get("path")
            if not path:
                return {"error": "Path parameter is required"}
                
            types_data = client.get_types(path)
            
            # Format the response to match the original API
            # This is a simplified version - the actual implementation would need to
            # parse the types data from the Binary Ninja HTTP API
            types = []
            for type_name, type_info in types_data.items():
                type_obj = {
                    "name": type_name,
                    "type_class": type_info.get("type_class", "unknown"),
                    "type_string": type_info.get("type_string", "")
                }
                
                if type_info.get("type_class") == "structure":
                    type_obj["size"] = type_info.get("size", 0)
                    type_obj["members"] = []
                    for member in type_info.get("members", []):
                        type_obj["members"].append({
                            "name": member.get("name", ""),
                            "type": member.get("type", ""),
                            "offset": member.get("offset", 0)
                        })
                
                types.append(type_obj)
            
            return {"result": types}
            
        elif method == "generate_header":
            # This is a more complex operation that would require additional implementation
            # For now, we'll return a simplified version
            return {"error": "Method not implemented in HTTP client version"}
            
        elif method == "generate_source":
            # This is a more complex operation that would require additional implementation
            # For now, we'll return a simplified version
            return {"error": "Method not implemented in HTTP client version"}
            
        elif method == "rebuild_driver":
            # This is a more complex operation that would require additional implementation
            # For now, we'll return a simplified version
            return {"error": "Method not implemented in HTTP client version"}

        return {"error": f"Unknown method: {method}"}

    except Exception as e:
        logger.error(f"Error handling request: {e}")
        logger.error(traceback.format_exc())
        return {
            "error": str(e),
            "traceback": traceback.format_exc()
        }

def main():
    """Main function to run the MCP server."""
    logger.info("Starting Binary Ninja MCP Server (HTTP Client Version)")
    
    # Create the Binary Ninja HTTP client
    client = BinaryNinjaHTTPClient()
    
    # Test the connection to the Binary Ninja server
    ping_result = client.ping()
    if ping_result["status"] != "connected":
        logger.error(f"Failed to connect to Binary Ninja server: {ping_result.get('error', 'Unknown error')}")
        sys.exit(1)
        
    logger.info(f"Connected to Binary Ninja server (binary loaded: {ping_result.get('loaded', False)})")
    
    # Process requests
    while True:
        try:
            req = read_json()
            res = handle_request(req, client)
            res["id"] = req.get("id")
            write_json(res)
        except Exception as e:
            logger.error(f"Error processing request: {e}")
            logger.error(traceback.format_exc())
            sys.exit(1)

if __name__ == "__main__":
    main()
