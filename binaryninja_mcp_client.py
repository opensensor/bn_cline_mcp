#!/usr/bin/env python3
"""
Binary Ninja MCP Client

This module provides a client for interacting with the Binary Ninja MCP server.
The Binary Ninja MCP server is a plugin that provides an HTTP API for Binary Ninja.
"""

import requests
import json
import time
import logging
import sys

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('BinaryNinjaMCPClient')

class BinaryNinjaMCPClient:
    """Client for interacting with the Binary Ninja MCP server."""
    
    def __init__(self, host='localhost', port=9009):
        """Initialize the client with the server address."""
        self.base_url = f"http://{host}:{port}"
        self.session = requests.Session()
        logger.info(f"Initialized Binary Ninja MCP client for {self.base_url}")
        
    def _request(self, method, endpoint, data=None, params=None, timeout=60):
        """Make a request to the Binary Ninja MCP server."""
        url = f"{self.base_url}/{endpoint}"
        try:
            if method == 'GET':
                response = self.session.get(url, params=params, timeout=timeout)
            elif method == 'POST':
                response = self.session.post(url, json=data, timeout=timeout)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error making request to {url}: {e}")
            raise
            
    def ping(self):
        """Test the connection to the Binary Ninja server."""
        try:
            # Try to get the status of the current binary view
            response = self._request('GET', 'status')
            return {"status": "connected", "loaded": response.get("loaded", False)}
        except Exception as e:
            # If that fails, try a simple request to the root URL
            try:
                response = requests.get(f"{self.base_url}/", timeout=5)
                if response.status_code == 200 or response.status_code == 404:
                    # Even a 404 means the server is running
                    return {"status": "connected", "loaded": False}
                else:
                    logger.error(f"Failed to ping Binary Ninja server: {response.status_code}")
                    return {"status": "disconnected", "error": f"HTTP error: {response.status_code}"}
            except Exception as e2:
                logger.error(f"Failed to ping Binary Ninja server: {e2}")
                return {"status": "disconnected", "error": str(e2)}
            
    def load_binary(self, file_path):
        """Load a binary file."""
        try:
            data = {"filepath": file_path}
            response = self._request('POST', 'load', data=data)
            return response
        except Exception as e:
            logger.error(f"Failed to load file {file_path}: {e}")
            raise
            
    def get_status(self):
        """Get the current status of the binary view."""
        try:
            response = self._request('GET', 'status')
            return response
        except Exception as e:
            logger.error(f"Failed to get status: {e}")
            raise
            
    def list_functions(self, offset=0, limit=100):
        """List all functions in a binary file."""
        try:
            params = {"offset": offset, "limit": limit}
            response = self._request('GET', 'functions', params=params)
            return response.get("functions", [])
        except Exception as e:
            logger.error(f"Failed to list functions: {e}")
            raise
            
    def list_classes(self, offset=0, limit=100):
        """List all classes in a binary file."""
        try:
            params = {"offset": offset, "limit": limit}
            response = self._request('GET', 'classes', params=params)
            return response.get("classes", [])
        except Exception as e:
            logger.error(f"Failed to list classes: {e}")
            raise
            
    def list_segments(self, offset=0, limit=100):
        """List all segments in a binary file."""
        try:
            params = {"offset": offset, "limit": limit}
            response = self._request('GET', 'segments', params=params)
            return response.get("segments", [])
        except Exception as e:
            logger.error(f"Failed to list segments: {e}")
            raise
            
    def list_imports(self, offset=0, limit=100):
        """List all imported functions in a binary file."""
        try:
            params = {"offset": offset, "limit": limit}
            response = self._request('GET', 'imports', params=params)
            return response.get("imports", [])
        except Exception as e:
            logger.error(f"Failed to list imports: {e}")
            raise
            
    def list_exports(self, offset=0, limit=100):
        """List all exported symbols in a binary file."""
        try:
            params = {"offset": offset, "limit": limit}
            response = self._request('GET', 'exports', params=params)
            return response.get("exports", [])
        except Exception as e:
            logger.error(f"Failed to list exports: {e}")
            raise
            
    def list_namespaces(self, offset=0, limit=100):
        """List all namespaces in a binary file."""
        try:
            params = {"offset": offset, "limit": limit}
            response = self._request('GET', 'namespaces', params=params)
            return response.get("namespaces", [])
        except Exception as e:
            logger.error(f"Failed to list namespaces: {e}")
            raise
            
    def list_data(self, offset=0, limit=100):
        """List all data variables in a binary file."""
        try:
            params = {"offset": offset, "limit": limit}
            response = self._request('GET', 'data', params=params)
            return response.get("data", [])
        except Exception as e:
            logger.error(f"Failed to list data: {e}")
            raise
            
    def search_functions(self, query, offset=0, limit=100):
        """Search for functions by name."""
        try:
            params = {"query": query, "offset": offset, "limit": limit}
            response = self._request('GET', 'searchFunctions', params=params)
            return response.get("matches", [])
        except Exception as e:
            logger.error(f"Failed to search functions: {e}")
            raise
            
    def decompile_function(self, function_name):
        """Decompile a function by name."""
        try:
            params = {"name": function_name}
            response = self._request('GET', 'decompile', params=params)
            return response
        except Exception as e:
            logger.error(f"Failed to decompile function {function_name}: {e}")
            raise
            
    def rename_function(self, old_name, new_name):
        """Rename a function."""
        try:
            data = {"oldName": old_name, "newName": new_name}
            response = self._request('POST', 'rename/function', data=data)
            return response
        except Exception as e:
            logger.error(f"Failed to rename function {old_name} to {new_name}: {e}")
            raise
            
    def rename_data(self, address, new_name):
        """Rename a data variable."""
        try:
            data = {"address": address, "newName": new_name}
            response = self._request('POST', 'rename/data', data=data)
            return response
        except Exception as e:
            logger.error(f"Failed to rename data at {address} to {new_name}: {e}")
            raise

# Example usage
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <path_to_binary>")
        sys.exit(1)
        
    binary_path = sys.argv[1]
    client = BinaryNinjaMCPClient()
    
    # Test the connection
    ping_result = client.ping()
    print(f"Connection status: {ping_result['status']}")
    if ping_result['status'] == 'connected':
        print(f"Binary file loaded: {ping_result.get('loaded', False)}")
        
        # If no binary is loaded, try to load one
        if not ping_result.get('loaded', False):
            try:
                print(f"\nLoading binary: {binary_path}")
                load_result = client.load_binary(binary_path)
                print(f"Load result: {json.dumps(load_result, indent=2)}")
            except Exception as e:
                print(f"Error loading binary: {e}")
                sys.exit(1)
        
        # Get status
        try:
            status = client.get_status()
            print(f"\nBinary status: {json.dumps(status, indent=2)}")
        except Exception as e:
            print(f"Error getting status: {e}")
        
        # List functions
        try:
            functions = client.list_functions()
            print(f"\nFound {len(functions)} functions")
            for i, func in enumerate(functions[:5]):  # Show only first 5 functions
                print(f"{i+1}. {func['name']} at {func.get('address', 'unknown')}")
        except Exception as e:
            print(f"Error listing functions: {e}")
            
        # If there are functions, decompile the first one
        if functions:
            func = functions[0]
            try:
                print(f"\nDecompiling function: {func['name']}")
                decompiled = client.decompile_function(func['name'])
                print(f"Decompiled function: {func['name']}")
                print(decompiled.get('decompiled', 'No decompilation available'))
            except Exception as e:
                print(f"Error decompiling function: {e}")
    else:
        print(f"Error: {ping_result.get('error', 'Unknown error')}")
