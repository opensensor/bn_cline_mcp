#!/usr/bin/env python3
"""
Test script to verify that pagination is working correctly in the Binary Ninja HTTP client.
This script will load a binary file and retrieve all functions, demonstrating that
pagination is working correctly by retrieving more than the default limit of 100 functions.
"""

import sys
import json
from binaryninja_http_client import BinaryNinjaHTTPClient

def main():
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <path_to_binary>")
        sys.exit(1)
        
    binary_path = sys.argv[1]
    client = BinaryNinjaHTTPClient()
    
    # Test the connection
    ping_result = client.ping()
    print(f"Connection status: {ping_result['status']}")
    
    if ping_result['status'] != 'connected':
        print(f"Error: {ping_result.get('error', 'Unknown error')}")
        sys.exit(1)
        
    # Load the binary if not already loaded
    if not ping_result.get('loaded', False):
        try:
            print(f"Loading binary: {binary_path}")
            load_result = client.load_binary(binary_path)
            print(f"Load result: {json.dumps(load_result, indent=2)}")
        except Exception as e:
            print(f"Error loading binary: {e}")
            sys.exit(1)
    
    # Get all functions
    print("\nRetrieving all functions...")
    functions = client.list_functions()
    print(f"Retrieved {len(functions)} functions in total")
    
    # Print the first 5 and last 5 functions to verify pagination is working
    if functions:
        print("\nFirst 5 functions:")
        for i, func in enumerate(functions[:5]):
            print(f"{i+1}. {func['name']} at {func.get('address', 'unknown')}")
            
        if len(functions) > 10:
            print("\nLast 5 functions:")
            for i, func in enumerate(functions[-5:]):
                print(f"{len(functions)-4+i}. {func['name']} at {func.get('address', 'unknown')}")
    
    # Test other paginated methods
    print("\nRetrieving all imports...")
    imports = client.get_imports()
    print(f"Retrieved {len(imports)} imports in total")
    
    print("\nRetrieving all exports...")
    exports = client.get_exports()
    print(f"Retrieved {len(exports)} exports in total")
    
    print("\nRetrieving all segments...")
    segments = client.get_sections()
    print(f"Retrieved {len(segments)} segments in total")
    
    print("\nRetrieving all data items...")
    data_items = client.get_defined_data()
    print(f"Retrieved {len(data_items)} data items in total")
    
    print("\nTest completed successfully!")

if __name__ == "__main__":
    main()
