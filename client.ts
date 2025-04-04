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
   * Send a request to the Binary Ninja MCP server with retry capability
   */
  async sendRequest(
    method: string, 
    params?: Record<string, any>, 
    options: { maxRetries?: number, retryDelay?: number } = {}
  ): Promise<any> {
    if (!this.serverProcess || !this.rl) {
      throw new Error('Server not started');
    }

    const maxRetries = options.maxRetries ?? 3;
    const retryDelay = options.retryDelay ?? 1000;
    let lastError: Error | null = null;

    for (let attempt = 0; attempt <= maxRetries; attempt++) {
      try {
        return await new Promise((resolve, reject) => {
          const id = this.requestId++;
          const request: McpRequest = { id, method, params };
          
          // Set a timeout to handle cases where the server doesn't respond
          const timeoutId = setTimeout(() => {
            if (this.pendingRequests.has(id)) {
              this.pendingRequests.delete(id);
              reject(new Error(`Request timed out after 30 seconds: ${method}`));
            }
          }, 30000); // 30 second timeout
          
          this.pendingRequests.set(id, { 
            resolve: (value: any) => {
              clearTimeout(timeoutId);
              resolve(value);
            }, 
            reject: (error: any) => {
              clearTimeout(timeoutId);
              reject(error);
            }
          });
          
          this.serverProcess!.stdin!.write(JSON.stringify(request) + '\n');
        });
      } catch (error: unknown) {
        const err = error instanceof Error ? error : new Error(String(error));
        lastError = err;
        
        // If this was the last retry, throw the error
        if (attempt === maxRetries) {
          throw err;
        }
        
        // Log the retry attempt
        console.error(`Request failed (attempt ${attempt + 1}/${maxRetries + 1}): ${err.message}`);
        console.error(`Retrying in ${retryDelay}ms...`);
        
        // Wait before retrying
        await new Promise(resolve => setTimeout(resolve, retryDelay));
      }
    }

    // This should never be reached due to the throw in the loop, but TypeScript doesn't know that
    throw lastError || new Error('Unknown error');
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
   * Get detailed information about a specific function
   */
  async getFunction(path: string, functionName: string): Promise<any> {
    return this.sendRequest('get_function', { path, function: functionName });
  }

  /**
   * Disassemble a function in a binary file
   */
  async disassembleFunction(path: string, functionName: string): Promise<string[]> {
    return this.sendRequest('disassemble_function', { path, function: functionName });
  }

  /**
   * List all sections/segments in a binary file
   */
  async listSections(path: string): Promise<any[]> {
    return this.sendRequest('list_sections', { path });
  }

  /**
   * List all imported functions in a binary file
   */
  async listImports(path: string): Promise<any[]> {
    return this.sendRequest('list_imports', { path });
  }

  /**
   * List all exported symbols in a binary file
   */
  async listExports(path: string): Promise<any[]> {
    return this.sendRequest('list_exports', { path });
  }

  /**
   * List all C++ namespaces in a binary file
   */
  async listNamespaces(path: string): Promise<string[]> {
    return this.sendRequest('list_namespaces', { path });
  }

  /**
   * List all defined data variables in a binary file
   */
  async listData(path: string): Promise<any[]> {
    return this.sendRequest('list_data', { path });
  }

  /**
   * Search for functions by name
   */
  async searchFunctions(path: string, query: string): Promise<any[]> {
    return this.sendRequest('search_functions', { path, query });
  }

  /**
   * Rename a function
   */
  async renameFunction(path: string, oldName: string, newName: string): Promise<any> {
    return this.sendRequest('rename_function', { path, old_name: oldName, new_name: newName });
  }

  /**
   * Rename a data variable
   */
  async renameData(path: string, address: string, newName: string): Promise<any> {
    return this.sendRequest('rename_data', { path, address, new_name: newName });
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

  /**
   * Analyze a binary file and generate a comprehensive report
   */
  async analyzeFile(path: string, outputPath?: string): Promise<any> {
    // This is a higher-level function that combines multiple API calls
    // to generate a comprehensive analysis report
    const report: any = {
      file_info: await this.getBinaryInfo(path),
      sections: await this.listSections(path),
      functions: [],
      imports: await this.listImports(path),
      exports: await this.listExports(path),
      namespaces: await this.listNamespaces(path),
      data_variables: await this.listData(path),
      timestamp: new Date().toISOString()
    };

    // Get detailed information for the first 10 functions
    const functionNames = await this.listFunctions(path);
    report.function_count = functionNames.length;
    
    const sampleFunctions = functionNames.slice(0, 10);
    for (const funcName of sampleFunctions) {
      try {
        const funcInfo = await this.getFunction(path, funcName);
        const decompiled = await this.decompileFunction(path, funcName);
        report.functions.push({
          ...funcInfo,
          decompiled: decompiled
        });
      } catch (err) {
        console.error(`Error analyzing function ${funcName}: ${err}`);
      }
    }

    // Save the report to a file if outputPath is provided
    if (outputPath) {
      const fs = require('fs');
      const reportJson = JSON.stringify(report, null, 2);
      fs.writeFileSync(outputPath, reportJson);
    }

    return report;
  }

  /**
   * Find potential vulnerabilities in a binary file
   */
  async findVulnerabilities(path: string): Promise<any[]> {
    // This is a higher-level function that analyzes the binary for potential vulnerabilities
    const vulnerabilities: any[] = [];
    
    try {
      // Get all functions
      const functionNames = await this.listFunctions(path);
      
      // Look for potentially vulnerable functions
      const dangerousFunctions = [
        'strcpy', 'strcat', 'sprintf', 'gets', 'memcpy', 'system',
        'exec', 'popen', 'scanf', 'malloc', 'free', 'realloc'
      ];
      
      // Search for each dangerous function
      for (const dangerFunc of dangerousFunctions) {
        try {
          const matches = await this.searchFunctions(path, dangerFunc);
          
          for (const match of matches) {
            // Get more details about the function
            const decompiled = await this.decompileFunction(path, match.name);
            
            vulnerabilities.push({
              type: 'dangerous_function',
              function_name: match.name,
              dangerous_call: dangerFunc,
              address: match.address,
              decompiled: decompiled
            });
          }
        } catch (err) {
          console.error(`Error searching for ${dangerFunc}: ${err}`);
        }
      }
      
      // Look for string format vulnerabilities
      try {
        const printfMatches = await this.searchFunctions(path, 'printf');
        for (const match of printfMatches) {
          const decompiled = await this.decompileFunction(path, match.name);
          
          // Simple heuristic: if printf is called with a variable as first argument
          if (decompiled && decompiled.includes('printf(') && !decompiled.includes('printf("%')) {
            vulnerabilities.push({
              type: 'format_string',
              function_name: match.name,
              address: match.address,
              decompiled: decompiled
            });
          }
        }
      } catch (err) {
        console.error(`Error analyzing format string vulnerabilities: ${err}`);
      }
    } catch (err) {
      console.error(`Error finding vulnerabilities: ${err}`);
    }
    
    return vulnerabilities;
  }

  /**
   * Compare two binary files and identify differences
   */
  async compareBinaries(path1: string, path2: string): Promise<any> {
    // This is a higher-level function that compares two binaries
    const comparison: any = {
      file1: await this.getBinaryInfo(path1),
      file2: await this.getBinaryInfo(path2),
      differences: {
        functions: {
          only_in_file1: [],
          only_in_file2: [],
          modified: []
        },
        sections: {
          only_in_file1: [],
          only_in_file2: [],
          modified: []
        }
      }
    };
    
    // Compare functions
    const functions1 = await this.listFunctions(path1);
    const functions2 = await this.listFunctions(path2);
    
    // Find functions only in file1
    for (const func of functions1) {
      if (!functions2.includes(func)) {
        comparison.differences.functions.only_in_file1.push(func);
      }
    }
    
    // Find functions only in file2
    for (const func of functions2) {
      if (!functions1.includes(func)) {
        comparison.differences.functions.only_in_file2.push(func);
      }
    }
    
    // Compare common functions
    const commonFunctions = functions1.filter(f => functions2.includes(f));
    for (const func of commonFunctions) {
      try {
        const decompiled1 = await this.decompileFunction(path1, func);
        const decompiled2 = await this.decompileFunction(path2, func);
        
        if (decompiled1 !== decompiled2) {
          comparison.differences.functions.modified.push({
            name: func,
            file1_code: decompiled1,
            file2_code: decompiled2
          });
        }
      } catch (err) {
        console.error(`Error comparing function ${func}: ${err}`);
      }
    }
    
    // Compare sections
    const sections1 = await this.listSections(path1);
    const sections2 = await this.listSections(path2);
    
    const sectionNames1 = sections1.map(s => s.name);
    const sectionNames2 = sections2.map(s => s.name);
    
    // Find sections only in file1
    for (const section of sections1) {
      if (!sectionNames2.includes(section.name)) {
        comparison.differences.sections.only_in_file1.push(section);
      }
    }
    
    // Find sections only in file2
    for (const section of sections2) {
      if (!sectionNames1.includes(section.name)) {
        comparison.differences.sections.only_in_file2.push(section);
      }
    }
    
    // Compare common sections
    const commonSectionNames = sectionNames1.filter(s => sectionNames2.includes(s));
    for (const sectionName of commonSectionNames) {
      const section1 = sections1.find(s => s.name === sectionName);
      const section2 = sections2.find(s => s.name === sectionName);
      
      if (section1.size !== section2.size || section1.start !== section2.start) {
        comparison.differences.sections.modified.push({
          name: sectionName,
          file1_section: section1,
          file2_section: section2
        });
      }
    }
    
    return comparison;
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
