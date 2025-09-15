#!/usr/bin/env python3
"""
Update script for Hebrew Dashboard
Rebuilds the executable and reinstalls it to ~/.local/bin
"""

import subprocess
import sys
from pathlib import Path

def run_build():
    """Run the build script"""
    print("Running build script...")
    build_script = Path(__file__).parent / "build.py"
    
    try:
        result = subprocess.run([sys.executable, str(build_script)], 
                              capture_output=False, text=True)
        if result.returncode == 0:
            print("✓ Build completed successfully")
            return True
        else:
            print("✗ Build failed")
            return False
    except Exception as e:
        print(f"✗ Failed to run build script: {e}")
        return False

def run_install():
    """Run the install script"""
    print("\nRunning install script...")
    install_script = Path(__file__).parent / "install.py"
    
    try:
        result = subprocess.run([sys.executable, str(install_script)], 
                              capture_output=False, text=True)
        if result.returncode == 0:
            print("✓ Installation completed successfully")
            return True
        else:
            print("✗ Installation failed")
            return False
    except Exception as e:
        print(f"✗ Failed to run install script: {e}")
        return False

def check_existing_installation():
    """Check if Hebrew Dashboard is already installed"""
    local_bin = Path.home() / ".local" / "bin" / "hebrew-dashboard"
    desktop_file = Path.home() / ".local" / "share" / "applications" / "hebrew-dashboard.desktop"
    
    if local_bin.exists():
        print(f"✓ Found existing installation: {local_bin}")
        if desktop_file.exists():
            print(f"✓ Found existing desktop launcher: {desktop_file}")
        return True
    else:
        print("ℹ No existing installation found")
        return False

def main():
    """Main update process"""
    print("Hebrew Dashboard Update Script")
    print("=" * 40)
    
    # Check for existing installation
    has_existing = check_existing_installation()
    
    if has_existing:
        print("\nThis will rebuild and replace your current installation.")
        response = input("Continue? (y/N): ").strip().lower()
        if response not in ['y', 'yes']:
            print("Update cancelled.")
            return
    
    print("\nStarting update process...")
    
    # Run build
    if not run_build():
        print("\n" + "=" * 40)
        print("Update failed during build phase.")
        sys.exit(1)
    
    # Run install
    if not run_install():
        print("\n" + "=" * 40)
        print("Update failed during install phase.")
        sys.exit(1)
    
    print("\n" + "=" * 40)
    print("Update completed successfully!")
    
    if has_existing:
        print("Your Hebrew Dashboard installation has been updated.")
    else:
        print("Hebrew Dashboard has been installed for the first time.")
    
    print("\nYou can now launch the application from:")
    print("• Terminal: hebrew-dashboard")
    print("• Application menu: Hebrew Dashboard")

if __name__ == "__main__":
    main()
