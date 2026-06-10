"""
Entry point for PyInstaller-bundled Nokton backend.
This script is used as the main entry point when building with PyInstaller.
"""
import sys
import os

# When running as a PyInstaller bundle, add the bundle dir to path
if getattr(sys, 'frozen', False):
    bundle_dir = sys._MEIPASS
    os.chdir(bundle_dir)
    sys.path.insert(0, bundle_dir)

from backend.main import run

if __name__ == "__main__":
    run()
