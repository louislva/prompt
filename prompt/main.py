from prompt_toolkit import PromptSession
from prompt_toolkit.completion import Completer, Completion
from pathlib import Path
import os
import pyperclip
import re

file_ref_re = re.compile(r'(?<!\\)@\S+')

def get_file_paths():
    file_paths = []
    for root, dirs, files in os.walk('.'):
        for name in files:
            # Store paths without the './' prefix
            full_path = os.path.join(root, name)[2:]
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
    file_paths = get_file_paths()
    files_referenced = []
    for file_ref in file_refs:
        file_path = file_ref[1:].lower()
        if file_path in file_paths:
            files_referenced.append(file_path)

    prompt = ""

    if files_referenced:
        for file_path in files_referenced:
            file_content = open(file_path, "r").read().strip()
            prompt += f"```{file_path}\n{file_content}\n```\n\n"
        prompt += "---\n\n"
    
    prompt += text

    return prompt

def to_clipboard(text):
    pyperclip.copy(text)

def main():
    # Print welcome message in blue and bold
    print("\033[1;34mWelcome to Prompt!\033[0m")
    
    # Create completer
    file_path_completer = FilePathCompleter()
    
    # Create session
    session = PromptSession(completer=file_path_completer)
    
    while True:
        try:
            # This will show suggestions as you type
            text = session.prompt("> ")
            to_clipboard(to_prompt(text))
            break
        except KeyboardInterrupt:
            break
        except EOFError:
            break

# Change this part
def cli():
    """Entry point for the command line script"""
    main()

if __name__ == "__main__":
    cli()