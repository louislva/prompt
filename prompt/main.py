from prompt_toolkit import PromptSession
from prompt_toolkit.completion import Completer, Completion
from pathlib import Path
import os
import pyperclip
import re
import pathspec
import hashlib
from collections import deque
import json

DEFAULT_USER_SETTINGS = {
    "style_prompt": ""
}
user_settings_path = os.path.join(os.path.dirname(__file__), "user_settings.json")
user_settings = DEFAULT_USER_SETTINGS
try:
    user_settings = json.load(open(user_settings_path))
except FileNotFoundError:
    pass

file_ref_re = re.compile(r'(?<!\\)@\S+')

def get_file_paths():
    # Load gitignore patterns if .gitignore exists
    gitignore_patterns = []
    if os.path.exists('.gitignore'):
        with open('.gitignore', 'r') as f:
            spec = pathspec.PathSpec.from_lines('gitwildmatch', f.readlines())
    else:
        spec = pathspec.PathSpec([])

    file_paths = []
    for root, dirs, files in os.walk('.'):
        # Remove hidden directories from dirs list (modifies walk)
        dirs[:] = [d for d in dirs if not d.startswith('.')]
        
        for name in files:
            # Skip hidden files
            if name.startswith('.'): 
                continue
                
            # Get relative path without './' prefix
            full_path = os.path.join(root, name)[2:]
            
            # Skip if matches gitignore patterns
            if spec.match_file(full_path):
                continue
                
            # Get the last modified time for the file
            mod_time = os.path.getmtime(os.path.join(root, name))
            file_paths.append((full_path, mod_time))
    
    # Sort by modification time (newest first) and extract just the paths
    file_paths.sort(key=lambda x: x[1], reverse=True)
    return [path for path, _ in file_paths]

class FilePathCompleter(Completer):
    def __init__(self):
        self.file_paths = get_file_paths()        

    def get_completions(self, document, complete_event):
        # Get the text before cursor
        text = document.text_before_cursor
        
        # Find the last file reference by iterating through all matches
        matches = list(file_ref_re.finditer(text))
        last_file_ref = matches[-1] if matches else None
        if not last_file_ref: return
        end_index = last_file_ref.start() + len(last_file_ref.group(0))
        if end_index != len(text): return
        
        search_text = last_file_ref.group(0)[1:].lower()

        # Search through our cached paths
        for path in self.file_paths:
            if search_text in path.lower():
                yield Completion(
                    path,
                    start_position=-len(search_text),
                    display=path
                )

def to_prompt(text):
    # Regular expression to match unescaped @ followed by non-whitespace characters
    file_refs = file_ref_re.findall(text)
    file_paths_lower = [path.lower() for path in get_file_paths()]
    files_referenced = []
    for file_ref in file_refs:
        file_ref_key = file_ref[1:].lower()
        # Find it; either by exact match or, second priority, by partial match
        file_path = next(
            (path for path in file_paths_lower if file_ref_key == path),
            next(
                (path for path in file_paths_lower if path.endswith(file_ref_key)),
                next(
                    (path for path in file_paths_lower if file_ref_key in path),
                    None
                )
            )
        )

        if file_path in file_paths_lower:
            files_referenced.append(file_path)
            text = text.replace(file_ref, f"@{file_path}")
    
    files_referenced = list(set(files_referenced))

    prompt = ""

    if files_referenced:
        for file_path in files_referenced:
            file_content = open(file_path, "r").read().strip()
            prompt += f"```{file_path}\n{file_content}\n```\n\n"
        prompt += "---\n\n"
    
    prompt += text

    if user_settings.get("style_prompt", ""):
        prompt += "\n\n---\n\n" + user_settings["style_prompt"]

    return prompt

def to_clipboard(text):
    pyperclip.copy(text)

class PromptHistory:
    def __init__(self, max_history=50):
        self.max_history = max_history
        self.history_dir = Path(__file__).parent / "prompt_history"
        self.current_history = deque(maxlen=max_history)
        self.load_history()

    def get_strings(self):
        return list(self.current_history)

    def append_string(self, string):
        pass # we need this bc PromptSession expects an append method

    def get_cwd_hash(self):
        # Create a hash of the current working directory
        return hashlib.md5(os.getcwd().encode()).hexdigest()

    def get_history_file(self):
        return self.history_dir / f"{self.get_cwd_hash()}.json"

    def load_history(self):
        history_file = self.get_history_file()
        if history_file.exists():
            try:
                with open(history_file, 'r') as f:
                    history_list = json.load(f)
                    self.current_history = deque(history_list, maxlen=self.max_history)
            except json.JSONDecodeError:
                self.current_history = deque(maxlen=self.max_history)

    async def load(self):
        """Make this method async and yield history items"""
        self.load_history()
        for item in reversed(self.current_history):
            yield item
    
    def add_prompt(self, prompt):
        self.current_history.append(prompt)
        self.save_history()

    def save_history(self):
        history_file = self.get_history_file()
        os.makedirs(history_file.parent, exist_ok=True)
        with open(history_file, 'w') as f:
            json.dump(list(self.current_history), f)

def main():
    # Print welcome message in blue and bold
    print("\033[1;34mWelcome to Prompt!\033[0m")
    
    # Create completer and history
    file_path_completer = FilePathCompleter()
    prompt_history = PromptHistory()
    
    # Create session with history
    session = PromptSession(
        completer=file_path_completer,
        history=prompt_history
    )
    
    while True:
        try:
            # This will show suggestions as you type
            text = session.prompt("> ")
            processed_prompt = to_prompt(text)
            to_clipboard(processed_prompt)
            print("\033[32mCopied to clipboard!\033[0m")  # Print in green color
            prompt_history.add_prompt(text)
            break
        except KeyboardInterrupt:
            break
        except EOFError:
            break

def update_settings():
    """Handle settings modification mode"""
    print("\033[1;34mSettings Mode\033[0m")
    
    # Load current settings
    current_style = user_settings.get("style_prompt", "")
    
    # Create session for settings input
    session = PromptSession()
    
    try:
        new_style = session.prompt("Edit style prompt: ", multiline=False, default=current_style)
        # Update settings
        user_settings["style_prompt"] = new_style
        
        # Save to file
        with open(user_settings_path, 'w') as f:
            json.dump(user_settings, f)
            
        print("\033[32mSettings updated successfully!\033[0m")
    except (KeyboardInterrupt, EOFError):
        print("\nSettings update cancelled.")

def cli():
    """Entry point for the command line script"""
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--settings":
        update_settings()
    if len(sys.argv) > 1 and sys.argv[1] == "--reset-settings":
        user_settings = DEFAULT_USER_SETTINGS
        with open(user_settings_path, 'w') as f:
            json.dump(user_settings, f)
        print("\033[32mSettings reset successfully!\033[0m")
    else:
        main()

if __name__ == "__main__":
    cli()