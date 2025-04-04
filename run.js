#!/usr/bin/env node
/**
 * Binary Ninja MCP Bridge Runner
 * 
 * This script helps start all the necessary components for the Binary Ninja MCP setup.
 * It can start the HTTP server, the MCP bridge, or both.
 */

const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');

// Parse command line arguments
const args = process.argv.slice(2);
const command = args[0] || 'all'; // Default to 'all'

// Configuration
const HTTP_SERVER_PORT = 8088;
const HTTP_SERVER_HOST = '127.0.0.1';

// Helper function to run a command and pipe its output
function runCommand(cmd, args, name) {
  console.log(`Starting ${name}...`);
  
  const proc = spawn(cmd, args, {
    stdio: 'inherit',
    shell: true
  });
  
  proc.on('error', (err) => {
    console.error(`Error starting ${name}: ${err.message}`);
  });
  
  proc.on('close', (code) => {
    if (code !== 0) {
      console.error(`${name} exited with code ${code}`);
    } else {
      console.log(`${name} stopped`);
    }
  });
  
  return proc;
}

// Start the HTTP server
function startHttpServer() {
  const serverPath = path.join(__dirname, 'binaryninja_mcp_http_server.py');
  
  if (!fs.existsSync(serverPath)) {
    console.error(`HTTP server script not found at ${serverPath}`);
    process.exit(1);
  }
  
  return runCommand('python3', [
    serverPath,
    '--host', HTTP_SERVER_HOST,
    '--port', HTTP_SERVER_PORT.toString()
  ], 'HTTP Server');
}

// Start the MCP bridge
function startMcpBridge() {
  const bridgePath = path.join(__dirname, 'binaryninja-mcp-bridge.js');
  
  if (!fs.existsSync(bridgePath)) {
    console.error(`MCP bridge script not found at ${bridgePath}`);
    process.exit(1);
  }
  
  // Set the environment variable for the HTTP server URL
  process.env.BN_HTTP_SERVER = `http://${HTTP_SERVER_HOST}:${HTTP_SERVER_PORT}`;
  
  return runCommand('node', [bridgePath], 'MCP Bridge');
}

// Print usage information
function printUsage() {
  console.log(`
Usage: node run.js [command]

Commands:
  http     Start only the HTTP server
  bridge   Start only the MCP bridge
  all      Start both the HTTP server and MCP bridge (default)
  help     Show this help message

Example:
  node run.js all
`);
}

// Main function
function main() {
  switch (command.toLowerCase()) {
    case 'http':
      startHttpServer();
      break;
      
    case 'bridge':
      startMcpBridge();
      break;
      
    case 'all':
      startHttpServer();
      setTimeout(() => {
        startMcpBridge();
      }, 2000); // Wait 2 seconds for the HTTP server to start
      break;
      
    case 'help':
      printUsage();
      break;
      
    default:
      console.error(`Unknown command: ${command}`);
      printUsage();
      process.exit(1);
  }
}

// Run the main function
main();
