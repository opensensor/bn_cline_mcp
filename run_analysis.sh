#!/bin/bash
# Script to run the binary analysis example

# Check if a binary path was provided
if [ $# -lt 1 ]; then
  echo "Usage: $0 <path_to_binary> [output_dir]"
  exit 1
fi

BINARY_PATH="$1"
OUTPUT_DIR="${2:-./analysis_output}"

# Check if the binary exists
if [ ! -f "$BINARY_PATH" ]; then
  echo "Error: Binary file '$BINARY_PATH' not found"
  exit 1
fi

# Create the output directory if it doesn't exist
mkdir -p "$OUTPUT_DIR"

# Run the analysis script
echo "Running binary analysis on '$BINARY_PATH'..."
echo "Results will be saved to '$OUTPUT_DIR'"
echo

# Make sure we're in the right directory
cd "$(dirname "$0")"

# Run the TypeScript example using ts-node
npx ts-node examples/binary_analysis.ts "$BINARY_PATH" "$OUTPUT_DIR"

# Check if the analysis was successful
if [ $? -eq 0 ]; then
  echo
  echo "Analysis completed successfully!"
  echo "Results are available in '$OUTPUT_DIR'"
else
  echo
  echo "Analysis failed. Please check the error messages above."
fi
