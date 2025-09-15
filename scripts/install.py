#!/usr/bin/env python3
"""
Install script for Hebrew Dashboard
Moves the built executable to ~/.local/bin and creates a desktop launcher
"""

import os
import shutil
import stat
from pathlib import Path

def ensure_local_bin():
    """Ensure ~/.local/bin directory exists"""
    local_bin = Path.home() / ".local" / "bin"
    local_bin.mkdir(parents=True, exist_ok=True)
    return local_bin

def install_executable():
    """Install the executable to ~/.local/bin"""
    project_dir = Path(__file__).parent
    exe_path = project_dir / "dist" / "hebrew-dashboard"
    
    if not exe_path.exists():
        print("✗ Executable not found. Please run './build.py' first.")
        return False
    
    local_bin = ensure_local_bin()
    target_path = local_bin / "hebrew-dashboard"
    
    try:
        # Copy executable
        shutil.copy2(exe_path, target_path)
        
        # Make executable
        target_path.chmod(target_path.stat().st_mode | stat.S_IEXEC)
        
        print(f"✓ Installed executable to: {target_path}")
        return True
        
    except Exception as e:
        print(f"✗ Failed to install executable: {e}")
        return False

def create_desktop_launcher():
    """Create a desktop launcher file"""
    local_bin = Path.home() / ".local" / "bin"
    exe_path = local_bin / "hebrew-dashboard"
    
    if not exe_path.exists():
        print("✗ Executable not found in ~/.local/bin")
        return False
    
    # Desktop applications directory
    desktop_dir = Path.home() / ".local" / "share" / "applications"
    desktop_dir.mkdir(parents=True, exist_ok=True)
    
    desktop_file = desktop_dir / "hebrew-dashboard.desktop"
    
    # Get project directory for icon (if exists)
    project_dir = Path(__file__).parent
    icon_path = project_dir / "static" / "favicon.ico"
    
    desktop_content = f"""[Desktop Entry]
Name=Hebrew Dashboard
Comment=A personalized dashboard with Hebrew calendar, weather, and more
Exec={exe_path}
Icon={icon_path if icon_path.exists() else 'calendar'}
Terminal=false
Type=Application
Categories=Utility;Office;
StartupNotify=true
"""
    
    try:
        with open(desktop_file, 'w') as f:
            f.write(desktop_content)
        
        # Make desktop file executable
        desktop_file.chmod(desktop_file.stat().st_mode | stat.S_IEXEC)
        
        print(f"✓ Created desktop launcher: {desktop_file}")
        return True
        
    except Exception as e:
        print(f"✗ Failed to create desktop launcher: {e}")
        return False

def check_path():
    """Check if ~/.local/bin is in PATH"""
    local_bin = Path.home() / ".local" / "bin"
    path_env = os.environ.get('PATH', '')
    
    if str(local_bin) not in path_env:
        print("\n⚠ Warning: ~/.local/bin is not in your PATH")
        print("Add the following line to your ~/.bashrc or ~/.zshrc:")
        print(f'export PATH="$PATH:{local_bin}"')
        print("Then restart your terminal or run: source ~/.bashrc")
        return False
    else:
        print("✓ ~/.local/bin is in PATH")
        return True

def main():
    """Main installation process"""
    print("Hebrew Dashboard Install Script")
    print("=" * 40)
    
    # Install executable
    if not install_executable():
        return False
    
    # Create desktop launcher
    create_desktop_launcher()
    
    # Check PATH
    in_path = check_path()
    
    print("\n" + "=" * 40)
    print("Installation completed!")
    print("\nYou can now:")
    if in_path:
        print("• Run 'hebrew-dashboard' from any terminal")
    print("• Launch from your application menu")
    print("• Find it in your desktop applications")
    
    print("\nTo uninstall:")
    print("• Remove ~/.local/bin/hebrew-dashboard")
    print("• Remove ~/.local/share/applications/hebrew-dashboard.desktop")
    
    return True

if __name__ == "__main__":
    main()
