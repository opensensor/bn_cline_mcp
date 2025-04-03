#!/usr/bin/env python3
"""
Binary Ninja MCP Server

This is the main entry point for the Binary Ninja MCP server.
It integrates the HTTP server and client components to provide a complete MCP server implementation.
"""

import sys
import json
import traceback
import os
import logging
from binaryninja_http_client import BinaryNinjaHTTPClient

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('BinaryNinjaMCPServer')

# Create a file handler to log to a file
file_handler = logging.FileHandler('/tmp/binaryninja_mcp_server.log')
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
logger.addHandler(file_handler)

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
        
        # Log the request method and parameters
        logger.debug(f"Handling method: {method}")
        logger.debug(f"Parameters: {json.dumps(params)}")

        # MCP Protocol Methods
        if method == "list_tools":
            # Return the list of available tools
            return {
                "result": {
                    "tools": [
                        {
                            "name": "get_binary_info",
                            "description": "Get information about a binary file",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "path": {
                                        "type": "string",
                                        "description": "Path to the binary file"
                                    }
                                },
                                "required": ["path"]
                            }
                        },
                        {
                            "name": "list_functions",
                            "description": "List all functions in a binary file",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "path": {
                                        "type": "string",
                                        "description": "Path to the binary file"
                                    }
                                },
                                "required": ["path"]
                            }
                        },
                        {
                            "name": "disassemble_function",
                            "description": "Disassemble a function in a binary file",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "path": {
                                        "type": "string",
                                        "description": "Path to the binary file"
                                    },
                                    "function": {
                                        "type": "string",
                                        "description": "Name of the function to disassemble"
                                    }
                                },
                                "required": ["path", "function"]
                            }
                        },
                        {
                            "name": "decompile_function",
                            "description": "Decompile a function to C code",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "path": {
                                        "type": "string",
                                        "description": "Path to the binary file"
                                    },
                                    "function": {
                                        "type": "string",
                                        "description": "Name of the function to decompile"
                                    }
                                },
                                "required": ["path", "function"]
                            }
                        }
                    ]
                }
            }
            
        elif method == "list_resources":
            # Return the list of available resources
            return {
                "result": {
                    "resources": []  # No static resources available
                }
            }
            
        elif method == "list_resource_templates":
            # Return the list of available resource templates
            return {
                "result": {
                    "resourceTemplates": [
                        {
                            "uriTemplate": "binary://{path}/info",
                            "name": "Binary Information",
                            "description": "Information about a binary file"
                        },
                        {
                            "uriTemplate": "binary://{path}/functions",
                            "name": "Functions",
                            "description": "List of functions in a binary file"
                        },
                        {
                            "uriTemplate": "binary://{path}/function/{name}",
                            "name": "Function Disassembly",
                            "description": "Disassembly of a function in a binary file"
                        }
                    ]
                }
            }
            
        elif method == "read_resource":
            uri = params.get("uri", "")
            logger.debug(f"Reading resource: {uri}")
            
            # Parse the URI
            if uri.startswith("binary://"):
                # Remove the protocol
                path = uri[9:]
                
                # Check if it's a function disassembly
                if "/function/" in path:
                    # Extract the path and function name
                    parts = path.split("/function/")
                    if len(parts) != 2:
                        return {"error": "Invalid URI format"}
                    
                    binary_path = parts[0]
                    function_name = parts[1]
                    
                    # Get the disassembly
                    disasm_result = handle_request({
                        "method": "disassemble_function",
                        "params": {
                            "path": binary_path,
                            "function": function_name
                        }
                    }, client)
                    
                    if "error" in disasm_result:
                        return disasm_result
                    
                    return {
                        "result": {
                            "contents": [
                                {
                                    "uri": uri,
                                    "mimeType": "text/plain",
                                    "text": "\n".join(disasm_result["result"])
                                }
                            ]
                        }
                    }
                
                # Check if it's a functions list
                elif path.endswith("/functions"):
                    # Extract the binary path
                    binary_path = path[:-10]  # Remove "/functions"
                    
                    # Get the functions
                    functions_result = handle_request({
                        "method": "list_functions",
                        "params": {
                            "path": binary_path
                        }
                    }, client)
                    
                    if "error" in functions_result:
                        return functions_result
                    
                    return {
                        "result": {
                            "contents": [
                                {
                                    "uri": uri,
                                    "mimeType": "application/json",
                                    "text": json.dumps(functions_result["result"])
                                }
                            ]
                        }
                    }
                
                # Check if it's binary info
                elif path.endswith("/info"):
                    # Extract the binary path
                    binary_path = path[:-5]  # Remove "/info"
                    
                    # Get the binary info
                    info_result = handle_request({
                        "method": "get_binary_info",
                        "params": {
                            "path": binary_path
                        }
                    }, client)
                    
                    if "error" in info_result:
                        return info_result
                    
                    return {
                        "result": {
                            "contents": [
                                {
                                    "uri": uri,
                                    "mimeType": "application/json",
                                    "text": json.dumps(info_result["result"])
                                }
                            ]
                        }
                    }
            
            return {"error": f"Unknown resource URI: {uri}"}
            
        elif method == "call_tool":
            tool_name = params.get("name")
            tool_args = params.get("arguments", {})
            
            logger.debug(f"Calling tool: {tool_name}")
            logger.debug(f"Arguments: {json.dumps(tool_args)}")
            
            # Map the tool name to the corresponding method
            if tool_name == "get_binary_info":
                return handle_request({
                    "method": "get_binary_info",
                    "params": tool_args
                }, client)
            elif tool_name == "list_functions":
                return handle_request({
                    "method": "list_functions",
                    "params": tool_args
                }, client)
            elif tool_name == "disassemble_function":
                return handle_request({
                    "method": "disassemble_function",
                    "params": tool_args
                }, client)
            elif tool_name == "decompile_function":
                return handle_request({
                    "method": "decompile_function",
                    "params": tool_args
                }, client)
            else:
                return {"error": f"Unknown tool: {tool_name}"}
        
        # Binary Ninja API Methods
        elif method == "ping":
            ping_result = client.ping()
            if ping_result["status"] == "connected":
                return {"result": "pong"}
            else:
                return {"error": f"Failed to connect to Binary Ninja server: {ping_result.get('error', 'Unknown error')}"}

        elif method == "get_binary_info":
            path = params.get("path")
            if not path:
                return {"error": "Path parameter is required"}
                
            # We assume the binary is already loaded
            # Just log the path for debugging
            logger.info(f"Using binary: {path}")
                
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

        elif method == "list_functions":
            path = params.get("path")
            if not path:
                return {"error": "Path parameter is required"}
                
            # We assume the binary is already loaded
            # Just log the path for debugging
            logger.info(f"Using binary: {path}")
                
            functions = client.list_functions(path)
            func_names = [f["name"] for f in functions]
            return {"result": func_names}

        elif method == "disassemble_function":
            path = params.get("path")
            func_name = params.get("function")
            if not path or not func_name:
                return {"error": "Path and function parameters are required"}
                
            # We assume the binary is already loaded
            # Just log the path for debugging
            logger.info(f"Using binary: {path}")
                
            disasm = client.get_disassembly(path, function_name=func_name)
            return {"result": disasm}
            
        elif method == "list_sections":
            path = params.get("path")
            if not path:
                return {"error": "Path parameter is required"}
                
            # We assume the binary is already loaded
            # Just log the path for debugging
            logger.info(f"Using binary: {path}")
                
            sections_data = client.get_sections(path)
            
            # Format the response to match the original API
            sections = []
            for section in sections_data:
                # Handle the case where start, end, and length might be strings
                start = section.get("start", 0)
                end = section.get("end", 0)
                length = section.get("length", 0)
                
                # Convert to integers if they are strings
                if isinstance(start, str):
                    try:
                        start = int(start, 0)  # Base 0 means it will detect hex or decimal
                    except ValueError:
                        start = 0
                        
                if isinstance(end, str):
                    try:
                        end = int(end, 0)  # Base 0 means it will detect hex or decimal
                    except ValueError:
                        end = 0
                        
                if isinstance(length, str):
                    try:
                        length = int(length, 0)  # Base 0 means it will detect hex or decimal
                    except ValueError:
                        length = 0
                
                sections.append({
                    "name": section.get("name", ""),
                    "start": hex(start),
                    "end": hex(end),
                    "size": length,
                    "semantics": section.get("semantics", "")
                })
            return {"result": sections}
            
        elif method == "get_xrefs":
            path = params.get("path")
            func_name = params.get("function")
            if not path or not func_name:
                return {"error": "Path and function parameters are required"}
                
            # We assume the binary is already loaded
            # Just log the path for debugging
            logger.info(f"Using binary: {path}")
                
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
                
            # We assume the binary is already loaded
            # Just log the path for debugging
            logger.info(f"Using binary: {path}")
                
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
                
            # We assume the binary is already loaded
            # Just log the path for debugging
            logger.info(f"Using binary: {path}")
                
            # Get the function info
            function = client.get_function(path, function_name=func_name)
            if not function:
                return {"error": f"Function '{func_name}' not found"}
                
            # Get the decompiled code
            try:
                hlil = client.get_hlil(path, function_name=func_name)
                decompiled_code = "\n".join(hlil) if isinstance(hlil, list) else str(hlil)
            except Exception as e:
                logger.warning(f"Failed to decompile function: {e}")
                decompiled_code = "// Decompilation not available in personal license\n// or Binary Ninja server is not running."
            
            # Format the response to match the original API
            return {
                "result": {
                    "name": function.get("name", ""),
                    "signature": function.get("type", ""),
                    "decompiled_code": decompiled_code,
                    "address": hex(function.get("start", 0))
                }
            }
            
        elif method == "get_types":
            path = params.get("path")
            if not path:
                return {"error": "Path parameter is required"}
                
            # We assume the binary is already loaded
            # Just log the path for debugging
            logger.info(f"Using binary: {path}")
                
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
            path = params.get("path")
            output_path = params.get("output_path")
            include_functions = params.get("include_functions", True)
            include_types = params.get("include_types", True)
            
            if not path:
                return {"error": "Path parameter is required"}
                
            # We assume the binary is already loaded
            # Just log the path for debugging
            logger.info(f"Using binary: {path}")
                
            # This is a placeholder implementation
            # In a real implementation, we would generate a header file with function prototypes and type definitions
            header_content = "// Generated header file\n\n"
            
            # Add include guards
            header_content += "#ifndef GENERATED_HEADER_H\n"
            header_content += "#define GENERATED_HEADER_H\n\n"
            
            # Add standard includes
            header_content += "#include <stdint.h>\n"
            header_content += "#include <stdbool.h>\n\n"
            
            # Add types if requested
            if include_types:
                types_data = client.get_types(path)
                if types_data:
                    header_content += "// Types\n"
                    for type_name, type_info in types_data.items():
                        if type_info.get("type_class") == "structure":
                            header_content += f"typedef struct {type_name} {{\n"
                            for member in type_info.get("members", []):
                                header_content += f"    {member.get('type', 'void')} {member.get('name', 'unknown')}; // offset: {member.get('offset', 0)}\n"
                            header_content += f"}} {type_name};\n\n"
                        else:
                            header_content += f"typedef {type_info.get('type_string', 'void')} {type_name};\n"
                    header_content += "\n"
            
            # Add function prototypes if requested
            if include_functions:
                functions = client.list_functions(path)
                if functions:
                    header_content += "// Function prototypes\n"
                    for func in functions:
                        # Get the function info
                        function = client.get_function(path, function_name=func["name"])
                        if function:
                            header_content += f"{function.get('type', 'void')} {function.get('name', 'unknown')}();\n"
                    header_content += "\n"
            
            # Close include guards
            header_content += "#endif // GENERATED_HEADER_H\n"
            
            # Write to file if output_path is provided
            if output_path:
                try:
                    with open(output_path, "w") as f:
                        f.write(header_content)
                except Exception as e:
                    logger.error(f"Failed to write header file: {e}")
                    return {"error": f"Failed to write header file: {e}"}
            
            return {"result": header_content}
            
        elif method == "generate_source":
            path = params.get("path")
            output_path = params.get("output_path")
            header_path = params.get("header_path", "generated_header.h")
            
            if not path:
                return {"error": "Path parameter is required"}
                
            # We assume the binary is already loaded
            # Just log the path for debugging
            logger.info(f"Using binary: {path}")
                
            # This is a placeholder implementation
            # In a real implementation, we would generate a source file with function implementations
            source_content = "// Generated source file\n\n"
            
            # Add include for the header file
            source_content += f"#include \"{header_path}\"\n\n"
            
            # Add function implementations
            functions = client.list_functions(path)
            if functions:
                for func in functions:
                    # Get the function info
                    function = client.get_function(path, function_name=func["name"])
                    if function:
                        # Get the decompiled code
                        try:
                            hlil = client.get_hlil(path, function_name=func["name"])
                            decompiled_code = "\n".join(hlil) if isinstance(hlil, list) else str(hlil)
                        except Exception as e:
                            logger.warning(f"Failed to decompile function: {e}")
                            decompiled_code = "// Decompilation not available in personal license\n// or Binary Ninja server is not running."
                        
                        source_content += f"// Function: {function.get('name', 'unknown')}\n"
                        source_content += f"// Address: {hex(function.get('start', 0))}\n"
                        source_content += f"{function.get('type', 'void')} {function.get('name', 'unknown')}() {{\n"
                        source_content += f"    // TODO: Implement this function\n"
                        source_content += f"    // Decompiled code:\n"
                        source_content += f"    /*\n"
                        for line in decompiled_code.split("\n"):
                            source_content += f"    {line}\n"
                        source_content += f"    */\n"
                        source_content += f"}}\n\n"
            
            # Write to file if output_path is provided
            if output_path:
                try:
                    with open(output_path, "w") as f:
                        f.write(source_content)
                except Exception as e:
                    logger.error(f"Failed to write source file: {e}")
                    return {"error": f"Failed to write source file: {e}"}
            
            return {"result": source_content}
            
        elif method == "rebuild_driver":
            path = params.get("path")
            output_dir = params.get("output_dir")
            
            if not path:
                return {"error": "Path parameter is required"}
                
            if not output_dir:
                return {"error": "Output directory parameter is required"}
                
            # We assume the binary is already loaded
            # Just log the path for debugging
            logger.info(f"Using binary: {path}")
                
            # This is a placeholder implementation
            # In a real implementation, we would generate a complete driver module
            try:
                os.makedirs(output_dir, exist_ok=True)
                
                # Generate header file
                header_path = os.path.join(output_dir, "driver.h")
                header_result = handle_request({
                    "method": "generate_header",
                    "params": {
                        "path": path,
                        "output_path": header_path
                    }
                }, client)
                
                if "error" in header_result:
                    return {"error": f"Failed to generate header file: {header_result['error']}"}
                
                # Generate source file
                source_path = os.path.join(output_dir, "driver.c")
                source_result = handle_request({
                    "method": "generate_source",
                    "params": {
                        "path": path,
                        "output_path": source_path,
                        "header_path": "driver.h"
                    }
                }, client)
                
                if "error" in source_result:
                    return {"error": f"Failed to generate source file: {source_result['error']}"}
                
                # Generate Makefile
                makefile_path = os.path.join(output_dir, "Makefile")
                with open(makefile_path, "w") as f:
                    f.write("# Generated Makefile\n\n")
                    f.write("obj-m := driver.o\n\n")
                    f.write("all:\n")
                    f.write("\tmake -C /lib/modules/$(shell uname -r)/build M=$(PWD) modules\n\n")
                    f.write("clean:\n")
                    f.write("\tmake -C /lib/modules/$(shell uname -r)/build M=$(PWD) clean\n")
                
                return {
                    "result": {
                        "header_file": header_path,
                        "source_files": [source_path],
                        "makefile": makefile_path
                    }
                }
            except Exception as e:
                logger.error(f"Failed to rebuild driver: {e}")
                return {"error": f"Failed to rebuild driver: {e}"}

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
    logger.info("Starting Binary Ninja MCP Server")
    
    # Log all environment variables for debugging
    logger.debug("Environment variables:")
    for key, value in os.environ.items():
        logger.debug(f"  {key}={value}")
    
    # Create the Binary Ninja HTTP client
    client = BinaryNinjaHTTPClient()
    
    # Test the connection to the Binary Ninja server
    ping_result = client.ping()
    if ping_result["status"] != "connected":
        logger.error(f"Failed to connect to Binary Ninja server: {ping_result.get('error', 'Unknown error')}")
        # Don't exit, continue anyway to support the MCP protocol
        logger.warning("Continuing anyway to support the MCP protocol")
    else:
        logger.info(f"Connected to Binary Ninja server (binary loaded: {ping_result.get('loaded', False)})")
    
    # Log that we're ready to receive requests
    logger.info("Ready to receive MCP requests")
    
    # Process requests
    while True:
        try:
            # Log that we're waiting for a request
            logger.debug("Waiting for request...")
            
            # Read the request from stdin
            req = read_json()
            logger.debug(f"Received request: {json.dumps(req)}")
            
            # Handle the request
            res = handle_request(req, client)
            res["id"] = req.get("id")
            
            # Log the response
            logger.debug(f"Sending response: {json.dumps(res)}")
            
            # Write the response to stdout
            write_json(res)
        except json.JSONDecodeError as e:
            logger.error(f"Error decoding JSON: {e}")
            logger.error(f"Input was: {sys.stdin.readline()}")
            # Continue processing requests
        except Exception as e:
            logger.error(f"Error processing request: {e}")
            logger.error(traceback.format_exc())
            # Don't exit, continue processing requests
            logger.warning("Continuing to process requests...")

if __name__ == "__main__":
    main()
