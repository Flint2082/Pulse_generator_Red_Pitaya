#!/bin/bash

# # Launch the client side application

# # Set the script directory
# SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# # Change to the script directory
# cd "$SCRIPT_DIR"

# # Echo the current directory
# echo "Current directory: $(pwd)"

# # Check if the top.bit.bin exists
# if [ ! -f "$HOME/top.bit.bin" ]; then
#     echo "Error: top.bit.bin not found"
#     exit 1
# fi

# # Load FPGA bitstream 
# /opt/redpitaya/bin/fpgautil -b $HOME/top.bit.bin

