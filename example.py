#!/usr/bin/env python3
"""
Example script demonstrating how to use the Binary Ninja MCP server.
This script shows how to analyze a binary file using the Binary Ninja API.

Usage:
    python3 example.py <path_to_binary> [output_dir]

The path_to_binary parameter is required for the MCP server to identify which binary to analyze.
If output_dir is provided, source code reconstruction will save files there.
"""

import sys
import json
import subprocess
import os
import tempfile

def send_request(server_process, method, params=None):
    """Send a request to the Binary Ninja MCP server."""
    if params is None:
        params = {}
    
    request = {
        "id": 1,
        "method": method,
        "params": params
    }
    
    server_process.stdin.write(json.dumps(request) + "\n")
    server_process.stdin.flush()
    
    response = json.loads(server_process.stdout.readline())
    return response

def main():
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <path_to_binary> [output_dir]")
        sys.exit(1)
    
    binary_path = os.path.abspath(sys.argv[1])
    if not os.path.exists(binary_path):
        print(f"Error: Binary file '{binary_path}' not found")
        sys.exit(1)
    
    # Start the Binary Ninja MCP server
    server_path = os.path.join(os.path.dirname(__file__), "binaryninja_server.py")
    server_process = subprocess.Popen(
        ["python3", server_path],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1
    )
    
    try:
        # Test the server connection
        response = send_request(server_process, "ping")
        if response.get("result") != "pong":
            print("Error: Failed to connect to the Binary Ninja MCP server")
            sys.exit(1)
        
        print("Connected to Binary Ninja MCP server")
        
        # Get binary information
        print("\n=== Binary Information ===")
        response = send_request(server_process, "get_binary_info", {"path": binary_path})
        if "error" in response:
            print(f"Error: {response['error']}")
            sys.exit(1)
        
        info = response["result"]
        print(f"Filename: {info['filename']}")
        print(f"Architecture: {info['architecture']}")
        print(f"Platform: {info['platform']}")
        print(f"Entry Point: {info['entry_point']}")
        print(f"File Size: {info['file_size']} bytes")
        print(f"Executable: {info['is_executable']}")
        print(f"Relocatable: {info['is_relocatable']}")
        print(f"Address Size: {info['address_size']} bits")
        
        # List sections
        print("\n=== Sections ===")
        response = send_request(server_process, "list_sections", {"path": binary_path})
        if "error" in response:
            print(f"Error: {response['error']}")
            sys.exit(1)
        
        sections = response["result"]
        for section in sections:
            print(f"{section['name']}: {section['start']} - {section['end']} ({section['size']} bytes) [{section['semantics']}]")
        
        # List functions
        print("\n=== Functions ===")
        response = send_request(server_process, "list_functions", {"path": binary_path})
        if "error" in response:
            print(f"Error: {response['error']}")
            sys.exit(1)
        
        functions = response["result"]
        for i, func in enumerate(functions[:10]):  # Show only first 10 functions
            print(f"{i+1}. {func}")
        
        if len(functions) > 10:
            print(f"... and {len(functions) - 10} more functions")
        
        # If there are functions, disassemble the first one
        if functions:
            func_name = functions[0]
            print(f"\n=== Disassembly of '{func_name}' ===")
            response = send_request(server_process, "disassemble_function", {
                "path": binary_path,
                "function": func_name
            })
            if "error" in response:
                print(f"Error: {response['error']}")
                sys.exit(1)
            
            disasm = response["result"]
            for i, instr in enumerate(disasm):
                print(f"{i+1:3d}. {instr}")
            
            # Get cross-references to this function
            print(f"\n=== Cross-references to '{func_name}' ===")
            response = send_request(server_process, "get_xrefs", {
                "path": binary_path,
                "function": func_name
            })
            if "error" in response:
                print(f"Error: {response['error']}")
                sys.exit(1)
            
            xrefs = response["result"]
            if xrefs:
                for xref in xrefs:
                    print(f"From: {xref['from_function']} at {xref['from_address']} to {xref['to_address']}")
            else:
                print("No cross-references found")
        
        # Get strings
        print("\n=== Strings ===")
        response = send_request(server_process, "get_strings", {
            "path": binary_path,
            "min_length": 5
        })
        if "error" in response:
            print(f"Error: {response['error']}")
            sys.exit(1)
        
        strings = response["result"]
        for i, string in enumerate(strings[:10]):  # Show only first 10 strings
            print(f"{i+1}. {string['address']}: '{string['value']}'")
        
        if len(strings) > 10:
            print(f"... and {len(strings) - 10} more strings")
            
        # Source Code Reconstruction
        if len(sys.argv) > 2:
            output_dir = sys.argv[2]
            os.makedirs(output_dir, exist_ok=True)
            
            # Decompile the first function
            if functions:
                func_name = functions[0]
                print(f"\n=== Decompiled C Code for '{func_name}' ===")
                response = send_request(server_process, "decompile_function", {
                    "path": binary_path,
                    "function": func_name
                })
                if "error" in response:
                    print(f"Error: {response['error']}")
                else:
                    decompiled = response["result"]
                    print(f"Function: {decompiled['name']}")
                    print(f"Signature: {decompiled['signature']}")
                    print(f"Address: {decompiled['address']}")
                    print("\nDecompiled Code:")
                    print(decompiled['decompiled_code'])
                    
                    # Save decompiled code to file
                    decompiled_path = os.path.join(output_dir, f"{func_name}.c")
                    with open(decompiled_path, "w") as f:
                        f.write(f"// Decompiled function: {func_name}\n")
                        f.write(f"// Address: {decompiled['address']}\n\n")
                        f.write(decompiled['decompiled_code'])
                    print(f"Saved decompiled code to {decompiled_path}")
            
            # Extract types
            print("\n=== Data Types ===")
            response = send_request(server_process, "get_types", {"path": binary_path})
            if "error" in response:
                print(f"Error: {response['error']}")
            else:
                types = response["result"]
                print(f"Found {len(types)} types")
                
                # Show first 5 types
                for i, type_info in enumerate(types[:5]):
                    print(f"\n{i+1}. {type_info['name']} ({type_info['type_class']})")
                    if type_info['type_class'] == 'structure':
                        print(f"   Size: {type_info['size']} bytes")
                        print("   Members:")
                        for member in type_info['members']:
                            print(f"     - {member['name']}: {member['type']} (offset: {member['offset']})")
                
                if len(types) > 5:
                    print(f"... and {len(types) - 5} more types")
                
                # Save types to file
                types_path = os.path.join(output_dir, "types.json")
                with open(types_path, "w") as f:
                    json.dump(types, f, indent=2)
                print(f"Saved types to {types_path}")
            
            # Generate header file
            print("\n=== Generated Header File ===")
            header_path = os.path.join(output_dir, "generated_header.h")
            response = send_request(server_process, "generate_header", {
                "path": binary_path,
                "output_path": header_path
            })
            if "error" in response:
                print(f"Error: {response['error']}")
            else:
                header_content = response["result"]
                print(f"Generated header file saved to {header_path}")
                print("\nFirst 10 lines:")
                for line in header_content.split("\n")[:10]:
                    print(line)
                print("...")
            
            # Generate source file
            print("\n=== Generated Source File ===")
            source_path = os.path.join(output_dir, "generated_source.c")
            response = send_request(server_process, "generate_source", {
                "path": binary_path,
                "output_path": source_path,
                "header_path": "generated_header.h"
            })
            if "error" in response:
                print(f"Error: {response['error']}")
            else:
                source_content = response["result"]
                print(f"Generated source file saved to {source_path}")
                print("\nFirst 10 lines:")
                for line in source_content.split("\n")[:10]:
                    print(line)
                print("...")
            
            # Rebuild driver (if it's a driver module)
            if binary_path.endswith(".ko") or "driver" in binary_path.lower() or "module" in binary_path.lower():
                print("\n=== Rebuilding Driver Module ===")
                driver_dir = os.path.join(output_dir, "driver")
                response = send_request(server_process, "rebuild_driver", {
                    "path": binary_path,
                    "output_dir": driver_dir
                })
                if "error" in response:
                    print(f"Error: {response['error']}")
                else:
                    result = response["result"]
                    print("Driver module rebuilt successfully!")
                    print(f"Header file: {result['header_file']}")
                    print(f"Source files: {len(result['source_files'])} files generated")
                    print(f"Makefile: {result['makefile']}")
                    print(f"\nTo build the driver, run:")
                    print(f"cd {driver_dir} && make")
        else:
            print("\nTo see source code reconstruction examples, provide an output directory:")
            print(f"python3 {sys.argv[0]} {binary_path} /path/to/output/dir")
    finally:
        # Terminate the server process
        server_process.terminate()
        server_process.wait()

if __name__ == "__main__":
    main()
