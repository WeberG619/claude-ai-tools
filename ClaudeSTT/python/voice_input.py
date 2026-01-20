#!/usr/bin/env python
"""
Simple voice input function that can be imported and used anywhere
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from terminal_stt import TerminalSTT

_stt_instance = None

def voice_input(prompt="", wake_word="claude", timeout=30):
    """
    Get voice input from the user, similar to input() but with voice.
    
    Args:
        prompt: Optional prompt to display
        wake_word: Wake word to activate (default: "claude")
        timeout: Timeout in seconds (default: 30)
        
    Returns:
        The transcribed text or None if timeout
        
    Example:
        name = voice_input("Say your name: ")
        print(f"Hello, {name}!")
    """
    global _stt_instance
    
    # Create or reuse STT instance
    if _stt_instance is None or _stt_instance.wake_word != wake_word:
        _stt_instance = TerminalSTT(wake_word=wake_word, timeout=timeout)
    else:
        _stt_instance.timeout = timeout
        
    # Get voice command
    return _stt_instance.get_command(prompt)

def voice_confirm(question, wake_word="claude", timeout=30):
    """
    Get yes/no confirmation via voice.
    
    Returns:
        True if user says yes, False if no, None if unclear
    """
    response = voice_input(f"{question} (say yes or no): ", wake_word, timeout)
    
    if response:
        response_lower = response.lower()
        if "yes" in response_lower or "yeah" in response_lower or "sure" in response_lower:
            return True
        elif "no" in response_lower or "nope" in response_lower:
            return False
            
    return None

# Example usage
if __name__ == "__main__":
    print("Voice Input Demo")
    print("================\n")
    
    # Example 1: Simple input
    name = voice_input("What's your name? Say 'Claude' then your name: ")
    if name:
        print(f"Hello, {name}!")
    
    # Example 2: Confirmation
    if voice_confirm("Do you want to continue?"):
        print("Great! Let's continue...")
    else:
        print("Okay, stopping here.")
    
    # Example 3: Multiple inputs
    print("\nLet's collect some information:")
    color = voice_input("What's your favorite color? ")
    number = voice_input("Pick a number between 1 and 10: ")
    
    if color and number:
        print(f"\nYou like {color} and chose {number}!")