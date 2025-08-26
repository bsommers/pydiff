#!/usr/bin/env python3
"""
Directory Comparison Tool with Curses Interface
A tool to compare two directories and copy files between them.
"""

import os
import sys
import curses
import hashlib
import shutil
import threading
import subprocess
import tempfile
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Optional, Set
import argparse


class FileInfo:
    """Information about a file for comparison."""
    
    def __init__(self, path: Path, relative_path: str):
        self.path = path
        self.relative_path = relative_path
        self.size = path.stat().st_size if path.exists() else 0
        self.mtime = path.stat().st_mtime if path.exists() else 0
        self.exists = path.exists()
        self._hash = None
    
    @property
    def hash(self) -> str:
        """Calculate MD5 hash of file content (lazy loading)."""
        if self._hash is None and self.exists:
            try:
                with open(self.path, 'rb') as f:
                    self._hash = hashlib.md5(f.read()).hexdigest()
            except (OSError, IOError):
                self._hash = ""
        return self._hash or ""


class ComparisonResult:
    """Result of comparing two files."""
    
    def __init__(self, left_file: Optional[FileInfo], right_file: Optional[FileInfo]):
        self.left_file = left_file
        self.right_file = right_file
        self.relative_path = (left_file or right_file).relative_path
        
    @property
    def status(self) -> str:
        """Get comparison status."""
        if not self.left_file or not self.left_file.exists:
            return "ONLY_RIGHT"
        elif not self.right_file or not self.right_file.exists:
            return "ONLY_LEFT"
        elif self.left_file.size != self.right_file.size:
            return "DIFFERENT_SIZE"
        elif abs(self.left_file.mtime - self.right_file.mtime) > 1:  # 1 second tolerance
            return "DIFFERENT_TIME"
        elif self.left_file.hash != self.right_file.hash:
            return "DIFFERENT_CONTENT"
        else:
            return "IDENTICAL"
    
    @property
    def symbol(self) -> str:
        """Get symbol for status display."""
        symbols = {
            "ONLY_RIGHT": "<<<",
            "ONLY_LEFT": ">>>",
            "DIFFERENT_SIZE": "!=",
            "DIFFERENT_TIME": "~=",
            "DIFFERENT_CONTENT": "<>",
            "IDENTICAL": "=="
        }
        return symbols.get(self.status, "??")
    
    @property
    def can_merge(self) -> bool:
        """Check if files can be merged (both exist and are text files)."""
        if not (self.left_file and self.left_file.exists and 
                self.right_file and self.right_file.exists):
            return False
        
        if self.status == "IDENTICAL":
            return False
            
        # Check if files are likely text files
        try:
            with open(self.left_file.path, 'rb') as f:
                left_sample = f.read(512)
            with open(self.right_file.path, 'rb') as f:
                right_sample = f.read(512)
            
            # Simple heuristic: if most bytes are printable, consider it text
            def is_text(data):
                if not data:
                    return True
                text_chars = sum(1 for b in data if b in range(32, 127) or b in [9, 10, 13])
                return text_chars / len(data) > 0.7
            
            return is_text(left_sample) and is_text(right_sample)
        except (OSError, IOError):
            return False


class DirectoryComparer:
    """Main class for comparing directories."""
    
    def __init__(self, left_dir: str, right_dir: str):
        self.left_dir = Path(left_dir).resolve()
        self.right_dir = Path(right_dir).resolve()
        self.results: List[ComparisonResult] = []
        self.selected_index = 0
        
    def scan_directories(self) -> None:
        """Scan both directories and build comparison results."""
        left_files = self._scan_directory(self.left_dir)
        right_files = self._scan_directory(self.right_dir)
        
        all_relative_paths = set(left_files.keys()) | set(right_files.keys())
        
        self.results = []
        for rel_path in sorted(all_relative_paths):
            left_file = left_files.get(rel_path)
            right_file = right_files.get(rel_path)
            result = ComparisonResult(left_file, right_file)
            self.results.append(result)
    
    def _scan_directory(self, directory: Path) -> Dict[str, FileInfo]:
        """Scan a directory and return a dict of relative_path -> FileInfo."""
        files = {}
        if not directory.exists():
            return files
            
        for file_path in directory.rglob('*'):
            if file_path.is_file():
                try:
                    relative_path = str(file_path.relative_to(directory))
                    files[relative_path] = FileInfo(file_path, relative_path)
                except (OSError, ValueError):
                    continue
        return files
    
    def copy_file_left_to_right(self, index: int) -> bool:
        """Copy file from left directory to right directory."""
        if not (0 <= index < len(self.results)):
            return False
            
        result = self.results[index]
        if not result.left_file or not result.left_file.exists:
            return False
            
        try:
            dest_path = self.right_dir / result.relative_path
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(result.left_file.path, dest_path)
            
            # Update the result
            result.right_file = FileInfo(dest_path, result.relative_path)
            return True
        except (OSError, IOError):
            return False
    
    def copy_file_right_to_left(self, index: int) -> bool:
        """Copy file from right directory to left directory."""
        if not (0 <= index < len(self.results)):
            return False
            
        result = self.results[index]
        if not result.right_file or not result.right_file.exists:
            return False
            
        try:
            dest_path = self.left_dir / result.relative_path
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(result.right_file.path, dest_path)
            
            # Update the result
            result.left_file = FileInfo(dest_path, result.relative_path)
            return True
        except (OSError, IOError):
            return False
    
    def edit_file(self, index: int, side: str = "both") -> bool:
        """Edit file(s) using external editor."""
        if not (0 <= index < len(self.results)):
            return False
            
        result = self.results[index]
        files_to_edit = []
        
        if side in ["left", "both"] and result.left_file and result.left_file.exists:
            files_to_edit.append(str(result.left_file.path))
        
        if side in ["right", "both"] and result.right_file and result.right_file.exists:
            files_to_edit.append(str(result.right_file.path))
        
        if not files_to_edit:
            return False
        
        # Get editor from environment, default to vim
        editor = os.environ.get('EDITOR', 'vim')
        
        try:
            # Open editor
            if len(files_to_edit) == 1:
                subprocess.run([editor, files_to_edit[0]], check=True)
            else:
                # Open both files in split mode if editor supports it
                if 'vim' in editor or 'nvim' in editor:
                    subprocess.run([editor, '-O'] + files_to_edit, check=True)
                else:
                    # Open files sequentially
                    for file_path in files_to_edit:
                        subprocess.run([editor, file_path], check=True)
            
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False
    
    def merge_files(self, index: int) -> bool:
        """Merge two files using external merge tool."""
        if not (0 <= index < len(self.results)):
            return False
            
        result = self.results[index]
        if not result.can_merge:
            return False
        
        left_path = result.left_file.path
        right_path = result.right_file.path
        
        # Try different merge tools in order of preference
        merge_tools = [
            ('vimdiff', ['{editor}', '{left}', '{right}']),
            ('meld', ['meld', '{left}', '{right}']),
            ('diff3', ['diff3', '-m', '{left}', '{left}', '{right}']),
            ('merge', ['merge', '{left}', '{left}', '{right}']),
        ]
        
        for tool_name, cmd_template in merge_tools:
            if shutil.which(tool_name):
                try:
                    # Prepare command
                    editor = os.environ.get('EDITOR', 'vim')
                    cmd = []
                    for arg in cmd_template:
                        arg = arg.replace('{editor}', editor)
                        arg = arg.replace('{left}', str(left_path))
                        arg = arg.replace('{right}', str(right_path))
                        cmd.append(arg)
                    
                    subprocess.run(cmd, check=True)
                    return True
                except (subprocess.CalledProcessError, FileNotFoundError):
                    continue
        
        # If no merge tool available, fall back to editing both files
        return self.edit_file(index, "both")
    
    def create_merge_file(self, index: int) -> Optional[str]:
        """Create a unified merge file showing differences."""
        if not (0 <= index < len(self.results)):
            return None
            
        result = self.results[index]
        if not result.can_merge:
            return None
        
        try:
            # Create temporary file with merge content
            with tempfile.NamedTemporaryFile(mode='w', suffix='.merge', delete=False) as tmp:
                tmp.write(f"# Merge file for: {result.relative_path}\n")
                tmp.write(f"# Left file:  {result.left_file.path}\n")
                tmp.write(f"# Right file: {result.right_file.path}\n")
                tmp.write("#\n")
                tmp.write("# Choose the content you want to keep and save this file.\n")
                tmp.write("# Then use 'Apply Merge' to copy the merged content.\n")
                tmp.write("\n")
                
                # Add left file content
                tmp.write("=" * 60 + "\n")
                tmp.write(f"LEFT FILE ({result.left_file.path}):\n")
                tmp.write("=" * 60 + "\n")
                
                try:
                    with open(result.left_file.path, 'r', encoding='utf-8', errors='replace') as f:
                        tmp.write(f.read())
                except (OSError, IOError):
                    tmp.write("(Could not read file)\n")
                
                tmp.write("\n\n")
                
                # Add right file content
                tmp.write("=" * 60 + "\n")
                tmp.write(f"RIGHT FILE ({result.right_file.path}):\n")
                tmp.write("=" * 60 + "\n")
                
                try:
                    with open(result.right_file.path, 'r', encoding='utf-8', errors='replace') as f:
                        tmp.write(f.read())
                except (OSError, IOError):
                    tmp.write("(Could not read file)\n")
                
                return tmp.name
        except (OSError, IOError):
            return None


class CursesUI:
    """Curses-based user interface for the directory comparer."""
    
    def __init__(self, comparer: DirectoryComparer):
        self.comparer = comparer
        self.stdscr = None
        self.height = 0
        self.width = 0
        self.list_height = 0
        self.scroll_offset = 0
        self.status_message = ""
        self.copying = False
        
    def run(self, stdscr):
        """Main UI loop."""
        self.stdscr = stdscr
        curses.curs_set(0)  # Hide cursor
        curses.noecho()
        curses.cbreak()
        stdscr.keypad(True)
        
        # Initialize colors
        curses.start_color()
        curses.init_pair(1, curses.COLOR_WHITE, curses.COLOR_BLUE)    # Header
        curses.init_pair(2, curses.COLOR_YELLOW, curses.COLOR_BLACK)  # Selected
        curses.init_pair(3, curses.COLOR_RED, curses.COLOR_BLACK)     # Only left
        curses.init_pair(4, curses.COLOR_GREEN, curses.COLOR_BLACK)   # Only right
        curses.init_pair(5, curses.COLOR_MAGENTA, curses.COLOR_BLACK) # Different
        curses.init_pair(6, curses.COLOR_CYAN, curses.COLOR_BLACK)    # Identical
        curses.init_pair(7, curses.COLOR_WHITE, curses.COLOR_RED)     # Error
        
        while True:
            self._update_dimensions()
            self._draw_screen()
            
            key = stdscr.getch()
            if key == ord('q') or key == 27:  # ESC
                break
            elif key == curses.KEY_UP:
                self._move_selection(-1)
            elif key == curses.KEY_DOWN:
                self._move_selection(1)
            elif key == curses.KEY_PPAGE:  # Page Up
                self._move_selection(-self.list_height)
            elif key == curses.KEY_NPAGE:  # Page Down
                self._move_selection(self.list_height)
            elif key == curses.KEY_HOME:
                self._move_selection(-len(self.comparer.results))
            elif key == curses.KEY_END:
                self._move_selection(len(self.comparer.results))
            elif key == curses.KEY_F4 or key == ord('>'):  # Copy left to right
                self._copy_file_left_to_right()
            elif key == curses.KEY_F3 or key == ord('<'):  # Copy right to left
                self._copy_file_right_to_left()
            elif key == ord('e'):  # Edit both files
                self._edit_file("both")
            elif key == ord('E'):  # Edit left file
                self._edit_file("left")
            elif key == ord('w'):  # Edit right file  
                self._edit_file("right")
            elif key == ord('m'):  # Merge files
                self._merge_files()
            elif key == ord('M'):  # Manual merge
                self._manual_merge()
            elif key == ord('r'):  # Refresh
                self._refresh_directories()
            elif key == ord('h') or key == ord('?'):  # Help
                self._show_help()
    
    def _update_dimensions(self):
        """Update screen dimensions."""
        self.height, self.width = self.stdscr.getmaxyx()
        self.list_height = max(1, self.height - 6)  # Reserve space for header and status
    
    def _draw_screen(self):
        """Draw the main screen."""
        self.stdscr.clear()
        
        # Draw header
        header = f" Directory Comparison: {self.comparer.left_dir.name} <-> {self.comparer.right_dir.name} "
        self.stdscr.attron(curses.color_pair(1) | curses.A_BOLD)
        self.stdscr.addstr(0, 0, header.ljust(self.width)[:self.width])
        self.stdscr.attroff(curses.color_pair(1) | curses.A_BOLD)
        
        # Draw detailed column headers with clear sections
        # Calculate proper column widths - use fixed widths for consistency
        left_col_width = 25 if self.width >= 80 else self.width // 3 - 1
        status_col_width = 10
        right_col_width = self.width - left_col_width - status_col_width - 4  # -4 for the 4 border characters
        
        headers_line1 = "┌" + "─" * left_col_width + "┬" + "─" * status_col_width + "┬" + "─" * right_col_width + "┐"
        headers_line2 = f"│{'LEFT DIRECTORY':<{left_col_width}}│{'STATUS':<{status_col_width}}│{'RIGHT DIRECTORY':<{right_col_width}}│"
        headers_line3 = "├" + "─" * left_col_width + "┼" + "─" * status_col_width + "┼" + "─" * right_col_width + "┤"
        
        try:
            self.stdscr.addstr(1, 0, headers_line1[:self.width])
            self.stdscr.addstr(2, 0, headers_line2[:self.width]) 
            self.stdscr.addstr(3, 0, headers_line3[:self.width])
        except curses.error:
            # Fallback to simple headers if box drawing fails
            self.stdscr.addstr(1, 0, "-" * self.width)
            headers = f"{'LEFT':<{self.width//3}}{'STATUS':<10}{'RIGHT'}"
            self.stdscr.addstr(2, 0, headers[:self.width])
            self.stdscr.addstr(3, 0, "-" * self.width)
        
        # Draw file list
        self._draw_file_list()
        
        # Draw status and help
        self._draw_status()
        self._draw_help_line()
    
    def _draw_file_list(self):
        """Draw the file comparison list."""
        if not self.comparer.results:
            self.stdscr.addstr(5, 2, "No files found or directories don't exist")
            return
        
        # Calculate column widths (same as in _draw_screen)
        left_col_width = 25 if self.width >= 80 else self.width // 3 - 1
        status_col_width = 10
        right_col_width = self.width - left_col_width - status_col_width - 4  # -4 for the 4 border characters
        
        # Adjust scroll offset
        if self.comparer.selected_index < self.scroll_offset:
            self.scroll_offset = self.comparer.selected_index
        elif self.comparer.selected_index >= self.scroll_offset + self.list_height:
            self.scroll_offset = max(0, self.comparer.selected_index - self.list_height + 1)
        
        # Calculate visible items (each file takes 1 row now)
        visible_items = self.list_height
        
        for i in range(visible_items):
            result_index = self.scroll_offset + i
            if result_index >= len(self.comparer.results):
                break
                
            result = self.comparer.results[result_index]
            y_pos = 4 + i  # Start after headers
            
            if y_pos >= self.height - 2:
                break
            
            # Determine colors based on status
            color_pair = 0
            if result.status == "ONLY_LEFT":
                color_pair = 3
            elif result.status == "ONLY_RIGHT":
                color_pair = 4
            elif result.status in ["DIFFERENT_SIZE", "DIFFERENT_TIME", "DIFFERENT_CONTENT"]:
                color_pair = 5
            elif result.status == "IDENTICAL":
                color_pair = 6
            
            # Highlight selected item
            attr = curses.color_pair(color_pair)
            if result_index == self.comparer.selected_index:
                attr |= curses.A_REVERSE
            
            # Format file information for left side
            left_info = "─ MISSING ─"
            if result.left_file and result.left_file.exists:
                size_str = self._format_size(result.left_file.size)
                time_str = datetime.fromtimestamp(result.left_file.mtime).strftime("%m/%d %H:%M")
                left_info = f"{size_str} {time_str}"
            
            # Format file information for right side  
            right_info = "─ MISSING ─"
            if result.right_file and result.right_file.exists:
                size_str = self._format_size(result.right_file.size)
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
            left_width = left_col_width
            status_width = status_col_width 
            right_width = right_col_width
            
            # Create the complete line with filename and status info
            filename = result.relative_path
            if len(filename) > left_width - 18:  # Reserve space for size/time info
                filename = "..." + filename[-(left_width - 21):]
            
            left_part = f"{filename:<{left_width-18}}{left_info:>17}"
            # Ensure exact column width - pad or truncate as needed
            left_part = f"{left_part:<{left_width}}"[:left_width]
            status_part = f"{status_text:^{status_width}}"
            right_part = f"{right_info:<{right_width}}"[:right_width]
            
            # Construct the complete line with borders
            try:
                line = f"│{left_part}│{status_part}│{right_part}│"
            except:
                line = f"|{left_part}|{status_part}|{right_part}|"
            
            # Draw the line
            self.stdscr.attron(attr)
            try:
                self.stdscr.addstr(y_pos, 0, line[:self.width])
            except curses.error:
                # Handle edge cases where line is too long
                self.stdscr.addstr(y_pos, 0, line[:self.width-1])
            self.stdscr.attroff(attr)
        
        # Draw bottom border if we have files
        if self.comparer.results:
            bottom_y = 4 + min(visible_items, len(self.comparer.results) - self.scroll_offset)
            if bottom_y < self.height - 2:
                try:
                    bottom_line = "└" + "─" * left_col_width + "┴" + "─" * status_col_width + "┴" + "─" * right_col_width + "┘"
                    self.stdscr.addstr(bottom_y, 0, bottom_line[:self.width])
                except curses.error:
                    # Fallback to simple bottom line
                    self.stdscr.addstr(bottom_y, 0, "-" * self.width)
    
    def _draw_status(self):
        """Draw status bar."""
        status_y = self.height - 2
        if self.copying:
            status = "Processing..."
        elif self.status_message:
            status = self.status_message
        else:
            total = len(self.comparer.results)
            current = self.comparer.selected_index + 1 if total > 0 else 0
            status = f"Files: {total} | Selected: {current}/{total}"
        
        self.stdscr.addstr(status_y, 0, status[:self.width])
    
    def _draw_help_line(self):
        """Draw help line at bottom."""
        help_y = self.height - 1
        help_text = "↑↓:Select F3/<:Copy→Left F4/>:Copy→Right E:Edit M:Merge R:Refresh H:Help Q:Quit"
        self.stdscr.addstr(help_y, 0, help_text[:self.width])
    
    def _move_selection(self, delta: int):
        """Move selection by delta positions."""
        if not self.comparer.results:
            return
            
        new_index = self.comparer.selected_index + delta
        self.comparer.selected_index = max(0, min(len(self.comparer.results) - 1, new_index))
        self.status_message = ""
    
    def _copy_file_left_to_right(self):
        """Copy selected file from left to right."""
        if self.copying or not self.comparer.results:
            return
            
        def copy_thread():
            self.copying = True
            success = self.comparer.copy_file_left_to_right(self.comparer.selected_index)
            self.copying = False
            if success:
                self.status_message = "File copied left → right"
            else:
                self.status_message = "Failed to copy file"
        
        threading.Thread(target=copy_thread, daemon=True).start()
    
    def _copy_file_right_to_left(self):
        """Copy selected file from right to left."""
        if self.copying or not self.comparer.results:
            return
            
        def copy_thread():
            self.copying = True
            success = self.comparer.copy_file_right_to_left(self.comparer.selected_index)
            self.copying = False
            if success:
                self.status_message = "File copied right → left"
            else:
                self.status_message = "Failed to copy file"
        
        threading.Thread(target=copy_thread, daemon=True).start()
    
    def _edit_file(self, side: str):
        """Edit selected file(s)."""
        if self.copying or not self.comparer.results:
            return
        
        result = self.comparer.results[self.comparer.selected_index]
        
        # Check if files exist to edit
        files_exist = False
        if side in ["left", "both"] and result.left_file and result.left_file.exists:
            files_exist = True
        if side in ["right", "both"] and result.right_file and result.right_file.exists:
            files_exist = True
        
        if not files_exist:
            self.status_message = f"No {side} file(s) to edit"
            return
        
        # Set flag and status message
        self.copying = True
        self.status_message = f"Editing {side} file(s)..."
        
        try:
            # Suspend curses mode temporarily
            curses.endwin()
            
            success = self.comparer.edit_file(self.comparer.selected_index, side)
            if success:
                # Refresh the file info after editing
                self.comparer.scan_directories()
                if side == "both":
                    self.status_message = "Files edited successfully"
                else:
                    self.status_message = f"{side.title()} file edited successfully"
            else:
                self.status_message = "Editor failed or was cancelled"
        finally:
            # Resume curses mode
            curses.doupdate()
            self.copying = False
    
    def _merge_files(self):
        """Merge selected files using external tool."""
        if self.copying or not self.comparer.results:
            return
        
        result = self.comparer.results[self.comparer.selected_index]
        if not result.can_merge:
            self.status_message = "Files cannot be merged (missing or binary)"
            return
        
        # Set flag and status message
        self.copying = True
        self.status_message = "Starting merge tool..."
        
        try:
            # Suspend curses mode temporarily
            curses.endwin()
            
            success = self.comparer.merge_files(self.comparer.selected_index)
            if success:
                # Refresh the file info after merging
                self.comparer.scan_directories()
                self.status_message = "Files merged successfully"
            else:
                self.status_message = "Merge failed or was cancelled"
        finally:
            # Resume curses mode
            curses.doupdate()
            self.copying = False
    
    def _manual_merge(self):
        """Create a manual merge file and edit it."""
        if self.copying or not self.comparer.results:
            return
        
        result = self.comparer.results[self.comparer.selected_index]
        if not result.can_merge:
            self.status_message = "Files cannot be merged (missing or binary)"
            return
        
        # Set flag and status message
        self.copying = True
        self.status_message = "Creating manual merge file..."
        
        merge_file = self.comparer.create_merge_file(self.comparer.selected_index)
        if merge_file:
            # Edit the merge file
            editor = os.environ.get('EDITOR', 'vim')
            try:
                self.status_message = "Opening merge file in editor..."
                # Suspend curses mode temporarily
                curses.endwin()
                subprocess.run([editor, merge_file], check=True)
                self.status_message = f"Manual merge completed: {merge_file}"
            except (subprocess.CalledProcessError, FileNotFoundError):
                self.status_message = "Failed to open merge file in editor"
            finally:
                # Resume curses mode
                curses.doupdate()
        else:
            self.status_message = "Failed to create merge file"
        self.copying = False
    
    def _refresh_directories(self):
        """Refresh directory comparison."""
        self.status_message = "Refreshing..."
        self.comparer.scan_directories()
        self.comparer.selected_index = 0
        self.scroll_offset = 0
        self.status_message = "Refreshed"
    
    def _show_help(self):
        """Show help dialog."""
        help_text = [
            "Directory Comparison Tool - Help",
            "",
            "Navigation:",
            "  ↑/↓ or j/k    - Move selection up/down",
            "  PgUp/PgDn     - Page up/down",
            "  Home/End      - Go to first/last file",
            "",
            "File Operations:",
            "  F3 or <       - Copy selected file from right to left",
            "  F4 or >       - Copy selected file from left to right",
            "",
            "Editing & Merging:",
            "  e             - Edit both files (if they exist)",
            "  E             - Edit left file only",
            "  w             - Edit right file only",
            "  m             - Merge files using external tool",
            "  M             - Create manual merge file",
            "",
            "Other Commands:",
            "  r             - Refresh directory comparison",
            "  h or ?        - Show this help",
            "  q or ESC      - Quit application",
            "",
            "File Status Symbols:",
            "  >>>           - File only exists on left",
            "  <<<           - File only exists on right",
            "  !=            - Files have different sizes",
            "  ~=            - Files have different modification times",
            "  <>            - Files have different content",
            "  ==            - Files are identical",
            "",
            "Special Indicators:",
            "  [M]           - Files can be merged",
            "",
            "Notes:",
            "- Set EDITOR environment variable for preferred editor",
            "- Merge functionality requires text files",
            "- External merge tools: vimdiff, meld, diff3, merge",
            "",
            "Press any key to continue..."
        ]
        
        # Clear screen and show help
        self.stdscr.clear()
        for i, line in enumerate(help_text):
            if i < self.height - 1:
                self.stdscr.addstr(i, 2, line)
        
        self.stdscr.refresh()
        self.stdscr.getch()  # Wait for keypress
    
    @staticmethod
    def _format_size(size: int) -> str:
        """Format file size in human readable format."""
        for unit in ['B', 'K', 'M', 'G', 'T']:
            if size < 1024:
                return f"{size:3.0f}{unit}"
            size /= 1024
        return f"{size:.1f}P"


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Compare two directories with a curses interface")
    parser.add_argument("left_dir", help="Left directory to compare")
    parser.add_argument("right_dir", help="Right directory to compare")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    
    args = parser.parse_args()
    
    # Validate directories
    left_path = Path(args.left_dir)
    right_path = Path(args.right_dir)
    
    if not left_path.exists():
        print(f"Error: Left directory '{args.left_dir}' does not exist", file=sys.stderr)
        sys.exit(1)
    
    if not right_path.exists():
        print(f"Error: Right directory '{args.right_dir}' does not exist", file=sys.stderr)
        sys.exit(1)
    
    if not left_path.is_dir():
        print(f"Error: '{args.left_dir}' is not a directory", file=sys.stderr)
        sys.exit(1)
    
    if not right_path.is_dir():
        print(f"Error: '{args.right_dir}' is not a directory", file=sys.stderr)
        sys.exit(1)
    
    # Create comparer and scan directories
    print("Scanning directories...")
    comparer = DirectoryComparer(args.left_dir, args.right_dir)
    comparer.scan_directories()
    
    if args.verbose:
        print(f"Found {len(comparer.results)} files to compare")
    
    # Start curses interface
    try:
        ui = CursesUI(comparer)
        curses.wrapper(ui.run)
    except KeyboardInterrupt:
        print("\nInterrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
