#!/usr/bin/env python3
"""
Fixed Notes updater using the working Test 9 approach.
"""

import subprocess
import sys

def update_notes_simple(content):
    """
    Update Apple Notes using the working Test 9 approach.
    """
    
    # Convert \n to actual newlines
    content = content.replace('\\n', '\n')
    lines = content.split('\n')
    
    # Build AppleScript to create content incrementally
    note_name = "📈 Business Broker Monitoring"
    folder_name = "Building"
    
    # Escape quotes in lines
    escaped_lines = [line.replace('"', '\\"') for line in lines]
    
    script = f'''
    tell application "Notes"
        activate
        set noteName to "{note_name}"
        set folderName to "{folder_name}"
        
        -- Find or create folder
        try
            set targetFolder to folder folderName
        on error
            set targetFolder to make new folder with properties {{name:folderName}}
        end try
        
        -- Find or create note
        try
            set existingNote to note noteName in targetFolder
            set currentBody to body of existingNote
            
            -- Build new content incrementally (Test 9 approach)
            tell existingNote
                set body to "{escaped_lines[0] if escaped_lines else ""}"'''
    
    # Add remaining lines incrementally
    for line in escaped_lines[1:]:
        script += f'''
                set body to body & return & "{line}"'''
    
    script += f'''
                set body to body & return & return & currentBody
            end tell
            return "Appended to existing note"
        on error
            -- Create new note using Test 9 approach
            set newNote to make new note in targetFolder with properties {{name:noteName}}
            tell newNote
                set body to "{escaped_lines[0] if escaped_lines else ""}"'''
    
    # Add remaining lines for new note
    for line in escaped_lines[1:]:
        script += f'''
                set body to body & return & "{line}"'''
    
    script += '''
            end tell
            return "Created new note"
        end try
    end tell
    '''
    
    try:
        result = subprocess.run(['osascript', '-e', script], capture_output=True, text=True, check=True)
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        raise Exception(f"AppleScript failed: {e.stderr}")

def main():
    if len(sys.argv) != 2:
        print("Usage: python3 update_notes.py '<content>'")
        sys.exit(1)
    
    content = sys.argv[1]
    
    try:
        result = update_notes_simple(content)
        print(f"Success: {result}")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 