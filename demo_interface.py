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
    comparer = DirectoryComparer('t1', 't2')
    comparer.scan_directories()
    
    width = 80  # Simulate 80-character terminal width
    
    # Header
    print("=" * width)
    header = f" Directory Comparison: {comparer.left_dir.name} <-> {comparer.right_dir.name} "
    print(header.ljust(width))
    print("=" * width)
    
    # Draw detailed column headers with clear sections
    # Calculate proper column widths - make them exactly match the content positioning
    left_width = 25  # Fixed width for left column
    status_width = 10  # Fixed width for status column  
    right_width = width - left_width - status_width - 4  # Remaining width for right column
    
    headers_line1 = "┌" + "─" * left_width + "┬" + "─" * status_width + "┬" + "─" * right_width + "┐"
    headers_line2 = f"│{'LEFT DIRECTORY':<{left_width}}│{'STATUS':<{status_width}}│{'RIGHT DIRECTORY':<{right_width}}│"
    headers_line3 = "├" + "─" * left_width + "┼" + "─" * status_width + "┼" + "─" * right_width + "┤"
    
    try:
        print(headers_line1[:width])
        print(headers_line2[:width]) 
        print(headers_line3[:width])
    except:
        # Fallback to simple headers if box drawing fails
        print("-" * width)
        headers = f"{'LEFT':<{width//3}}{'STATUS':<10}{'RIGHT'}"
        print(headers[:width])
        print("-" * width)
    
    # File listing - one file per line with all information
    for i, result in enumerate(comparer.results):
        # Format file information for left side
        left_info = "─ MISSING ─"
        if result.left_file and result.left_file.exists:
            size_str = format_size(result.left_file.size)
            time_str = datetime.fromtimestamp(result.left_file.mtime).strftime("%m/%d %H:%M")
            left_info = f"{size_str} {time_str}"
        
        # Format file information for right side  
        right_info = "─ MISSING ─"
        if result.right_file and result.right_file.exists:
            size_str = format_size(result.right_file.size)
            time_str = datetime.fromtimestamp(result.right_file.mtime).strftime("%m/%d %H:%M")
            right_info = f"{size_str} {time_str}"
        
        # Get status description
        status_descriptions = {
            "ONLY_RIGHT": "<<<",
            "ONLY_LEFT": ">>>", 
            "DIFFERENT_SIZE": "SIZE",
            "DIFFERENT_TIME": "TIME",
            "DIFFERENT_CONTENT": "DIFF",
            "IDENTICAL": "SAME"
        }
        status_text = status_descriptions.get(result.status, "????")
        
        # Add merge indicator
        if result.can_merge:
            status_text += "[M]"
        
        # Use the same column widths as headers
        # Create the complete line with filename and status info
        filename = result.relative_path
        
        # Show selection indicator by adjusting filename formatting for first line
        if i == 0:
            # For selected line, add >> indicator and adjust space accordingly
            if len(filename) > left_width - 21:  # Reserve space for >> + size/time info
                filename = "..." + filename[-(left_width - 24):]
            left_part = f">> {filename:<{left_width-21}}{left_info:>17}"
        else:
            # For non-selected lines, normal formatting
            if len(filename) > left_width - 18:  # Reserve space for size/time info
                filename = "..." + filename[-(left_width - 21):]
            left_part = f"{filename:<{left_width-18}}{left_info:>17}"
        
        # Ensure exact column widths - pad or truncate as needed
        left_part = f"{left_part:<{left_width}}"[:left_width]
        status_part = f"{status_text:^{status_width}}"
        right_part = f"{right_info:<{right_width}}"[:right_width]
        
        # Construct the complete line with borders
        line = f"│{left_part}│{status_part}│{right_part}│"
        
        print(line[:width])
    
    # Bottom border
    try:
        bottom_line = "└" + "─" * left_width + "┴" + "─" * status_width + "┴" + "─" * right_width + "┘"
        print(bottom_line)
    except:
        print("-" * width)
    
    print(f"Files: {len(comparer.results)} | Selected: 1/{len(comparer.results)}")
    print("↑↓:Select F3/<:Copy→Left F4/>:Copy→Right E:Edit M:Merge R:Refresh H:Help Q:Quit")
    print("=" * width)

if __name__ == "__main__":
    demo_interface()
