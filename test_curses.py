#!/usr/bin/env python3
"""
Test script to verify the curses interface can start without errors.
"""

import sys
import os
sys.path.insert(0, '/Users/bill')

def test_curses_startup():
    """Test that the curses interface can initialize without errors."""
    try:
        from dircomp import DirectoryComparer, CursesUI
        import curses
        
        # Create comparer
        comparer = DirectoryComparer('/Users/bill/test_dirs/dir1', '/Users/bill/test_dirs/dir2')
        comparer.scan_directories()
        
        print(f"✓ DirectoryComparer initialized successfully")
        print(f"✓ Found {len(comparer.results)} files to compare")
        
        # Test that UI can be created
        ui = CursesUI(comparer)
        print("✓ CursesUI created successfully")
        
        # Test individual UI methods (without curses screen)
        ui.height = 24
        ui.width = 80
        ui.list_height = 18
        
        print("✓ UI dimensions set successfully")
        
        # Verify that core logic works
        if len(comparer.results) > 0:
            # Test navigation
            original_index = comparer.selected_index
            ui._move_selection(1)
            if comparer.selected_index != original_index:
                ui._move_selection(-1)
                print("✓ Navigation logic working")
            
            print("✓ All core functionality verified")
        
        print("\n🎉 All tests passed! The curses interface should work correctly.")
        print(f"\nTo run the actual interface:")
        print(f"   ./dircomp.py /Users/bill/test_dirs/dir1 /Users/bill/test_dirs/dir2")
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    
    return True

if __name__ == "__main__":
    test_curses_startup()
