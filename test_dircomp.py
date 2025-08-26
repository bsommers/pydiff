#!/usr/bin/env python3
"""
Test script for the directory comparison tool.
This tests the core functionality without the curses interface.
"""

import sys
sys.path.insert(0, '/Users/bill')
from dircomp import DirectoryComparer

def test_comparison():
    """Test the directory comparison functionality."""
    comparer = DirectoryComparer('/Users/bill/test_dirs/dir1', '/Users/bill/test_dirs/dir2')
    comparer.scan_directories()
    
    print(f"Found {len(comparer.results)} files to compare:")
    print(f"Left dir: {comparer.left_dir}")
    print(f"Right dir: {comparer.right_dir}")
    print()
    
    for i, result in enumerate(comparer.results):
        left_exists = result.left_file and result.left_file.exists
        right_exists = result.right_file and result.right_file.exists
        
        left_info = f"Size: {result.left_file.size}" if left_exists else "Missing"
        right_info = f"Size: {result.right_file.size}" if right_exists else "Missing"
        
        print(f"{i+1:2}. {result.relative_path}")
        print(f"    Left:  {left_info}")
        print(f"    Right: {right_info}")
        print(f"    Status: {result.status} ({result.symbol})")
        print()
    
    return comparer

if __name__ == "__main__":
    comparer = test_comparison()
    
    print("Testing file copy operations...")
    
    # Test copying a file from left to right (file2.txt should only exist on left)
    for i, result in enumerate(comparer.results):
        if result.relative_path == "file2.txt" and result.status == "ONLY_LEFT":
            print(f"Copying {result.relative_path} from left to right...")
            success = comparer.copy_file_left_to_right(i)
            print(f"Copy result: {'Success' if success else 'Failed'}")
            
            # Refresh and check
            comparer.scan_directories()
            new_result = comparer.results[i]
            print(f"New status: {new_result.status} ({new_result.symbol})")
            break
    
    print("\nTest completed!")
