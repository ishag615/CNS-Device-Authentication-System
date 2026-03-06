#!/usr/bin/env python3
"""
Automated setup script - copies all project files to your GitHub repo.
Run this from your repository root directory.

Usage:
    python setup_project.py
"""

import os
import sys
import shutil
from pathlib import Path

# Path to the source files (outputs folder)
SOURCE_DIR = "/mnt/user-data/outputs/iot-authentication-gateway"
CURRENT_DIR = os.getcwd()

# Files to copy from source to repo
FILES_TO_COPY = [
    ("gateway/db_manager.py", "gateway/db_manager.py"),
    ("gateway/crypto_utils.py", "gateway/crypto_utils.py"),
    ("device/iot_client.py", "device/iot_client.py"),
    ("scripts/setup_database.py", "scripts/setup_database.py"),
    ("scripts/enroll_device.py", "scripts/enroll_device.py"),
    ("scripts/manage_devices.py", "scripts/manage_devices.py"),
    ("requirements.txt", "requirements.txt"),
    ("GETTING_STARTED.md", "GETTING_STARTED.md"),
]

# Directories to create
DIRS_TO_CREATE = [
    "gateway",
    "device",
    "scripts",
    "config",
    "tests"
]

# __init__.py files to create
INIT_FILES = [
    "gateway/__init__.py",
    "device/__init__.py",
    "scripts/__init__.py",
    "config/__init__.py",
    "tests/__init__.py"
]


def print_header(text):
    """Print a formatted header."""
    print("\n" + "=" * 70)
    print(f"  {text}")
    print("=" * 70 + "\n")


def create_directories():
    """Create required directories."""
    print("Step 1: Creating directories...")
    for directory in DIRS_TO_CREATE:
        os.makedirs(directory, exist_ok=True)
        print(f"  ✓ Created: {directory}/")
    print()


def create_init_files():
    """Create __init__.py files."""
    print("Step 2: Creating __init__.py files...")
    for init_file in INIT_FILES:
        with open(init_file, 'w') as f:
            f.write("# Package module\n")
        print(f"  ✓ Created: {init_file}")
    print()


def copy_files():
    """Copy implementation files from source."""
    print("Step 3: Copying implementation files...")
    
    for source_file, dest_file in FILES_TO_COPY:
        source_path = os.path.join(SOURCE_DIR, source_file)
        dest_path = os.path.join(CURRENT_DIR, dest_file)
        
        # Create destination directory if needed
        os.makedirs(os.path.dirname(dest_path), exist_ok=True)
        
        if os.path.exists(source_path):
            shutil.copy2(source_path, dest_path)
            print(f"  ✓ Copied: {source_file}")
        else:
            print(f"  ✗ NOT FOUND: {source_file}")
            print(f"    Expected at: {source_path}")
    print()


def verify_setup():
    """Verify all files were created."""
    print("Step 4: Verifying setup...")
    
    all_files = [dest for _, dest in FILES_TO_COPY] + INIT_FILES
    missing = []
    
    for file_path in all_files:
        if os.path.exists(file_path):
            print(f"  ✓ {file_path}")
        else:
            print(f"  ✗ {file_path} (MISSING)")
            missing.append(file_path)
    
    print()
    return len(missing) == 0


def print_next_steps():
    """Print next steps."""
    print_header("✓ Setup Complete!")
    
    print("Your repository now has:\n")
    print("  ✓ gateway/db_manager.py       - Database management")
    print("  ✓ gateway/crypto_utils.py     - Signature verification")
    print("  ✓ device/iot_client.py        - Device authentication library")
    print("  ✓ scripts/setup_database.py   - Database initialization")
    print("  ✓ scripts/enroll_device.py    - Device enrollment")
    print("  ✓ scripts/manage_devices.py   - Device management")
    print("  ✓ requirements.txt            - Python dependencies")
    print("  ✓ GETTING_STARTED.md          - Setup & usage guide")
    print()
    
    print_header("Next Steps:")
    
    print("1. Install dependencies:")
    print("   $ pip install -r requirements.txt\n")
    
    print("2. Initialize database:")
    print("   $ python scripts/setup_database.py\n")
    
    print("3. Test device enrollment:")
    print("   $ python scripts/enroll_device.py --device-id test_device\n")
    
    print("4. List devices:")
    print("   $ python scripts/manage_devices.py list\n")
    
    print("5. Commit to GitHub:")
    print("   $ git add .")
    print("   $ git commit -m 'Add core authentication gateway implementation'")
    print("   $ git push\n")
    
    print_header("What to implement next:")
    
    print("  1. gateway/controller.py      - Ryu SDN OpenFlow controller")
    print("  2. tests/                     - Unit and integration tests")
    print("  3. Mininet testbed setup      - For evaluation")
    print()


def main():
    print_header("IoT Authentication Gateway - Automated Setup")
    
    print(f"Current directory: {CURRENT_DIR}\n")
    print(f"Source directory: {SOURCE_DIR}\n")
    
    # Check if we can access source files
    if not os.path.exists(SOURCE_DIR):
        print("ERROR: Source directory not found!")
        print(f"Expected: {SOURCE_DIR}")
        print("\nMake sure you're running this in the right location.")
        sys.exit(1)
    
    # Create directories
    try:
        create_directories()
    except Exception as e:
        print(f"ERROR creating directories: {e}")
        sys.exit(1)
    
    # Create __init__.py files
    try:
        create_init_files()
    except Exception as e:
        print(f"ERROR creating __init__.py files: {e}")
        sys.exit(1)
    
    # Copy files
    try:
        copy_files()
    except Exception as e:
        print(f"ERROR copying files: {e}")
        sys.exit(1)
    
    # Verify
    if verify_setup():
        print_next_steps()
        print_header("Ready to go! 🚀")
        return 0
    else:
        print("\nWARNING: Some files may be missing. Check above for details.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
