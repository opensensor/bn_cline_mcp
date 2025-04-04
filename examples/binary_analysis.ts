/**
 * Binary Analysis Example
 * 
 * This example demonstrates how to use the extended Binary Ninja MCP client
 * to perform advanced binary analysis tasks.
 */

import { BinaryNinjaClient } from '../client';
import * as path from 'path';
import * as fs from 'fs';

async function main() {
  if (process.argv.length < 3) {
    console.error('Usage: ts-node binary_analysis.ts <path_to_binary> [output_dir]');
    process.exit(1);
  }

  const binaryPath = process.argv[2];
  const outputDir = process.argv.length > 3 ? process.argv[3] : './analysis_output';
  
  // Create output directory if it doesn't exist
  if (!fs.existsSync(outputDir)) {
    fs.mkdirSync(outputDir, { recursive: true });
  }
  
  const client = new BinaryNinjaClient();

  try {
    // Start the server
    console.log('Starting Binary Ninja MCP server...');
    await client.start('/home/matteius/Documents/Cline/MCP/bn-mcp/binaryninja_server.py');
    console.log('Connected to Binary Ninja MCP server');

    // 1. Generate a comprehensive analysis report
    console.log('\n=== Generating Comprehensive Analysis Report ===');
    const reportPath = path.join(outputDir, 'analysis_report.json');
    const report = await client.analyzeFile(binaryPath, reportPath);
    console.log(`Analysis report generated and saved to ${reportPath}`);
    console.log(`Found ${report.function_count} functions, ${report.imports.length} imports, ${report.exports.length} exports`);

    // 2. Find potential vulnerabilities
    console.log('\n=== Scanning for Potential Vulnerabilities ===');
    const vulnerabilities = await client.findVulnerabilities(binaryPath);
    const vulnPath = path.join(outputDir, 'vulnerabilities.json');
    fs.writeFileSync(vulnPath, JSON.stringify(vulnerabilities, null, 2));
    console.log(`Found ${vulnerabilities.length} potential vulnerabilities`);
    console.log(`Vulnerability report saved to ${vulnPath}`);
    
    if (vulnerabilities.length > 0) {
      console.log('\nTop potential vulnerabilities:');
      for (let i = 0; i < Math.min(vulnerabilities.length, 3); i++) {
        const vuln = vulnerabilities[i];
        console.log(`${i+1}. ${vuln.type} in function ${vuln.function_name} at ${vuln.address}`);
        console.log(`   Dangerous call: ${vuln.dangerous_call || 'N/A'}`);
      }
    }

    // 3. Demonstrate function search and renaming
    console.log('\n=== Function Search and Manipulation ===');
    
    // Search for functions containing "main"
    const mainFunctions = await client.searchFunctions(binaryPath, 'main');
    console.log(`Found ${mainFunctions.length} functions matching "main"`);
    
    if (mainFunctions.length > 0) {
      // Get the first match
      const mainFunc = mainFunctions[0];
      console.log(`\nFunction details for ${mainFunc.name}:`);
      console.log(`Address: ${mainFunc.address}`);
      
      // Get detailed information
      const funcInfo = await client.getFunction(binaryPath, mainFunc.name);
      console.log(`Symbol type: ${funcInfo.symbol?.type || 'N/A'}`);
      
      // Disassemble the function
      console.log('\nDisassembly:');
      const disasm = await client.disassembleFunction(binaryPath, mainFunc.name);
      for (let i = 0; i < Math.min(disasm.length, 5); i++) {
        console.log(`  ${disasm[i]}`);
      }
      if (disasm.length > 5) {
        console.log(`  ... and ${disasm.length - 5} more lines`);
      }
      
      // Decompile the function
      console.log('\nDecompiled code:');
      const decompiled = await client.decompileFunction(binaryPath, mainFunc.name);
      const decompLines = decompiled.split('\n');
      for (let i = 0; i < Math.min(decompLines.length, 5); i++) {
        console.log(`  ${decompLines[i]}`);
      }
      if (decompLines.length > 5) {
        console.log(`  ... and ${decompLines.length - 5} more lines`);
      }
      
      // Save the decompiled code to a file
      const decompPath = path.join(outputDir, `${mainFunc.name}.c`);
      fs.writeFileSync(decompPath, decompiled);
      console.log(`\nDecompiled code saved to ${decompPath}`);
      
      // Example of renaming (commented out to avoid modifying the binary)
      /*
      console.log('\nRenaming function...');
      const newName = `${mainFunc.name}_analyzed`;
      const renameResult = await client.renameFunction(binaryPath, mainFunc.name, newName);
      console.log(`Rename result: ${JSON.stringify(renameResult)}`);
      */
    }

    // 4. List and analyze data variables
    console.log('\n=== Data Variables Analysis ===');
    const dataVars = await client.listData(binaryPath);
    console.log(`Found ${dataVars.length} data variables`);
    
    if (dataVars.length > 0) {
      console.log('\nSample data variables:');
      for (let i = 0; i < Math.min(dataVars.length, 5); i++) {
        const dataVar = dataVars[i];
        console.log(`${i+1}. ${dataVar.name || '(unnamed)'} at ${dataVar.address}`);
        console.log(`   Type: ${dataVar.type || 'unknown'}`);
        console.log(`   Value: ${dataVar.value || 'N/A'}`);
      }
      
      // Save data variables to a file
      const dataPath = path.join(outputDir, 'data_variables.json');
      fs.writeFileSync(dataPath, JSON.stringify(dataVars, null, 2));
      console.log(`\nData variables saved to ${dataPath}`);
    }

    // 5. Analyze imports and exports
    console.log('\n=== Imports and Exports Analysis ===');
    const imports = await client.listImports(binaryPath);
    const exports = await client.listExports(binaryPath);
    
    console.log(`Found ${imports.length} imports and ${exports.length} exports`);
    
    // Save imports and exports to files
    const importsPath = path.join(outputDir, 'imports.json');
    const exportsPath = path.join(outputDir, 'exports.json');
    
    fs.writeFileSync(importsPath, JSON.stringify(imports, null, 2));
    fs.writeFileSync(exportsPath, JSON.stringify(exports, null, 2));
    
    console.log(`Imports saved to ${importsPath}`);
    console.log(`Exports saved to ${exportsPath}`);
    
    // 6. Analyze C++ namespaces (if any)
    console.log('\n=== C++ Namespaces Analysis ===');
    const namespaces = await client.listNamespaces(binaryPath);
    
    if (namespaces.length > 0) {
      console.log(`Found ${namespaces.length} C++ namespaces:`);
      for (let i = 0; i < Math.min(namespaces.length, 5); i++) {
        console.log(`  ${i+1}. ${namespaces[i]}`);
      }
      if (namespaces.length > 5) {
        console.log(`  ... and ${namespaces.length - 5} more namespaces`);
      }
      
      // Save namespaces to a file
      const namespacesPath = path.join(outputDir, 'namespaces.json');
      fs.writeFileSync(namespacesPath, JSON.stringify(namespaces, null, 2));
      console.log(`Namespaces saved to ${namespacesPath}`);
    } else {
      console.log('No C++ namespaces found in the binary');
    }

    console.log('\n=== Analysis Complete ===');
    console.log(`All analysis results have been saved to ${outputDir}`);
    
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
