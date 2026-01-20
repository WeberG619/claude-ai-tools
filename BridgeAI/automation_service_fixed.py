#!/usr/bin/env python3
"""
BridgeAI Automation Service - Fixed Version
Watches folders and processes tasks automatically
"""

import os
import sys
import time
import json
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

# Paths
BASE_DIR = Path('C:/BridgeAI')
QUEUE_DIR = BASE_DIR / 'TaskQueue'
RESULTS_DIR = BASE_DIR / 'Results'
LOGS_DIR = BASE_DIR / 'Logs'
SHARED_DIR = BASE_DIR / 'SharedFiles'

# Create directories
for d in [QUEUE_DIR, RESULTS_DIR, LOGS_DIR, SHARED_DIR]:
    d.mkdir(parents=True, exist_ok=True)

def log(msg):
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log_line = f'[{timestamp}] {msg}'
    print(log_line)
    try:
        with open(LOGS_DIR / 'automation.log', 'a', encoding='utf-8') as f:
            f.write(log_line + '\n')
    except:
        pass

def process_task(task_file):
    """Process a task from the queue"""
    task_id = task_file.stem

    try:
        # Read file with explicit encoding
        content = task_file.read_text(encoding='utf-8-sig')  # Handle BOM

        if not content.strip():
            log(f'Empty task file: {task_file.name}, removing')
            task_file.unlink()
            return {'status': 'error', 'error': 'Empty file'}

        # Parse JSON
        try:
            task = json.loads(content)
        except json.JSONDecodeError as e:
            log(f'Invalid JSON in {task_file.name}: {e}')
            # Move bad file instead of deleting
            bad_dir = QUEUE_DIR / 'bad'
            bad_dir.mkdir(exist_ok=True)
            shutil.move(str(task_file), str(bad_dir / task_file.name))
            return {'status': 'error', 'error': f'Invalid JSON: {e}'}

        task_type = task.get('type', 'unknown')
        task_id = task.get('id', task_id)

        log(f'Processing task: {task_id} (type: {task_type})')

        result = {'id': task_id, 'status': 'completed', 'started': datetime.now().isoformat()}

        if task_type == 'shell':
            # Run a shell command
            cmd = task.get('command', '')
            if cmd:
                try:
                    proc = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=300)
                    result['stdout'] = proc.stdout
                    result['stderr'] = proc.stderr
                    result['returncode'] = proc.returncode
                except subprocess.TimeoutExpired:
                    result['status'] = 'error'
                    result['error'] = 'Command timed out'
            else:
                result['status'] = 'error'
                result['error'] = 'No command specified'

        elif task_type == 'python':
            # Run Python code
            code = task.get('code', '')
            if code:
                exec_result = {}
                try:
                    exec(code, {'result': exec_result})
                    result['output'] = exec_result
                except Exception as e:
                    result['status'] = 'error'
                    result['error'] = f'Python error: {e}'
            else:
                result['status'] = 'error'
                result['error'] = 'No code specified'

        elif task_type == 'copy':
            # Copy files
            src = task.get('source', '')
            dst = task.get('destination', '')
            if src and dst:
                if os.path.isdir(src):
                    shutil.copytree(src, dst, dirs_exist_ok=True)
                else:
                    shutil.copy2(src, dst)
                result['copied'] = src
            else:
                result['status'] = 'error'
                result['error'] = 'Missing source or destination'

        elif task_type == 'backup':
            # Backup a folder
            src = task.get('source', '')
            if src:
                backup_name = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                dst = BASE_DIR / 'Backups' / backup_name
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copytree(src, dst)
                result['backup_location'] = str(dst)
            else:
                result['status'] = 'error'
                result['error'] = 'No source specified'

        elif task_type == 'cleanup':
            # Clean old files
            target = Path(task.get('target', ''))
            days = task.get('older_than_days', 30)
            if target.exists():
                cutoff = time.time() - (days * 86400)
                cleaned = 0
                for f in target.rglob('*'):
                    try:
                        if f.is_file() and f.stat().st_mtime < cutoff:
                            f.unlink()
                            cleaned += 1
                    except:
                        pass
                result['files_cleaned'] = cleaned
            else:
                result['status'] = 'error'
                result['error'] = f'Target not found: {target}'

        elif task_type == 'ollama':
            # Run Ollama AI query
            prompt = task.get('prompt', '')
            model = task.get('model', 'llama3.2:1b')
            if prompt:
                try:
                    proc = subprocess.run(
                        ['ollama', 'run', model, prompt],
                        capture_output=True, text=True, timeout=120
                    )
                    result['response'] = proc.stdout
                    if proc.returncode != 0:
                        result['status'] = 'error'
                        result['error'] = proc.stderr or 'Ollama command failed'
                except subprocess.TimeoutExpired:
                    result['status'] = 'error'
                    result['error'] = 'Ollama timed out'
                except FileNotFoundError:
                    result['status'] = 'error'
                    result['error'] = 'Ollama not installed'
            else:
                result['status'] = 'error'
                result['error'] = 'No prompt specified'

        else:
            result['status'] = 'error'
            result['error'] = f'Unknown task type: {task_type}'

        result['completed'] = datetime.now().isoformat()

        # Save result
        result_file = RESULTS_DIR / f'{task_id}_result.json'
        with open(result_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2)

        # Remove task file only if successful
        try:
            task_file.unlink()
        except:
            pass

        log(f'Task {task_id} completed (status: {result.get("status", "unknown")})')
        return result

    except Exception as e:
        log(f'Error processing task {task_id}: {e}')
        # Save error result
        error_result = {
            'id': task_id,
            'status': 'error',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }
        try:
            result_file = RESULTS_DIR / f'{task_id}_result.json'
            with open(result_file, 'w', encoding='utf-8') as f:
                json.dump(error_result, f, indent=2)
            # Move problematic task file
            bad_dir = QUEUE_DIR / 'bad'
            bad_dir.mkdir(exist_ok=True)
            shutil.move(str(task_file), str(bad_dir / task_file.name))
        except:
            pass
        return error_result

def main():
    log('='*50)
    log('BridgeAI Automation Service Started (Fixed Version)')
    log(f'Watching: {QUEUE_DIR}')
    log(f'Results: {RESULTS_DIR}')
    log('='*50)

    while True:
        try:
            # Check for new tasks
            task_files = list(QUEUE_DIR.glob('*.json'))

            for task_file in task_files:
                # Skip files in subdirectories (like 'bad' folder)
                if task_file.parent != QUEUE_DIR:
                    continue

                # Small delay to ensure file is fully written
                time.sleep(0.1)

                process_task(task_file)

            # Sleep before next check
            time.sleep(2)

        except KeyboardInterrupt:
            log('Shutting down...')
            break
        except Exception as e:
            log(f'Error in main loop: {e}')
            time.sleep(5)

if __name__ == '__main__':
    main()
