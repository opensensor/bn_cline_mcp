#!/usr/bin/env node
import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from "@modelcontextprotocol/sdk/types.js";
import { z } from 'zod';
import { zodToJsonSchema } from 'zod-to-json-schema';
import fetch from 'node-fetch';

// Define the version
const VERSION = "0.1.0";

// Configuration
const BN_HTTP_SERVER = process.env.BN_HTTP_SERVER || 'http://localhost:8088';

// Schema definitions
const FilePathSchema = z.object({
  path: z.string().min(1, "File path cannot be empty")
});

const FunctionSchema = z.object({
  path: z.string().min(1, "File path cannot be empty"),
  function: z.string().min(1, "Function name cannot be empty")
});

// Create a server instance
const server = new Server(
  {
    name: "binaryninja-mcp-server",
    version: VERSION,
  },
  {
    capabilities: {
      tools: {},
    },
  }
);

// HTTP client for Binary Ninja server
async function callBinaryNinjaServer(method, params = {}) {
  try {
    console.error(`[INFO] Calling Binary Ninja server method: ${method}`);
    console.error(`[INFO] Params: ${JSON.stringify(params)}`);
    
    const response = await fetch(`${BN_HTTP_SERVER}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        jsonrpc: "2.0",
        id: Date.now().toString(),
        method: method,
        params: params
      })
    });
    
    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`HTTP error ${response.status}: ${errorText}`);
    }
    
    const result = await response.json();
    
    if (result.error) {
      throw new Error(`Binary Ninja server error: ${JSON.stringify(result.error)}`);
    }
    
    return result;
  } catch (error) {
    console.error(`[ERROR] Failed to call Binary Ninja server: ${error.message}`);
    throw error;
  }
}

// Register the ListTools handler
server.setRequestHandler(ListToolsRequestSchema, async () => {
  console.error("[INFO] Received ListTools request");
  return {
    tools: [
      {
        name: "get_binary_info",
        description: "Get binary metadata",
        inputSchema: zodToJsonSchema(FilePathSchema),
      },
      {
        name: "list_functions",
        description: "List functions in a binary",
        inputSchema: zodToJsonSchema(FilePathSchema),
      },
      {
        name: "disassemble_function",
        description: "Disassemble a function from a binary",
        inputSchema: zodToJsonSchema(FunctionSchema),
      },
      {
        name: "decompile_function",
        description: "Decompile a function to C",
        inputSchema: zodToJsonSchema(FunctionSchema),
      }
    ],
  };
});

// Register the CallTool handler
server.setRequestHandler(CallToolRequestSchema, async (request) => {
  try {
    console.error(`[INFO] Received CallTool request for tool: ${request.params.name}`);
    
    if (!request.params.arguments) {
      throw new Error("Arguments are required");
    }

    let result;
    
    // Log the arguments for debugging
    console.error(`[DEBUG] Tool arguments: ${JSON.stringify(request.params.arguments)}`);
    
    // Check if arguments use 'file' instead of 'path'
    if (request.params.arguments && request.params.arguments.file !== undefined && request.params.arguments.path === undefined) {
      console.error(`[INFO] Converting 'file' parameter to 'path'`);
      request.params.arguments.path = request.params.arguments.file;
    }
    
    switch (request.params.name) {
      case "get_binary_info": {
        try {
          const args = FilePathSchema.parse(request.params.arguments);
          result = await callBinaryNinjaServer("get_binary_info", args);
        } catch (error) {
          console.error(`[ERROR] Failed to parse arguments for get_binary_info: ${error.message}`);
          console.error(`[ERROR] Arguments received: ${JSON.stringify(request.params.arguments)}`);
          throw error;
        }
        break;
      }

      case "list_functions": {
        try {
          const args = FilePathSchema.parse(request.params.arguments);
          result = await callBinaryNinjaServer("list_functions", args);
        } catch (error) {
          console.error(`[ERROR] Failed to parse arguments for list_functions: ${error.message}`);
          console.error(`[ERROR] Arguments received: ${JSON.stringify(request.params.arguments)}`);
          throw error;
        }
        break;
      }

      case "disassemble_function": {
        try {
          const args = FunctionSchema.parse(request.params.arguments);
          result = await callBinaryNinjaServer("disassemble_function", args);
        } catch (error) {
          console.error(`[ERROR] Failed to parse arguments for disassemble_function: ${error.message}`);
          console.error(`[ERROR] Arguments received: ${JSON.stringify(request.params.arguments)}`);
          throw error;
        }
        break;
      }

      case "decompile_function": {
        try {
          const args = FunctionSchema.parse(request.params.arguments);
          result = await callBinaryNinjaServer("decompile_function", args);
        } catch (error) {
          console.error(`[ERROR] Failed to parse arguments for decompile_function: ${error.message}`);
          console.error(`[ERROR] Arguments received: ${JSON.stringify(request.params.arguments)}`);
          throw error;
        }
        break;
      }

      default:
        throw new Error(`Unknown tool: ${request.params.name}`);
    }
    
    // Extract content from the result
    const content = result.result?.content?.[0]?.text || JSON.stringify(result, null, 2);
    
    return {
      content: [{ type: "text", text: content }],
    };
    
  } catch (error) {
    if (error instanceof z.ZodError) {
      console.error(`[ERROR] Validation error: ${JSON.stringify(error.errors, null, 2)}`);
      throw new Error(`Invalid input: ${JSON.stringify(error.errors)}`);
    }
    console.error(`[ERROR] Unexpected error: ${error.message}`);
    throw error;
  }
});

// Run the server
async function runServer() {
  try {
    console.error(`[INFO] Starting Binary Ninja MCP Server (connecting to ${BN_HTTP_SERVER})...`);
    const transport = new StdioServerTransport();
    await server.connect(transport);
    console.error("[INFO] Binary Ninja MCP Server running on stdio");
  } catch (error) {
    console.error(`[FATAL] Failed to start server: ${error.message}`);
    process.exit(1);
  }
}

runServer().catch((error) => {
  console.error(`[FATAL] Unhandled error in main: ${error.message}`);
  process.exit(1);
});
