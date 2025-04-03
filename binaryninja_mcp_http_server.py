#!/usr/bin/env python3
import sys
import json
import traceback
import os
import logging
import argparse
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse
import time
from socketserver import ThreadingMixIn
import requests

# Assuming this is your BinaryNinja client implementation
# You would need to adjust this import to match your actual implementation
from binaryninja_http_client import BinaryNinjaHTTPClient

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("BinaryNinjaMCP")

# Define the MCP tools - note the use of "path" instead of "file"
MCP_TOOLS = [
    {
        "name": "get_binary_info",
        "description": "Get binary metadata",
        "streaming": False,
        "inputSchema": {
            "type": "object",
            "properties": {"path": {"type": "string"}},
            "required": ["path"]
        }
    },
    {
        "name": "list_functions",
        "description": "List functions",
        "streaming": False,
        "inputSchema": {
            "type": "object",
            "properties": {"path": {"type": "string"}},
            "required": ["path"]
        }
    },
    {
        "name": "disassemble_function",
        "description": "Disassemble function",
        "streaming": False,
        "inputSchema": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "function": {"type": "string"}
            },
            "required": ["path", "function"]
        }
    },
    {
        "name": "decompile_function",
        "description": "Decompile to C",
        "streaming": False,
        "inputSchema": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "function": {"type": "string"}
            },
            "required": ["path", "function"]
        }
    }
]

class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True

class BinaryNinjaMCPHandler(BaseHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        self.client = BinaryNinjaHTTPClient()
        super().__init__(*args, **kwargs)

    def _set_headers(self, content_type='application/json', status_code=200):
        self.send_response(status_code)
        self.send_header('Content-Type', content_type)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_OPTIONS(self):
        self._set_headers()

    def log_message(self, format, *args):
        logger.info(format % args)

    def do_GET(self):
        logger.debug(f"GET request received: {self.path}")
        logger.debug(f"Headers: {dict(self.headers)}")
        
        parsed = urlparse(self.path)
        if parsed.path == '/':
            if 'text/event-stream' in self.headers.get('Accept', ''):
                self.send_response(200)
                self.send_header('Content-Type', 'text/event-stream')
                self.send_header('Cache-Control', 'no-cache')
                self.send_header('Connection', 'keep-alive')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                try:
                    logger.debug("Starting SSE connection")
                    self.wfile.write(b"event: connected\ndata: {\"status\": \"ready\"}\n\n")
                    self.wfile.flush()
                    
                    # Use a shorter heartbeat interval
                    heartbeat_interval = 10  # seconds
                    
                    while True:
                        heartbeat = {
                            "jsonrpc": "2.0",
                            "method": "heartbeat",
                            "params": {"timestamp": int(time.time())}
                        }
                        msg = f"event: mcp-event\ndata: {json.dumps(heartbeat)}\n\n"
                        logger.debug(f"Sending heartbeat: {msg}")
                        self.wfile.write(msg.encode())
                        self.wfile.flush()
                        time.sleep(heartbeat_interval)
                except Exception as e:
                    logger.warning(f"SSE error: {e}")
            else:
                response = {
                    "jsonrpc": "2.0",
                    "id": "root-list",
                    "result": {
                        "name": "binaryninja-mcp",
                        "version": "0.1.0",
                        "tools": MCP_TOOLS
                    }
                }
                self._set_headers()
                response_str = json.dumps(response)
                logger.debug(f"Returning tool list: {response_str[:100]}...")
                self.wfile.write(response_str.encode())
        elif parsed.path == '/ping':
            self._set_headers()
            self.wfile.write(json.dumps({"status": "ok"}).encode())
        else:
            self._set_headers(status_code=404)
            self.wfile.write(json.dumps({"error": "Not found"}).encode())

    def do_POST(self):
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            raw_data = self.rfile.read(content_length).decode('utf-8')
            
            logger.debug(f"POST received: {raw_data[:200]}...")
            
            request = json.loads(raw_data)
            response = self._handle_mcp_request(request)
            
            self._set_headers()
            response_str = json.dumps(response)
            logger.debug(f"Responding with: {response_str[:200]}...")
            self.wfile.write(response_str.encode())
        except Exception as e:
            logger.error(f"POST error: {e}")
            logger.error(traceback.format_exc())
            self._set_headers(status_code=500)
            self.wfile.write(json.dumps({
                "jsonrpc": "2.0",
                "id": None,
                "error": {"code": -32603, "message": str(e)}
            }).encode())

    def _wrap_result(self, request_id, text):
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "content": [{"type": "text", "text": text}],
                "isError": False
            }
        }

    def _handle_mcp_request(self, request):
        request_id = request.get("id")
        method = request.get("method")
        params = request.get("params", {})

        logger.debug(f"Handling MCP request: id={request_id}, method={method}, params={params}")

        try:
            if method == "list_tools":
                return {
                    "jsonrpc": "2.0", "id": request_id,
                    "result": {"tools": MCP_TOOLS}
                }
            elif method == "call_tool":
                name = params.get("name")
                args = params.get("arguments", {})
                return self._handle_mcp_request({"jsonrpc": "2.0", "id": request_id, "method": name, "params": args})

            elif method == "get_binary_info":
                path = params.get("path")
                if not path:
                    logger.error("Missing 'path' parameter")
                    return self._error_response(request_id, -32602, "Missing 'path' parameter")
                if not isinstance(path, str):
                    logger.error(f"Invalid path type: {type(path)}")
                    return self._error_response(request_id, -32602, "Parameter 'path' must be a string")
                
                logger.debug(f"Getting info for file: {path}")
                info = self.client.get_file_info(path)
                return self._wrap_result(request_id, json.dumps(info, indent=2))

            elif method == "list_functions":
                path = params.get("path")
                if not path:
                    logger.error("Missing 'path' parameter")
                    return self._error_response(request_id, -32602, "Missing 'path' parameter")
                if not isinstance(path, str):
                    logger.error(f"Invalid path type: {type(path)}")
                    return self._error_response(request_id, -32602, "Parameter 'path' must be a string")
                
                logger.debug(f"Listing functions for file: {path}")
                funcs = self.client.list_functions(path)
                return self._wrap_result(request_id, json.dumps([f["name"] for f in funcs], indent=2))

            elif method == "disassemble_function":
                path = params.get("path")
                func = params.get("function")
                if not path:
                    logger.error("Missing 'path' parameter")
                    return self._error_response(request_id, -32602, "Missing 'path' parameter")
                if not func:
                    logger.error("Missing 'function' parameter")
                    return self._error_response(request_id, -32602, "Missing 'function' parameter")
                if not isinstance(path, str):
                    logger.error(f"Invalid path type: {type(path)}")
                    return self._error_response(request_id, -32602, "Parameter 'path' must be a string")
                if not isinstance(func, str):
                    logger.error(f"Invalid function type: {type(func)}")
                    return self._error_response(request_id, -32602, "Parameter 'function' must be a string")
                
                logger.debug(f"Disassembling function {func} in file: {path}")
                code = self.client.get_disassembly(path, function_name=func)
                return self._wrap_result(request_id, "\n".join(code))

            elif method == "decompile_function":
                path = params.get("path")
                func = params.get("function")
                if not path:
                    logger.error("Missing 'path' parameter")
                    return self._error_response(request_id, -32602, "Missing 'path' parameter")
                if not func:
                    logger.error("Missing 'function' parameter")
                    return self._error_response(request_id, -32602, "Missing 'function' parameter")
                if not isinstance(path, str):
                    logger.error(f"Invalid path type: {type(path)}")
                    return self._error_response(request_id, -32602, "Parameter 'path' must be a string")
                if not isinstance(func, str):
                    logger.error(f"Invalid function type: {type(func)}")
                    return self._error_response(request_id, -32602, "Parameter 'function' must be a string")
                
                logger.debug(f"Decompiling function {func} in file: {path}")
                hlil = self.client.get_hlil(path, function_name=func)
                return self._wrap_result(request_id, "\n".join(hlil) if isinstance(hlil, list) else str(hlil))

            elif method == "cancel":
                logger.debug("Cancel requested — not implemented.")
                return self._error_response(request_id, -32601, "Cancel not implemented")

            logger.error(f"Unknown method: {method}")
            return self._error_response(request_id, -32601, f"Unknown method: {method}")

        except Exception as e:
            logger.error(f"Error in MCP handler: {e}\n{traceback.format_exc()}")
            return self._error_response(request_id, -32603, str(e))

    def _error_response(self, request_id, code, message):
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {
                "code": code,
                "message": message
            }
        }

def run_server(host='127.0.0.1', port=8088):
    server = ThreadedHTTPServer((host, port), BinaryNinjaMCPHandler)
    logger.info(f"Binary Ninja MCP HTTP server running at http://{host}:{port}")
    server.serve_forever()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--host', default='127.0.0.1')
    parser.add_argument('--port', type=int, default=8088)
    args = parser.parse_args()
    run_server(args.host, args.port)

if __name__ == '__main__':
    main()