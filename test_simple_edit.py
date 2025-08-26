#!/usr/bin/env python3
"""
Simple test to check if the basic edit functionality works
"""

import sys
import os
import tempfile
sys.path.insert(0, '/Users/bill/src/python/pydiff')

from dircomp import DirectoryComparer

# Create a temporary "safe" editor script
with tempfile.NamedTemporaryFile(mode='w', suffix='.sh', delete=False) as f:
    f.write('#!/bin/bash\n')
    f.write('echo "Editor called with: $@"\n')
    f.write('echo "Mock editing complete" >> "$1"\n')
    temp_editor = f.name

# Make it executable
os.chmod(temp_editor, 0o755)

# Set the mock editor
os.environ['EDITOR'] = temp_editor

try:
    # Test the functionality
    comparer = DirectoryComparer('t1', 't2')
    comparer.scan_directories()
    
    print("Testing edit functionality with mock editor...")
    
    # Find a file to test on
    test_index = -1
    for i, result in enumerate(comparer.results):
        if result.left_file and result.left_file.exists:
            test_index = i
            print(f"Testing on: {result.relative_path}")
            break
    
    if test_index >= 0:
        success = comparer.edit_file(test_index, "left")
        print(f"Edit result: {'Success' if success else 'Failed'}")
        
        if success:
            print("✅ Editing functionality is working!")
        else:
            print("❌ Editing functionality failed")
    else:
        print("❌ No files found for testing")

finally:
    # Clean up
    try:
        os.unlink(temp_editor)
    except:
        pass
