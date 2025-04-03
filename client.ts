/**
 * Binary Ninja MCP Client
 * 
 * This is a TypeScript client for the Binary Ninja MCP server.
 * It demonstrates how to interact with the server using the Model Context Protocol.
 * 
 * The client supports both raw binary files and Binary Ninja database files (.bndb).
 * Binary Ninja database files contain analysis results, annotations, and other information
 * that can speed up analysis and provide more accurate results.
 */

import { spawn, ChildProcess } from 'child_process';
import * as readline from 'readline';

interface McpRequest {
  id: number;
  method: string;
  params?: Record<string, any>;
}

interface McpResponse {
  id: number;
  result?: any;
  error?: string;
  traceback?: string;
}

class BinaryNinjaClient {
  private serverProcess: ChildProcess | null = null;
  private rl: readline.Interface | null = null;
  private requestId = 1;
  private pendingRequests: Map<number, { resolve: Function; reject: Function }> = new Map();

  /**
   * Start the Binary Ninja MCP server
   */
  async start(serverPath: string): Promise<void> {
    return new Promise((resolve, reject) => {
      try {
        this.serverProcess = spawn('python3', [serverPath], {
          stdio: ['pipe', 'pipe', 'pipe']
        });

        this.rl = readline.createInterface({
          input: this.serverProcess.stdout!,
          terminal: false
        });

        this.rl.on('line', (line) => {
          try {
            const response = JSON.parse(line) as McpResponse;
            const pending = this.pendingRequests.get(response.id);
            
            if (pending) {
              if (response.error) {
                pending.reject(new Error(`${response.error}\n${response.traceback || ''}`));
              } else {
                pending.resolve(response.result);
              }
              this.pendingRequests.delete(response.id);
            }
          } catch (err) {
            console.error('Error parsing server response:', err);
          }
        });

        this.serverProcess.stderr!.on('data', (data) => {
          console.error(`Server error: ${data.toString()}`);
        });

        this.serverProcess.on('close', (code) => {
          console.log(`Server process exited with code ${code}`);
          this.cleanup();
        });

        // Test the connection with a ping
        this.sendRequest('ping')
          .then(() => resolve())
          .catch(reject);
      } catch (err) {
        reject(err);
      }
    });
  }

  /**
   * Send a request to the Binary Ninja MCP server
   */
  async sendRequest(method: string, params?: Record<string, any>): Promise<any> {
    if (!this.serverProcess || !this.rl) {
      throw new Error('Server not started');
    }

    return new Promise((resolve, reject) => {
      const id = this.requestId++;
      const request: McpRequest = { id, method, params };
      
      this.pendingRequests.set(id, { resolve, reject });
      
      this.serverProcess!.stdin!.write(JSON.stringify(request) + '\n');
    });
  }

  /**
   * Stop the Binary Ninja MCP server
   */
  stop(): void {
    this.cleanup();
  }

  private cleanup(): void {
    if (this.rl) {
      this.rl.close();
      this.rl = null;
    }

    if (this.serverProcess) {
      this.serverProcess.kill();
      this.serverProcess = null;
    }

    // Reject any pending requests
    for (const [id, { reject }] of this.pendingRequests) {
      reject(new Error('Server connection closed'));
      this.pendingRequests.delete(id);
    }
  }

  /**
   * Get information about a binary file
   */
  async getBinaryInfo(path: string): Promise<any> {
    return this.sendRequest('get_binary_info', { path });
  }

  /**
   * List all functions in a binary file
   */
  async listFunctions(path: string): Promise<string[]> {
    return this.sendRequest('list_functions', { path });
  }

  /**
   * Disassemble a function in a binary file
   */
  async disassembleFunction(path: string, functionName: string): Promise<string[]> {
    return this.sendRequest('disassemble_function', { path, function: functionName });
  }

  /**
   * List all sections in a binary file
   */
  async listSections(path: string): Promise<any[]> {
    return this.sendRequest('list_sections', { path });
  }

  /**
   * Get cross-references to a function in a binary file
   */
  async getXrefs(path: string, functionName: string): Promise<any[]> {
    return this.sendRequest('get_xrefs', { path, function: functionName });
  }

  /**
   * Get the control flow graph of a function in a binary file
   */
  async getFunctionGraph(path: string, functionName: string): Promise<any[]> {
    return this.sendRequest('get_function_graph', { path, function: functionName });
  }

  /**
   * Get strings from a binary file
   */
  async getStrings(path: string, minLength: number = 4): Promise<any[]> {
    return this.sendRequest('get_strings', { path, min_length: minLength });
  }

  /**
   * Decompile a function to C code
   */
  async decompileFunction(path: string, functionName: string): Promise<any> {
    return this.sendRequest('decompile_function', { path, function: functionName });
  }

  /**
   * Extract data structures and types from a binary file
   */
  async getTypes(path: string): Promise<any[]> {
    return this.sendRequest('get_types', { path });
  }

  /**
   * Generate a header file with function prototypes and type definitions
   */
  async generateHeader(path: string, outputPath?: string, includeFunctions: boolean = true, includeTypes: boolean = true): Promise<string> {
    return this.sendRequest('generate_header', { 
      path, 
      output_path: outputPath,
      include_functions: includeFunctions,
      include_types: includeTypes
    });
  }

  /**
   * Generate a source file with function implementations
   */
  async generateSource(path: string, outputPath?: string, headerPath: string = 'generated_header.h'): Promise<string> {
    return this.sendRequest('generate_source', { 
      path, 
      output_path: outputPath,
      header_path: headerPath
    });
  }

  /**
   * Rebuild an entire driver module from a binary file
   */
  async rebuildDriver(path: string, outputDir: string): Promise<any> {
    return this.sendRequest('rebuild_driver', { 
      path, 
      output_dir: outputDir
    });
  }
}

// Example usage
async function main() {
  if (process.argv.length < 3) {
    console.error('Usage: ts-node client.ts <path_to_binary>');
    process.exit(1);
  }

  const binaryPath = process.argv[2];
  const client = new BinaryNinjaClient();

  try {
    // Start the server
    await client.start('/home/matteius/Documents/Cline/MCP/bn-mcp/binaryninja_server.py');
    console.log('Connected to Binary Ninja MCP server');

    // Get binary information
    console.log('\n=== Binary Information ===');
    const info = await client.getBinaryInfo(binaryPath);
    console.log(`Filename: ${info.filename}`);
    console.log(`Architecture: ${info.architecture}`);
    console.log(`Platform: ${info.platform}`);
    console.log(`Entry Point: ${info.entry_point}`);
    console.log(`File Size: ${info.file_size} bytes`);
    console.log(`Executable: ${info.is_executable}`);
    console.log(`Relocatable: ${info.is_relocatable}`);
    console.log(`Address Size: ${info.address_size} bits`);

    // List sections
    console.log('\n=== Sections ===');
    const sections = await client.listSections(binaryPath);
    for (const section of sections) {
      console.log(`${section.name}: ${section.start} - ${section.end} (${section.size} bytes) [${section.semantics}]`);
    }

    // List functions
    console.log('\n=== Functions ===');
    const functions = await client.listFunctions(binaryPath);
    for (let i = 0; i < Math.min(functions.length, 10); i++) {
      console.log(`${i+1}. ${functions[i]}`);
    }
    if (functions.length > 10) {
      console.log(`... and ${functions.length - 10} more functions`);
    }

    // If there are functions, disassemble the first one
    if (functions.length > 0) {
      const funcName = functions[0];
      console.log(`\n=== Disassembly of '${funcName}' ===`);
      const disasm = await client.disassembleFunction(binaryPath, funcName);
      for (let i = 0; i < disasm.length; i++) {
        console.log(`${i+1}. ${disasm[i]}`);
      }

      // Get cross-references to this function
      console.log(`\n=== Cross-references to '${funcName}' ===`);
      const xrefs = await client.getXrefs(binaryPath, funcName);
      if (xrefs.length > 0) {
        for (const xref of xrefs) {
          console.log(`From: ${xref.from_function} at ${xref.from_address} to ${xref.to_address}`);
        }
      } else {
        console.log('No cross-references found');
      }
    }

    // Get strings
    console.log('\n=== Strings ===');
    const strings = await client.getStrings(binaryPath, 5);
    for (let i = 0; i < Math.min(strings.length, 10); i++) {
      console.log(`${i+1}. ${strings[i].address}: '${strings[i].value}'`);
    }
    if (strings.length > 10) {
      console.log(`... and ${strings.length - 10} more strings`);
    }

    // Source Code Reconstruction
    if (process.argv.length > 3) {
      const outputDir = process.argv[3];
      const fs = require('fs');
      const path = require('path');
      
      // Create output directory
      if (!fs.existsSync(outputDir)) {
        fs.mkdirSync(outputDir, { recursive: true });
      }
      
      // Decompile the first function
      if (functions.length > 0) {
        const funcName = functions[0];
        console.log(`\n=== Decompiled C Code for '${funcName}' ===`);
        try {
          const decompiled = await client.decompileFunction(binaryPath, funcName);
          console.log(`Function: ${decompiled.name}`);
          console.log(`Signature: ${decompiled.signature}`);
          console.log(`Address: ${decompiled.address}`);
          console.log("\nDecompiled Code:");
          console.log(decompiled.decompiled_code);
          
          // Save decompiled code to file
          const decompilePath = path.join(outputDir, `${funcName}.c`);
          fs.writeFileSync(decompilePath, 
            `// Decompiled function: ${funcName}\n` +
            `// Address: ${decompiled.address}\n\n` +
            decompiled.decompiled_code
          );
          console.log(`Saved decompiled code to ${decompilePath}`);
        } catch (err) {
          console.error(`Error decompiling function: ${err}`);
        }
      }
      
      // Extract types
      console.log("\n=== Data Types ===");
      try {
        const types = await client.getTypes(binaryPath);
        console.log(`Found ${types.length} types`);
        
        // Show first 5 types
        for (let i = 0; i < Math.min(types.length, 5); i++) {
          const type = types[i];
          console.log(`\n${i+1}. ${type.name} (${type.type_class})`);
          if (type.type_class === 'structure') {
            console.log(`   Size: ${type.size} bytes`);
            console.log("   Members:");
            for (const member of type.members) {
              console.log(`     - ${member.name}: ${member.type} (offset: ${member.offset})`);
            }
          }
        }
        
        if (types.length > 5) {
          console.log(`... and ${types.length - 5} more types`);
        }
        
        // Save types to file
        const typesPath = path.join(outputDir, "types.json");
        fs.writeFileSync(typesPath, JSON.stringify(types, null, 2));
        console.log(`Saved types to ${typesPath}`);
      } catch (err) {
        console.error(`Error getting types: ${err}`);
      }
      
      // Generate header file
      console.log("\n=== Generated Header File ===");
      try {
        const headerPath = path.join(outputDir, "generated_header.h");
        const headerContent = await client.generateHeader(binaryPath, headerPath);
        console.log(`Generated header file saved to ${headerPath}`);
        console.log("\nFirst 10 lines:");
        const headerLines = headerContent.split("\n");
        for (let i = 0; i < Math.min(headerLines.length, 10); i++) {
          console.log(headerLines[i]);
        }
        console.log("...");
      } catch (err) {
        console.error(`Error generating header: ${err}`);
      }
      
      // Generate source file
      console.log("\n=== Generated Source File ===");
      try {
        const sourcePath = path.join(outputDir, "generated_source.c");
        const sourceContent = await client.generateSource(binaryPath, sourcePath, "generated_header.h");
        console.log(`Generated source file saved to ${sourcePath}`);
        console.log("\nFirst 10 lines:");
        const sourceLines = sourceContent.split("\n");
        for (let i = 0; i < Math.min(sourceLines.length, 10); i++) {
          console.log(sourceLines[i]);
        }
        console.log("...");
      } catch (err) {
        console.error(`Error generating source: ${err}`);
      }
      
      // Rebuild driver (if it's a driver module)
      if (binaryPath.endsWith(".ko") || binaryPath.toLowerCase().includes("driver") || binaryPath.toLowerCase().includes("module")) {
        console.log("\n=== Rebuilding Driver Module ===");
        try {
          const driverDir = path.join(outputDir, "driver");
          const result = await client.rebuildDriver(binaryPath, driverDir);
          console.log("Driver module rebuilt successfully!");
          console.log(`Header file: ${result.header_file}`);
          console.log(`Source files: ${result.source_files.length} files generated`);
          console.log(`Makefile: ${result.makefile}`);
          console.log(`\nTo build the driver, run:`);
          console.log(`cd ${driverDir} && make`);
        } catch (err) {
          console.error(`Error rebuilding driver: ${err}`);
        }
      }
    } else {
      console.log("\nTo see source code reconstruction examples, provide an output directory:");
      console.log(`ts-node client.ts ${binaryPath} /path/to/output/dir`);
    }
  } catch (err) {
    console.error('Error:', err);
  } finally {
    // Stop the server
    client.stop();
  }
}

// Run the example if this file is executed directly
if (require.main === module) {
  main().catch(console.error);
}

export { BinaryNinjaClient };
