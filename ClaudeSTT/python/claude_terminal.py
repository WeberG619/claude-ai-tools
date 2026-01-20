#!/usr/bin/env python
"""
Claude Terminal - Voice-enabled terminal commands
"""
import os
import sys
import subprocess
import time
from terminal_stt import TerminalSTT

class ClaudeTerminal:
    def __init__(self):
        self.stt = TerminalSTT(wake_word="claude", timeout=20)
        self.commands = {
            "list files": self.list_files,
            "show directory": self.list_files,
            "what directory": self.show_pwd,
            "where am i": self.show_pwd,
            "current directory": self.show_pwd,
            "change directory": self.change_directory,
            "go to": self.change_directory,
            "make directory": self.make_directory,
            "create folder": self.make_directory,
            "show file": self.show_file,
            "read file": self.show_file,
            "run python": self.run_python,
            "git status": self.git_status,
            "git log": self.git_log,
            "help": self.show_help,
            "commands": self.show_help,
        }
        
    def list_files(self, command):
        """List files in current directory"""
        print("\nFiles in current directory:")
        subprocess.run(["ls", "-la"] if os.name != 'nt' else ["dir"])
        
    def show_pwd(self, command):
        """Show current directory"""
        print(f"\nCurrent directory: {os.getcwd()}")
        
    def change_directory(self, command):
        """Change directory based on voice command"""
        # Extract directory name from command
        words = command.lower().split()
        if "parent" in words or "up" in words:
            os.chdir("..")
            print(f"Changed to: {os.getcwd()}")
        elif "home" in words:
            os.chdir(os.path.expanduser("~"))
            print(f"Changed to: {os.getcwd()}")
        else:
            # Try to find a directory name in the command
            for word in words:
                if os.path.isdir(word):
                    os.chdir(word)
                    print(f"Changed to: {os.getcwd()}")
                    return
            print("Directory not found in command")
            
    def make_directory(self, command):
        """Create a new directory"""
        words = command.split()
        # Find the last word that could be a directory name
        for word in reversed(words):
            if word.replace("_", "").replace("-", "").isalnum():
                os.makedirs(word, exist_ok=True)
                print(f"Created directory: {word}")
                return
        print("Could not determine directory name")
        
    def show_file(self, command):
        """Show contents of a file"""
        words = command.split()
        for word in words:
            if os.path.isfile(word):
                print(f"\nContents of {word}:")
                with open(word, 'r') as f:
                    print(f.read())
                return
        print("File not found in command")
        
    def run_python(self, command):
        """Run a Python script"""
        words = command.split()
        for word in words:
            if word.endswith('.py') and os.path.isfile(word):
                print(f"\nRunning {word}...")
                subprocess.run([sys.executable, word])
                return
        print("Python file not found in command")
        
    def git_status(self, command):
        """Show git status"""
        subprocess.run(["git", "status"])
        
    def git_log(self, command):
        """Show git log"""
        subprocess.run(["git", "log", "--oneline", "-10"])
        
    def show_help(self, command):
        """Show available commands"""
        print("\nAvailable voice commands:")
        print("- 'list files' or 'show directory' - List files")
        print("- 'current directory' or 'where am i' - Show current path")
        print("- 'change directory [name]' or 'go to [name]' - Change directory")
        print("- 'make directory [name]' - Create new directory")
        print("- 'show file [name]' - Display file contents")
        print("- 'run python [script.py]' - Run Python script")
        print("- 'git status' - Show git status")
        print("- 'git log' - Show recent commits")
        print("- 'exit' or 'quit' - Exit Claude Terminal")
        
    def process_command(self, command):
        """Process a voice command"""
        if not command:
            return True
            
        command_lower = command.lower()
        
        # Check for exit
        if "exit" in command_lower or "quit" in command_lower:
            return False
            
        # Find matching command
        for key, func in self.commands.items():
            if key in command_lower:
                func(command)
                return True
                
        # If no command matched, try to run it as a shell command
        print(f"\nRunning: {command}")
        try:
            subprocess.run(command.split())
        except Exception as e:
            print(f"Error: {e}")
            
        return True
        
    def run(self):
        """Main loop"""
        print("Claude Terminal - Voice-Enabled Command Line")
        print("============================================")
        print(f"Say 'Claude' followed by your command")
        print("Say 'Claude help' for available commands")
        print("Say 'Claude exit' to quit\n")
        
        while True:
            try:
                # Get voice command
                command = self.stt.get_command("🎤 Ready for command (say 'Claude' first):")
                
                if command:
                    print(f"📝 Heard: {command}")
                    if not self.process_command(command):
                        break
                else:
                    print("⏱️ Timeout - no command received")
                    
            except KeyboardInterrupt:
                print("\n\nExiting...")
                break
            except Exception as e:
                print(f"Error: {e}")
                
        print("Goodbye!")

if __name__ == "__main__":
    terminal = ClaudeTerminal()
    terminal.run()