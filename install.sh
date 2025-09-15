#!/bin/bash
set -e

# Hebrew Dashboard Install Script
# Moves the built executable to ~/.local/bin and creates a desktop launcher

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
EXE_PATH="$SCRIPT_DIR/dist/hebrew-dashboard"
LOCAL_BIN="$HOME/.local/bin"
TARGET_PATH="$LOCAL_BIN/hebrew-dashboard"
DESKTOP_DIR="$HOME/.local/share/applications"
DESKTOP_FILE="$DESKTOP_DIR/hebrew-dashboard.desktop"

echo "Hebrew Dashboard Install Script"
echo "==============================="

# Check if executable exists
if [ ! -f "$EXE_PATH" ]; then
    echo "✗ Executable not found. Please run './build.sh' first."
    exit 1
fi

# Ensure ~/.local/bin exists
mkdir -p "$LOCAL_BIN"

# Install executable
echo "Installing executable to ~/.local/bin..."
cp "$EXE_PATH" "$TARGET_PATH"
chmod +x "$TARGET_PATH"
echo "✓ Installed executable to: $TARGET_PATH"

# Create desktop launcher
echo "Creating desktop launcher..."
mkdir -p "$DESKTOP_DIR"

# Check for icon
ICON_PATH="$SCRIPT_DIR/static/favicon.ico"
if [ -f "$ICON_PATH" ]; then
    ICON_ENTRY="Icon=$ICON_PATH"
else
    ICON_ENTRY="Icon=calendar"
fi

cat > "$DESKTOP_FILE" << EOF
[Desktop Entry]
Name=Hebrew Dashboard
Comment=A personalized dashboard with Hebrew calendar, weather, and more
Exec=$TARGET_PATH
$ICON_ENTRY
Terminal=false
Type=Application
Categories=Utility;Office;
StartupNotify=true
EOF

chmod +x "$DESKTOP_FILE"
echo "✓ Created desktop launcher: $DESKTOP_FILE"

# Check if ~/.local/bin is in PATH
if [[ ":$PATH:" != *":$LOCAL_BIN:"* ]]; then
    echo ""
    echo "⚠ Warning: ~/.local/bin is not in your PATH"
    echo "Add the following line to your ~/.bashrc or ~/.zshrc:"
    echo "export PATH=\"\$PATH:$LOCAL_BIN\""
    echo "Then restart your terminal or run: source ~/.bashrc"
    PATH_IN_PATH=false
else
    echo "✓ ~/.local/bin is in PATH"
    PATH_IN_PATH=true
fi

echo ""
echo "==============================="
echo "Installation completed!"
echo ""
echo "You can now:"
if [ "$PATH_IN_PATH" = true ]; then
    echo "• Run 'hebrew-dashboard' from any terminal"
fi
echo "• Launch from your application menu"
echo "• Find it in your desktop applications"
echo ""
echo "To uninstall:"
echo "• Remove $TARGET_PATH"
echo "• Remove $DESKTOP_FILE"
