# Extended Binary Ninja MCP Client

This project extends the Binary Ninja MCP client to provide more comprehensive binary analysis capabilities through the Model Context Protocol (MCP).

## Features

The extended client adds the following capabilities:

### Basic Binary Analysis
- Get binary metadata
- List functions, sections, imports, exports
- Get detailed function information
- Disassemble and decompile functions
- Search for functions by name
- List C++ namespaces
- List and analyze data variables

### Advanced Analysis
- Generate comprehensive analysis reports
- Find potential vulnerabilities in binaries
- Compare two binaries to identify differences
- Rename functions and data variables

## Setup

1. Install dependencies:
```bash
cd bn_cline_mcp
npm install
npm install --save-dev @types/node
```

2. Make sure Binary Ninja is running with the MCP plugin installed.

## Usage

### TypeScript Client

The TypeScript client provides a simple API for interacting with Binary Ninja:

```typescript
import { BinaryNinjaClient } from './client';

async function main() {
  const client = new BinaryNinjaClient();
  
  try {
    // Start the server
    await client.start('/path/to/binaryninja_server.py');
    
    // Load a binary file
    const binaryPath = '/path/to/binary';
    
    // Get binary information
    const info = await client.getBinaryInfo(binaryPath);
    console.log(info);
    
    // List functions
    const functions = await client.listFunctions(binaryPath);
    console.log(functions);
    
    // Decompile a function
    const decompiled = await client.decompileFunction(binaryPath, functions[0]);
    console.log(decompiled);
    
    // Generate a comprehensive analysis report
    const report = await client.analyzeFile(binaryPath, 'report.json');
    console.log(`Found ${report.function_count} functions`);
    
    // Find potential vulnerabilities
    const vulnerabilities = await client.findVulnerabilities(binaryPath);
    console.log(`Found ${vulnerabilities.length} potential vulnerabilities`);
    
  } catch (err) {
    console.error('Error:', err);
  } finally {
    // Stop the server
    client.stop();
  }
}

main().catch(console.error);
```

### Example Scripts

The `examples` directory contains example scripts that demonstrate how to use the extended client:

- `binary_analysis.ts`: Demonstrates comprehensive binary analysis capabilities

To run an example:

```bash
cd bn_cline_mcp
npx ts-node examples/binary_analysis.ts /path/to/binary [output_dir]
```

## API Reference

### Basic Operations

- `getBinaryInfo(path: string)`: Get information about a binary file
- `listFunctions(path: string)`: List all functions in a binary file
- `getFunction(path: string, functionName: string)`: Get detailed information about a specific function
- `disassembleFunction(path: string, functionName: string)`: Disassemble a function
- `decompileFunction(path: string, functionName: string)`: Decompile a function to C code
- `listSections(path: string)`: List all sections/segments in a binary file
- `listImports(path: string)`: List all imported functions
- `listExports(path: string)`: List all exported symbols
- `listNamespaces(path: string)`: List all C++ namespaces
- `listData(path: string)`: List all defined data variables
- `searchFunctions(path: string, query: string)`: Search for functions by name
- `renameFunction(path: string, oldName: string, newName: string)`: Rename a function
- `renameData(path: string, address: string, newName: string)`: Rename a data variable

### Advanced Analysis

- `analyzeFile(path: string, outputPath?: string)`: Generate a comprehensive analysis report
- `findVulnerabilities(path: string)`: Find potential vulnerabilities in a binary file
- `compareBinaries(path1: string, path2: string)`: Compare two binary files and identify differences

## Extending the Client

You can extend the client by adding new methods to the `BinaryNinjaClient` class in `client.ts`. If you need to add new server-side functionality, you'll need to:

1. Add a new tool definition to the `MCP_TOOLS` array in `binaryninja_mcp_http_server.py`
2. Implement the handler for the new tool in the `_handle_mcp_request` method
3. Add a corresponding method to the `BinaryNinjaClient` class in `client.ts`

## Troubleshooting

- Make sure Binary Ninja is running and the MCP plugin is installed
- Check that the server path in `client.start()` is correct
- If you get TypeScript errors, make sure you've installed the required dependencies with `npm install --save-dev @types/node`

## Handling Timeouts

The client includes built-in retry logic to handle occasional timeouts that may occur when communicating with the Binary Ninja MCP server. By default, each request will:

- Timeout after 30 seconds if no response is received
- Automatically retry up to 3 times with a 1-second delay between attempts
- Log detailed error information for debugging

You can customize the retry behavior when making requests:

```typescript
// Custom retry options
const result = await client.sendRequest('some_method', { param: 'value' }, {
  maxRetries: 5,    // Retry up to 5 times
  retryDelay: 2000  // Wait 2 seconds between retries
});
```

This makes the client more robust when dealing with large binaries or complex analysis tasks that might occasionally cause timeouts.
