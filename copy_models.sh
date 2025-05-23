#!/bin/bash

# Script to copy top-level folders from the current USB drive to the user's cache folder

# Get username
USERNAME=$(whoami)
echo "Hello $USERNAME!"

# Check if rsync is installed
if ! command -v rsync &> /dev/null; then
    echo "rsync is required but not installed. Please install rsync first."
    exit 1
fi

# Ensure cache directory exists
CACHE_DIR="/Users/$USERNAME/.cache/huggingface/hub/"
if [ ! -d "$CACHE_DIR" ]; then
    mkdir -p "$CACHE_DIR"
    echo "Created cache directory at $CACHE_DIR"
fi

# Get the current directory (USB drive)
USB_MOUNT_POINT=$(pwd)
echo "Using folders from: $USB_MOUNT_POINT"

# List only top-level directories
echo -e "\nFolders available on the USB drive:"
DIR_LIST=$(find "$USB_MOUNT_POINT" -mindepth 1 -maxdepth 1 -type d -not -path "*/\.*" | sort)

if [ -z "$DIR_LIST" ]; then
    echo "No folders found on the USB drive."
    exit 1
fi

# Display directories with numbers
echo "$DIR_LIST" | nl

# Prompt user to select a directory
echo -e "\nEnter the number of the folder you want to copy to your .cache folder: "
read DIR_NUM

# Get the selected directory
SELECTED_DIR=$(echo "$DIR_LIST" | sed "${DIR_NUM}q;d")

if [ -z "$SELECTED_DIR" ]; then
    echo "Invalid folder selection. Exiting."
    exit 1
fi

DIR_NAME=$(basename "$SELECTED_DIR")
echo "Selected folder: $DIR_NAME"

# Create target directory if it doesn't exist
TARGET_DIR="$CACHE_DIR/$DIR_NAME"
if [ ! -d "$TARGET_DIR" ]; then
    mkdir -p "$TARGET_DIR"
fi

# Copy the directory recursively with progress
echo -e "\nCopying folder $DIR_NAME to $CACHE_DIR..."
rsync -ah --progress "$SELECTED_DIR/" "$TARGET_DIR/"

# Check if copy was successful
if [ $? -eq 0 ]; then
    echo -e "\nFolder successfully copied to $TARGET_DIR"
    echo "Full path: $TARGET_DIR"
else
    echo -e "\nError: Failed to copy the folder."
    exit 1
fi

exit 0
