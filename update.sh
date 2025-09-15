#!/bin/bash
set -e

# Hebrew Dashboard Update Script
# Rebuilds the executable and reinstalls it to ~/.local/bin

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOCAL_BIN="$HOME/.local/bin"
TARGET_PATH="$LOCAL_BIN/hebrew-dashboard"
DESKTOP_FILE="$HOME/.local/share/applications/hebrew-dashboard.desktop"

echo "Hebrew Dashboard Update Script"
echo "=============================="

# Check for existing installation
if [ -f "$TARGET_PATH" ]; then
    echo "✓ Found existing installation: $TARGET_PATH"
    if [ -f "$DESKTOP_FILE" ]; then
        echo "✓ Found existing desktop launcher: $DESKTOP_FILE"
    fi
    HAS_EXISTING=true
else
    echo "ℹ No existing installation found"
    HAS_EXISTING=false
fi

if [ "$HAS_EXISTING" = true ]; then
    echo ""
    echo "This will rebuild and replace your current installation."
    read -p "Continue? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Update cancelled."
        exit 0
    fi
fi

echo ""
echo "Starting update process..."

# Run build script
echo "Running build script..."
if ! "$SCRIPT_DIR/build.sh"; then
    echo ""
    echo "=============================="
    echo "Update failed during build phase."
    exit 1
fi

# Run install script
echo ""
echo "Running install script..."
if ! "$SCRIPT_DIR/install.sh"; then
    echo ""
    echo "=============================="
    echo "Update failed during install phase."
    exit 1
fi

echo ""
echo "=============================="
echo "Update completed successfully!"

if [ "$HAS_EXISTING" = true ]; then
    echo "Your Hebrew Dashboard installation has been updated."
else
    echo "Hebrew Dashboard has been installed for the first time."
fi

echo ""
echo "You can now launch the application from:"
echo "• Terminal: hebrew-dashboard"
echo "• Application menu: Hebrew Dashboard"
