#!/usr/bin/env python3
"""
Demo script to show what the curses interface looks like.
This simulates the interface without actually running curses.
"""

import sys
sys.path.insert(0, '/Users/bill')
from dircomp import DirectoryComparer
from datetime import datetime

def format_size(size: int) -> str:
    """Format file size in human readable format."""
    for unit in ['B', 'K', 'M', 'G', 'T']:
        if size < 1024:
            return f"{size:3.0f}{unit}"
        size /= 1024
    return f"{size:.1f}P"

def demo_interface():
    """Show what the interface looks like."""
    comparer = DirectoryComparer('/Users/bill/test_dirs/dir1', '/Users/bill/test_dirs/dir2')
    comparer.scan_directories()
    
    width = 80  # Simulate 80-character terminal width
    
    # Header
    print("=" * width)
    header = f" Directory Comparison: {comparer.left_dir.name} <-> {comparer.right_dir.name} "
    print(header.ljust(width))
    print("=" * width)
    
    # Column headers
    left_header = f"{'LEFT':<{width//3}}"
    middle_header = f"{'STATUS':<8}"
    right_header = f"RIGHT"
    headers = left_header + middle_header + right_header
    print(headers[:width])
    print("-" * width)
    
    # File listing
    for i, result in enumerate(comparer.results):
        # Determine status symbol and description
        symbol = result.symbol
        status_desc = {
            "ONLY_RIGHT": "[Only on right]",
            "ONLY_LEFT": "[Only on left]",
            "DIFFERENT_SIZE": "[Different size]",
            "DIFFERENT_TIME": "[Different time]",
            "DIFFERENT_CONTENT": "[Different content]",
            "IDENTICAL": "[Identical]"
        }.get(result.status, "[Unknown]")
        
        # Show selection indicator
        indicator = ">>" if i == 0 else "  "  # Simulate first item selected
        
        # Print filename
        print(f"{indicator} {result.relative_path}")
        
        # Format file information
        left_info = "Missing"
        if result.left_file and result.left_file.exists:
            size_str = format_size(result.left_file.size)
            time_str = datetime.fromtimestamp(result.left_file.mtime).strftime("%m/%d %H:%M")
            left_info = f"{size_str:>8} {time_str}"
        
        right_info = "Missing"
        if result.right_file and result.right_file.exists:
            size_str = format_size(result.right_file.size)
            time_str = datetime.fromtimestamp(result.right_file.mtime).strftime("%m/%d %H:%M")
            right_info = f"{size_str:>8} {time_str}"
        
        # Create the display line
        left_width = width // 3 - 1
        middle_width = 8
        right_width = width - left_width - middle_width - 2
        
        left_part = f"{left_info:<{left_width}}"[:left_width]
        middle_part = f"{symbol:^{middle_width}}"
        right_part = f"{right_info:<{right_width}}"[:right_width]
        
        line = left_part + " " + middle_part + " " + right_part
        print(f"   {line[:width-3]}")
        
        print(f"   {status_desc}")
        print()
    
    print("-" * width)
    print(f"Files: {len(comparer.results)} | Selected: 1/{len(comparer.results)}")
    print("↑↓:Select F3/<:Copy→Left F4/>:Copy→Right R:Refresh H:Help Q:Quit")
    print("=" * width)

if __name__ == "__main__":
    demo_interface()
