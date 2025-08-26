#!/usr/bin/env python3

import os
import time
from dircomp import DirectoryComparer

def test_filename_display():
    """Test that filenames display correctly without truncation issues."""
    print("Testing filename display...")
    
    # Create comparer
    comparer = DirectoryComparer("t1", "t2")
    comparer.scan_directories()
    
    print(f"Found {len(comparer.results)} files for comparison")
    
    for i, result in enumerate(comparer.results):
        print(f"{i+1:2d}. {result.relative_path:<60} [{result.status}]")
    
    print("\nFilename display test completed!")
    return True

if __name__ == "__main__":
    test_filename_display()
