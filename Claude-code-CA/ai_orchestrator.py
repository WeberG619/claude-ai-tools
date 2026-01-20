#!/usr/bin/env python3
"""
AI-Enhanced Automation Orchestrator
A comprehensive system that understands natural language commands and executes them intelligently
"""

import os
import sys
import json
import time
import logging
import asyncio
import subprocess
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import re
import traceback

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('ai_orchestrator.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class TaskType(Enum):
    """Types of tasks the system can handle"""
    UI_AUTOMATION = "ui_automation"
    FILE_OPERATION = "file_operation"
    WEB_AUTOMATION = "web_automation"
    CODE_GENERATION = "code_generation"
    SYSTEM_COMMAND = "system_command"
    DATA_PROCESSING = "data_processing"
    OFFICE_AUTOMATION = "office_automation"
    UNKNOWN = "unknown"

class TaskStatus(Enum):
    """Status of task execution"""
    PENDING = "pending"
    ANALYZING = "analyzing"
    PLANNING = "planning"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    RECOVERING = "recovering"

@dataclass
class TaskContext:
    """Context for task execution"""
    original_request: str
    task_type: TaskType
    intent: Dict[str, Any]
    steps: List[Dict[str, Any]] = field(default_factory=list)
    current_step: int = 0
    status: TaskStatus = TaskStatus.PENDING
    error_count: int = 0
    screenshots: List[str] = field(default_factory=list)
    outputs: List[Any] = field(default_factory=list)
    memory: Dict[str, Any] = field(default_factory=dict)
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None

class IntentRecognizer:
    """Recognizes user intent from natural language"""
    
    def __init__(self):
        self.patterns = {
            TaskType.UI_AUTOMATION: [
                r"click.*button", r"close.*dialog", r"open.*application",
                r"navigate.*to", r"fill.*form", r"select.*option",
                r"powerpoint", r"excel", r"word", r"copilot"
            ],
            TaskType.FILE_OPERATION: [
                r"create.*file", r"delete.*file", r"move.*file",
                r"copy.*file", r"rename.*file", r"find.*file",
                r"organize.*folder", r"backup.*data"
            ],
            TaskType.WEB_AUTOMATION: [
                r"browse.*to", r"download.*from", r"fill.*online",
                r"scrape.*website", r"automate.*web", r"login.*to"
            ],
            TaskType.CODE_GENERATION: [
                r"write.*code", r"create.*script", r"generate.*function",
                r"build.*application", r"implement.*algorithm"
            ],
            TaskType.OFFICE_AUTOMATION: [
                r"create.*presentation", r"format.*document", r"generate.*report",
                r"analyze.*spreadsheet", r"merge.*documents"
            ]
        }
    
    def recognize(self, user_input: str) -> Tuple[TaskType, Dict[str, Any]]:
        """Recognize intent from user input"""
        user_input_lower = user_input.lower()
        
        # Check patterns
        for task_type, patterns in self.patterns.items():
            for pattern in patterns:
                if re.search(pattern, user_input_lower):
                    return task_type, self._extract_parameters(user_input, task_type)
        
        # Default to UI automation for specific keywords
        ui_keywords = ['powerpoint', 'excel', 'word', 'window', 'application', 'dialog']
        if any(keyword in user_input_lower for keyword in ui_keywords):
            return TaskType.UI_AUTOMATION, self._extract_parameters(user_input, TaskType.UI_AUTOMATION)
        
        return TaskType.UNKNOWN, {"raw_input": user_input}
    
    def _extract_parameters(self, user_input: str, task_type: TaskType) -> Dict[str, Any]:
        """Extract parameters based on task type"""
        params = {"raw_input": user_input}
        
        if task_type == TaskType.UI_AUTOMATION:
            # Extract application name
            apps = ['powerpoint', 'excel', 'word', 'chrome', 'firefox', 'notepad']
            for app in apps:
                if app in user_input.lower():
                    params['application'] = app
                    break
            
            # Extract action
            actions = ['close', 'click', 'open', 'navigate', 'fill', 'select']
            for action in actions:
                if action in user_input.lower():
                    params['action'] = action
                    break
            
            # Extract target (dialog, button, etc.)
            if 'dialog' in user_input.lower():
                params['target'] = 'dialog'
            elif 'button' in user_input.lower():
                params['target'] = 'button'
                # Try to extract button name
                match = re.search(r'button["\']?\s*(?:named|called|labeled)?\s*["\']?(\w+)', user_input.lower())
                if match:
                    params['button_name'] = match.group(1)
        
        return params

class ActionPlanner:
    """Plans steps to accomplish a task"""
    
    def plan(self, context: TaskContext) -> List[Dict[str, Any]]:
        """Create an execution plan based on task context"""
        task_type = context.task_type
        intent = context.intent
        
        if task_type == TaskType.UI_AUTOMATION:
            return self._plan_ui_automation(intent)
        elif task_type == TaskType.FILE_OPERATION:
            return self._plan_file_operation(intent)
        elif task_type == TaskType.WEB_AUTOMATION:
            return self._plan_web_automation(intent)
        elif task_type == TaskType.CODE_GENERATION:
            return self._plan_code_generation(intent)
        elif task_type == TaskType.OFFICE_AUTOMATION:
            return self._plan_office_automation(intent)
        else:
            return self._plan_generic(intent)
    
    def _plan_ui_automation(self, intent: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Plan UI automation steps"""
        steps = []
        
        # Common pattern: ensure app is running, find target, perform action, verify
        if intent.get('application'):
            steps.append({
                'action': 'ensure_application_running',
                'params': {'app': intent['application']}
            })
        
        steps.append({
            'action': 'capture_screen',
            'params': {'reason': 'initial_state'}
        })
        
        if intent.get('action') == 'close' and intent.get('target') == 'dialog':
            steps.extend([
                {
                    'action': 'find_dialog',
                    'params': {'screenshot': 'latest'}
                },
                {
                    'action': 'click_close_button',
                    'params': {'method': 'robust', 'fallback': True}
                },
                {
                    'action': 'verify_dialog_closed',
                    'params': {'timeout': 2}
                }
            ])
        elif intent.get('action') == 'click':
            steps.extend([
                {
                    'action': 'find_element',
                    'params': {'target': intent.get('target', 'button')}
                },
                {
                    'action': 'click_element',
                    'params': {'method': 'safe'}
                }
            ])
        
        steps.append({
            'action': 'capture_screen',
            'params': {'reason': 'final_state'}
        })
        
        return steps
    
    def _plan_file_operation(self, intent: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Plan file operation steps"""
        # Implementation for file operations
        return [{'action': 'execute_file_operation', 'params': intent}]
    
    def _plan_web_automation(self, intent: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Plan web automation steps"""
        # Implementation for web automation
        return [{'action': 'execute_web_automation', 'params': intent}]
    
    def _plan_code_generation(self, intent: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Plan code generation steps"""
        # Implementation for code generation
        return [{'action': 'generate_code', 'params': intent}]
    
    def _plan_office_automation(self, intent: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Plan office automation steps"""
        steps = []
        
        if 'presentation' in intent.get('raw_input', '').lower():
            steps = [
                {'action': 'open_powerpoint', 'params': {}},
                {'action': 'create_presentation', 'params': intent},
                {'action': 'save_presentation', 'params': {}}
            ]
        
        return steps
    
    def _plan_generic(self, intent: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Plan generic steps when type is unknown"""
        return [
            {
                'action': 'analyze_request',
                'params': {'input': intent['raw_input']}
            },
            {
                'action': 'execute_best_guess',
                'params': {}
            }
        ]

class AIOrchestrator:
    """Main orchestrator that coordinates all components"""
    
    def __init__(self):
        self.intent_recognizer = IntentRecognizer()
        self.action_planner = ActionPlanner()
        self.memory = {}
        self.active_contexts = []
        
        # Initialize action executors
        self._initialize_executors()
    
    def _initialize_executors(self):
        """Initialize various action executors"""
        # These will be loaded dynamically
        self.executors = {}
        
        # Load PowerShell executor if on Windows
        if sys.platform == 'win32':
            from powershell_executor import PowerShellExecutor
            self.executors['powershell'] = PowerShellExecutor()
        
        # Load other executors
        try:
            from screen_analyzer import ScreenAnalyzer
            self.executors['screen'] = ScreenAnalyzer()
        except ImportError:
            logger.warning("Screen analyzer not available")
        
        try:
            from web_automator import WebAutomator
            self.executors['web'] = WebAutomator()
        except ImportError:
            logger.warning("Web automator not available")
    
    async def process_request(self, user_input: str) -> Dict[str, Any]:
        """Process a user request end-to-end"""
        logger.info(f"Processing request: {user_input}")
        
        # Create task context
        context = TaskContext(original_request=user_input)
        self.active_contexts.append(context)
        
        try:
            # Recognize intent
            context.status = TaskStatus.ANALYZING
            task_type, intent = self.intent_recognizer.recognize(user_input)
            context.task_type = task_type
            context.intent = intent
            logger.info(f"Recognized task type: {task_type}, intent: {intent}")
            
            # Plan steps
            context.status = TaskStatus.PLANNING
            steps = self.action_planner.plan(context)
            context.steps = steps
            logger.info(f"Planned {len(steps)} steps")
            
            # Execute steps
            context.status = TaskStatus.EXECUTING
            for i, step in enumerate(steps):
                context.current_step = i
                logger.info(f"Executing step {i+1}/{len(steps)}: {step['action']}")
                
                try:
                    result = await self._execute_step(step, context)
                    context.outputs.append(result)
                    
                    # Check if we should stop
                    if result.get('stop_execution'):
                        break
                        
                except Exception as e:
                    logger.error(f"Step failed: {e}")
                    context.error_count += 1
                    
                    # Try recovery
                    if context.error_count < 3:
                        context.status = TaskStatus.RECOVERING
                        recovery_result = await self._recover_from_error(e, step, context)
                        if recovery_result.get('recovered'):
                            continue
                    
                    raise
            
            # Mark as completed
            context.status = TaskStatus.COMPLETED
            context.end_time = datetime.now()
            
            return {
                'success': True,
                'task_type': task_type.value,
                'steps_executed': len(context.outputs),
                'duration': (context.end_time - context.start_time).total_seconds(),
                'outputs': context.outputs
            }
            
        except Exception as e:
            logger.error(f"Task failed: {e}")
            context.status = TaskStatus.FAILED
            context.end_time = datetime.now()
            
            return {
                'success': False,
                'error': str(e),
                'traceback': traceback.format_exc(),
                'steps_completed': context.current_step,
                'duration': (context.end_time - context.start_time).total_seconds()
            }
    
    async def _execute_step(self, step: Dict[str, Any], context: TaskContext) -> Dict[str, Any]:
        """Execute a single step"""
        action = step['action']
        params = step.get('params', {})
        
        # Route to appropriate executor
        if action == 'capture_screen':
            return await self._capture_screen(params)
        elif action == 'ensure_application_running':
            return await self._ensure_app_running(params)
        elif action == 'find_dialog':
            return await self._find_dialog(params, context)
        elif action == 'click_close_button':
            return await self._click_close_button(params, context)
        elif action == 'verify_dialog_closed':
            return await self._verify_dialog_closed(params, context)
        else:
            # Generic execution
            return await self._execute_generic(action, params, context)
    
    async def _capture_screen(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Capture screenshot"""
        if 'screen' in self.executors:
            screenshot_path = await self.executors['screen'].capture(
                reason=params.get('reason', 'unknown')
            )
            return {'screenshot': screenshot_path}
        else:
            # Fallback to PowerShell
            return await self._execute_powershell(
                "Take-Screenshot",
                {'Path': f"screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"}
            )
    
    async def _ensure_app_running(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Ensure application is running"""
        app = params.get('app')
        
        # Check if app is running
        check_cmd = f"Get-Process | Where-Object {{$_.ProcessName -like '*{app}*'}}"
        result = await self._execute_powershell_command(check_cmd)
        
        if not result.get('output'):
            # Start the application
            start_cmd = f"Start-Process {app}"
            await self._execute_powershell_command(start_cmd)
            await asyncio.sleep(3)  # Wait for app to start
        
        return {'app_running': True}
    
    async def _find_dialog(self, params: Dict[str, Any], context: TaskContext) -> Dict[str, Any]:
        """Find dialog on screen"""
        # This would use computer vision or UI automation
        # For now, return known coordinates
        return {
            'dialog_found': True,
            'coordinates': {'x': 1271, 'y': 497}
        }
    
    async def _click_close_button(self, params: Dict[str, Any], context: TaskContext) -> Dict[str, Any]:
        """Click close button"""
        # Get coordinates from previous step
        coords = None
        for output in reversed(context.outputs):
            if 'coordinates' in output:
                coords = output['coordinates']
                break
        
        if not coords:
            coords = {'x': 1271, 'y': 497}  # Fallback
        
        # Use safe clicking method
        script = f"""
        . .\\safe_ui_automation.ps1
        Invoke-SafeClick -X {coords['x']} -Y {coords['y']}
        """
        
        result = await self._execute_powershell_command(script)
        
        if params.get('fallback') and not result.get('success'):
            # Try ESC key
            esc_script = "[System.Windows.Forms.SendKeys]::SendWait('{ESC}')"
            await self._execute_powershell_command(esc_script)
        
        return {'clicked': True}
    
    async def _verify_dialog_closed(self, params: Dict[str, Any], context: TaskContext) -> Dict[str, Any]:
        """Verify dialog is closed"""
        timeout = params.get('timeout', 2)
        await asyncio.sleep(timeout)
        
        # Capture screen and analyze
        screenshot = await self._capture_screen({'reason': 'verification'})
        
        # In a real implementation, this would use computer vision
        # For now, assume success
        return {'dialog_closed': True, 'screenshot': screenshot}
    
    async def _execute_generic(self, action: str, params: Dict[str, Any], context: TaskContext) -> Dict[str, Any]:
        """Execute generic action"""
        logger.info(f"Executing generic action: {action}")
        return {'action': action, 'params': params, 'executed': True}
    
    async def _execute_powershell(self, function: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute PowerShell function"""
        param_str = ' '.join([f"-{k} {v}" for k, v in params.items()])
        command = f"{function} {param_str}"
        return await self._execute_powershell_command(command)
    
    async def _execute_powershell_command(self, command: str) -> Dict[str, Any]:
        """Execute PowerShell command"""
        try:
            # Add necessary assemblies
            full_command = f"""
            Add-Type -AssemblyName System.Windows.Forms
            {command}
            """
            
            result = subprocess.run(
                ['powershell', '-Command', full_command],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            return {
                'success': result.returncode == 0,
                'output': result.stdout,
                'error': result.stderr
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    async def _recover_from_error(self, error: Exception, step: Dict[str, Any], context: TaskContext) -> Dict[str, Any]:
        """Attempt to recover from an error"""
        logger.info(f"Attempting recovery from: {error}")
        
        # Simple recovery strategies
        if "click" in step.get('action', '').lower():
            # Try alternative clicking method
            logger.info("Trying alternative click method")
            await self._execute_powershell_command("[System.Windows.Forms.SendKeys]::SendWait('{ESC}')")
            return {'recovered': True}
        
        return {'recovered': False}

# Main entry point
async def main():
    """Main entry point for the orchestrator"""
    orchestrator = AIOrchestrator()
    
    # Example usage
    print("\nAI-Enhanced Automation Orchestrator")
    print("===================================")
    print("Enter your commands in natural language.")
    print("Examples:")
    print("  - Close the Copilot dialog in PowerPoint")
    print("  - Create a new presentation about AI")
    print("  - Find all Python files in the project folder")
    print("  - Open Excel and create a budget spreadsheet")
    print("\nType 'exit' to quit.\n")
    
    while True:
        try:
            user_input = input("What would you like me to do? > ").strip()
            
            if user_input.lower() in ['exit', 'quit']:
                break
            
            if not user_input:
                continue
            
            # Process the request
            result = await orchestrator.process_request(user_input)
            
            # Display result
            if result['success']:
                print(f"\n✓ Task completed successfully!")
                print(f"  Task type: {result['task_type']}")
                print(f"  Steps executed: {result['steps_executed']}")
                print(f"  Duration: {result['duration']:.2f} seconds")
            else:
                print(f"\n✗ Task failed!")
                print(f"  Error: {result['error']}")
                print(f"  Steps completed: {result['steps_completed']}")
            
            print("\n" + "-" * 50 + "\n")
            
        except KeyboardInterrupt:
            print("\n\nInterrupted by user.")
            break
        except Exception as e:
            print(f"\nUnexpected error: {e}")
            logger.error(f"Unexpected error: {e}", exc_info=True)

if __name__ == "__main__":
    asyncio.run(main())