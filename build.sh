#!/bin/bash
set -e

# Hebrew Dashboard Build Script
# Creates a standalone executable using PyInstaller with uv venv management

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$SCRIPT_DIR/.venv"

echo "Hebrew Dashboard Build Script"
echo "============================="

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo "Error: uv is not installed. Please install uv first:"
    echo "curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

# Create virtual environment if it doesn't exist
if [ ! -d "$VENV_DIR" ]; then
    echo "Creating virtual environment with uv..."
    cd "$SCRIPT_DIR"
    uv venv
    echo "✓ Virtual environment created"
else
    echo "✓ Virtual environment found"
fi

# Install dependencies
echo "Installing dependencies..."
cd "$SCRIPT_DIR"
uv pip install -r requirements.txt
uv pip install pyinstaller

echo "✓ Dependencies installed"

# Build executable
echo "Building Hebrew Dashboard executable..."

# Activate virtual environment and run PyInstaller
source "$VENV_DIR/bin/activate"

pyinstaller \
    --onefile \
    --windowed \
    --name hebrew-dashboard \
    --add-data "templates:templates" \
    --add-data "static:static" \
    --add-data ".env.example:." \
    --hidden-import google.oauth2.credentials \
    --hidden-import google_auth_oauthlib.flow \
    --hidden-import googleapiclient.discovery \
    --hidden-import googleapiclient.errors \
    --hidden-import google.auth.transport.requests \
    --hidden-import requests \
    --hidden-import feedparser \
    --hidden-import dateutil \
    --hidden-import flask \
    --hidden-import dotenv \
    --collect-all flask \
    --collect-all google-auth \
    --collect-all google-auth-oauthlib \
    --collect-all google-api-python-client \
    app.py

# Check if build was successful
if [ -f "$SCRIPT_DIR/dist/hebrew-dashboard" ]; then
    echo "✓ Build completed successfully"
    echo "✓ Executable created at: $SCRIPT_DIR/dist/hebrew-dashboard"
    
    # Clean up build artifacts
    echo "Cleaning up build artifacts..."
    rm -rf "$SCRIPT_DIR/build"
    rm -f "$SCRIPT_DIR/hebrew-dashboard.spec"
    echo "✓ Cleaned build directory and spec file"
    
    echo ""
    echo "============================="
    echo "Build completed successfully!"
    echo "Executable location: $SCRIPT_DIR/dist/hebrew-dashboard"
    echo ""
    echo "Next steps:"
    echo "1. Run './install.sh' to install to ~/.local/bin"
    echo "2. Or run './update.sh' to build and install in one step"
else
    echo "✗ Build failed - executable not found"
    exit 1
fi
