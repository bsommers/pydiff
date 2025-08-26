# Directory Comparison Tool

A curses-based Python application for comparing two directories and copying files between them.

## Features

- **Visual comparison**: Side-by-side comparison of two directories with color-coded status
- **File operations**: Copy files from left to right or right to left
- **Smart detection**: Identifies files that are identical, different, or missing
- **Keyboard navigation**: Full keyboard control with intuitive shortcuts
- **Nested directories**: Supports recursive directory scanning
- **Real-time updates**: Refreshes comparison after file operations

## Installation

No installation required. Just make sure you have Python 3.6+ installed.

```bash
chmod +x dircomp.py
```

## Usage

```bash
./dircomp.py left_directory right_directory
```

### Example

```bash
./dircomp.py ~/Documents/project_v1 ~/Documents/project_v2
```

## Controls

### Navigation
- **↑/↓**: Move selection up/down
- **Page Up/Page Down**: Navigate by page
- **Home/End**: Go to first/last file

### File Operations
- **F3** or **<**: Copy selected file from right to left
- **F4** or **>**: Copy selected file from left to right

### Other Commands
- **r**: Refresh directory comparison
- **h** or **?**: Show help dialog
- **q** or **ESC**: Quit application

## File Status Symbols

| Symbol | Meaning |
|--------|---------|
| `>>>` | File only exists on left |
| `<<<` | File only exists on right |
| `!=` | Files have different sizes |
| `~=` | Files have different modification times |
| `<>` | Files have different content |
| `==` | Files are identical |

## Color Coding

- **Red**: Files only on left
- **Green**: Files only on right  
- **Magenta**: Files with differences
- **Cyan**: Identical files
- **Yellow**: Currently selected file (highlighted)

## File Comparison Logic

The tool compares files using multiple criteria:

1. **Existence**: Checks if file exists in both directories
2. **Size**: Compares file sizes
3. **Modification time**: Compares last modified timestamps (1 second tolerance)
4. **Content hash**: Compares MD5 hash of file contents (lazy loaded)

## Examples

### Basic Usage
Compare two project directories:
```bash
./dircomp.py ~/projects/myapp_old ~/projects/myapp_new
```

### Verbose Mode
Get detailed information during scanning:
```bash
./dircomp.py -v ~/backup ~/current
```

## Requirements

- Python 3.6 or higher
- Standard library modules only (no external dependencies)
- Terminal with curses support

## Limitations

- Only compares regular files (not symbolic links, device files, etc.)
- MD5 hash calculation is done on-demand, which may be slow for large files
- No preview of file content differences
- Cannot handle binary files specially

## Troubleshooting

### "Terminal too small" error
Resize your terminal window to at least 80x24 characters.

### Permission errors when copying
Ensure you have write permissions to the destination directory.

### Files not showing up
Make sure the directories exist and contain regular files (not just directories).

## License

This tool is provided as-is for educational and utility purposes.
