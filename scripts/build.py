#!/usr/bin/env python3
"""
Build script for Hebrew Dashboard
Creates a standalone executable using PyInstaller
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

def check_pyinstaller():
    """Check if PyInstaller is installed, install if not"""
    try:
        import PyInstaller
        print("✓ PyInstaller found")
    except ImportError:
        print("Installing PyInstaller...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])

def build_executable():
    """Build the executable using PyInstaller"""
    print("Building Hebrew Dashboard executable...")
    
    # Get the project directory
    project_dir = Path(__file__).parent
    
    # PyInstaller command
    cmd = [
        "pyinstaller",
        "--onefile",
        "--windowed",
        "--name", "hebrew-dashboard",
        "--add-data", f"{project_dir}/templates{os.pathsep}templates",
        "--add-data", f"{project_dir}/static{os.pathsep}static",
        "--add-data", f"{project_dir}/.env.example{os.pathsep}.",
        "--hidden-import", "google.oauth2.credentials",
        "--hidden-import", "google_auth_oauthlib.flow",
        "--hidden-import", "googleapiclient.discovery",
        "--hidden-import", "googleapiclient.errors",
        "--hidden-import", "google.auth.transport.requests",
        "--hidden-import", "requests",
        "--hidden-import", "feedparser",
        "--hidden-import", "dateutil",
        "--hidden-import", "flask",
        "--hidden-import", "dotenv",
        "--collect-all", "flask",
        "--collect-all", "google-auth",
        "--collect-all", "google-auth-oauthlib",
        "--collect-all", "google-api-python-client",
        str(project_dir / "app.py")
    ]
    
    try:
        subprocess.check_call(cmd, cwd=project_dir)
        print("✓ Build completed successfully")
        
        # Check if executable was created
        exe_path = project_dir / "dist" / "hebrew-dashboard"
        if exe_path.exists():
            print(f"✓ Executable created at: {exe_path}")
            return exe_path
        else:
            print("✗ Executable not found after build")
            return None
            
    except subprocess.CalledProcessError as e:
        print(f"✗ Build failed: {e}")
        return None

def clean_build_artifacts():
    """Clean up PyInstaller build artifacts"""
    project_dir = Path(__file__).parent
    
    # Remove build directory
    build_dir = project_dir / "build"
    if build_dir.exists():
        shutil.rmtree(build_dir)
        print("✓ Cleaned build directory")
    
    # Remove spec file
    spec_file = project_dir / "hebrew-dashboard.spec"
    if spec_file.exists():
        spec_file.unlink()
        print("✓ Cleaned spec file")

def main():
    """Main build process"""
    print("Hebrew Dashboard Build Script")
    print("=" * 40)
    
    # Check dependencies
    check_pyinstaller()
    
    # Build executable
    exe_path = build_executable()
    
    if exe_path:
        print("\n" + "=" * 40)
        print("Build completed successfully!")
        print(f"Executable location: {exe_path}")
        print("\nNext steps:")
        print("1. Run './install.py' to install to ~/.local/bin")
        print("2. Or run './update.py' to build and install in one step")
    else:
        print("\n" + "=" * 40)
        print("Build failed. Please check the error messages above.")
        sys.exit(1)
    
    # Clean up build artifacts
    clean_build_artifacts()

if __name__ == "__main__":
    main()
