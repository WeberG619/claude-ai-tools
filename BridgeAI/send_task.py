#!/usr/bin/env python3
"""
Send tasks to the Dell PC automation service
"""

import json
import uuid
import argparse
from pathlib import Path
from datetime import datetime

DELL_PC_QUEUE = Path(r'\\192.168.1.31\BridgeAI\TaskQueue')
DELL_PC_RESULTS = Path(r'\\192.168.1.31\BridgeAI\Results')

def send_task(task_type, **kwargs):
    """Send a task to the Dell PC"""
    task_id = str(uuid.uuid4())[:8]

    task = {
        'id': task_id,
        'type': task_type,
        'submitted': datetime.now().isoformat(),
        **kwargs
    }

    task_file = DELL_PC_QUEUE / f'{task_id}.json'
    with open(task_file, 'w') as f:
        json.dump(task, f, indent=2)

    print(f'Task submitted: {task_id}')
    print(f'Type: {task_type}')
    print(f'Check results at: {DELL_PC_RESULTS / f"{task_id}_result.json"}')

    return task_id

def check_result(task_id):
    """Check if a task has completed"""
    result_file = DELL_PC_RESULTS / f'{task_id}_result.json'
    if result_file.exists():
        with open(result_file) as f:
            return json.load(f)
    return None

# Quick task functions
def run_command(cmd):
    """Run a shell command on Dell PC"""
    return send_task('shell', command=cmd)

def run_python(code):
    """Run Python code on Dell PC"""
    return send_task('python', code=code)

def backup_folder(source):
    """Backup a folder on Dell PC"""
    return send_task('backup', source=source)

def ask_ai(prompt, model='llama3.2:1b'):
    """Ask the local AI on Dell PC"""
    return send_task('ollama', prompt=prompt, model=model)

def cleanup_old_files(target, days=30):
    """Clean files older than X days"""
    return send_task('cleanup', target=target, older_than_days=days)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Send tasks to Dell PC')
    parser.add_argument('type', choices=['shell', 'python', 'backup', 'ai', 'cleanup'])
    parser.add_argument('--command', '-c', help='Shell command to run')
    parser.add_argument('--code', help='Python code to run')
    parser.add_argument('--source', '-s', help='Source path for backup')
    parser.add_argument('--prompt', '-p', help='AI prompt')
    parser.add_argument('--target', '-t', help='Target for cleanup')
    parser.add_argument('--days', '-d', type=int, default=30, help='Days for cleanup')

    args = parser.parse_args()

    if args.type == 'shell':
        run_command(args.command)
    elif args.type == 'python':
        run_python(args.code)
    elif args.type == 'backup':
        backup_folder(args.source)
    elif args.type == 'ai':
        ask_ai(args.prompt)
    elif args.type == 'cleanup':
        cleanup_old_files(args.target, args.days)
