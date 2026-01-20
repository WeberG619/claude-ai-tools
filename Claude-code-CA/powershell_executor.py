#!/usr/bin/env python3
"""
PowerShell Executor Module
Integrates PowerShell automation scripts with the AI orchestrator
"""

import os
import sys
import subprocess
import json
import asyncio
import tempfile
from typing import Dict, List, Any, Optional
import logging
from pathlib import Path
import base64

logger = logging.getLogger(__name__)

class PowerShellExecutor:
    """Executes PowerShell commands and scripts with enhanced capabilities"""
    
    def __init__(self):
        self.script_cache = {}
        self.loaded_modules = set()
        self.execution_history = []
        self._initialize_base_scripts()
    
    def _initialize_base_scripts(self):
        """Load base PowerShell scripts"""
        base_scripts = [
            'safe_ui_automation.ps1',
            'robust_ui_automation.ps1',
            'complete_task_automation.ps1'
        ]
        
        for script in base_scripts:
            script_path = Path(script)
            if script_path.exists():
                self.script_cache[script] = script_path.read_text()
                logger.info(f"Loaded base script: {script}")
    
    async def execute(self, command: str, timeout: int = 30, capture_output: bool = True) -> Dict[str, Any]:
        """Execute a PowerShell command"""
        start_time = asyncio.get_event_loop().time()
        
        try:
            # Prepare the command with proper error handling
            wrapped_command = self._wrap_command(command)
            
            # Execute
            process = await asyncio.create_subprocess_exec(
                'powershell.exe',
                '-NoProfile',
                '-ExecutionPolicy', 'Bypass',
                '-Command', wrapped_command,
                stdout=asyncio.subprocess.PIPE if capture_output else None,
                stderr=asyncio.subprocess.PIPE if capture_output else None
            )
            
            # Wait for completion with timeout
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=timeout
                )
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
                raise TimeoutError(f"Command timed out after {timeout} seconds")
            
            # Process results
            result = {
                'success': process.returncode == 0,
                'exit_code': process.returncode,
                'stdout': stdout.decode('utf-8', errors='replace') if stdout else '',
                'stderr': stderr.decode('utf-8', errors='replace') if stderr else '',
                'duration': asyncio.get_event_loop().time() - start_time
            }
            
            # Store in history
            self.execution_history.append({
                'command': command[:100] + '...' if len(command) > 100 else command,
                'result': result,
                'timestamp': asyncio.get_event_loop().time()
            })
            
            return result
            
        except Exception as e:
            logger.error(f"PowerShell execution failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'duration': asyncio.get_event_loop().time() - start_time
            }
    
    def _wrap_command(self, command: str) -> str:
        """Wrap command with error handling and output formatting"""
        return f"""
        $ErrorActionPreference = 'Continue'
        $ProgressPreference = 'SilentlyContinue'
        
        try {{
            {command}
            if ($LASTEXITCODE -and $LASTEXITCODE -ne 0) {{
                throw "Command failed with exit code: $LASTEXITCODE"
            }}
        }} catch {{
            Write-Error $_.Exception.Message
            exit 1
        }}
        """
    
    async def execute_script(self, script_name: str, parameters: Dict[str, Any] = None) -> Dict[str, Any]:
        """Execute a PowerShell script with parameters"""
        
        # Check if script is in cache
        if script_name in self.script_cache:
            script_content = self.script_cache[script_name]
        elif os.path.exists(script_name):
            with open(script_name, 'r') as f:
                script_content = f.read()
            self.script_cache[script_name] = script_content
        else:
            return {
                'success': False,
                'error': f"Script not found: {script_name}"
            }
        
        # Build parameter string
        param_str = ""
        if parameters:
            param_str = ' '.join([f"-{k} {self._format_parameter(v)}" for k, v in parameters.items()])
        
        # Create temporary script file with parameters
        with tempfile.NamedTemporaryFile(mode='w', suffix='.ps1', delete=False) as tf:
            tf.write(script_content)
            tf.write(f"\n\n# Execute with parameters\n")
            if parameters:
                tf.write(f"{param_str}\n")
            temp_script = tf.name
        
        try:
            # Execute the script
            result = await self.execute(f". '{temp_script}'")
            return result
        finally:
            # Clean up
            try:
                os.unlink(temp_script)
            except:
                pass
    
    def _format_parameter(self, value: Any) -> str:
        """Format parameter value for PowerShell"""
        if isinstance(value, bool):
            return '$true' if value else '$false'
        elif isinstance(value, str):
            # Escape quotes and return quoted string
            return f'"{value.replace('"', '`"')}"'
        elif isinstance(value, (list, tuple)):
            # Format as array
            formatted_items = [self._format_parameter(item) for item in value]
            return f"@({','.join(formatted_items)})"
        elif isinstance(value, dict):
            # Format as hashtable
            items = [f'"{k}"={self._format_parameter(v)}' for k, v in value.items()]
            return f"@{{{';'.join(items)}}}"
        else:
            return str(value)
    
    async def click_at_position(self, x: int, y: int, method: str = 'safe') -> Dict[str, Any]:
        """Click at specific screen coordinates"""
        if method == 'safe':
            command = f"""
            . .\\safe_ui_automation.ps1
            Invoke-SafeClick -X {x} -Y {y}
            """
        else:
            command = f"""
            . .\\robust_ui_automation.ps1
            Invoke-RobustClick -X {x} -Y {y} -Verify
            """
        
        return await self.execute(command)
    
    async def capture_screenshot(self, filename: Optional[str] = None) -> Dict[str, Any]:
        """Capture a screenshot"""
        if not filename:
            filename = f"screenshot_{asyncio.get_event_loop().time():.0f}.png"
        
        command = f"""
        Add-Type -AssemblyName System.Windows.Forms
        Add-Type -AssemblyName System.Drawing
        
        $bounds = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds
        $bitmap = New-Object System.Drawing.Bitmap($bounds.Width, $bounds.Height)
        $graphics = [System.Drawing.Graphics]::FromImage($bitmap)
        $graphics.CopyFromScreen($bounds.Location, [System.Drawing.Point]::Empty, $bounds.Size)
        $bitmap.Save('{filename}')
        $graphics.Dispose()
        $bitmap.Dispose()
        
        Write-Output "Screenshot saved: {filename}"
        """
        
        result = await self.execute(command)
        if result['success']:
            result['screenshot_path'] = filename
        
        return result
    
    async def get_active_window_info(self) -> Dict[str, Any]:
        """Get information about the active window"""
        command = """
        Add-Type @"
        using System;
        using System.Runtime.InteropServices;
        using System.Text;
        
        public class Win32 {
            [DllImport("user32.dll")]
            public static extern IntPtr GetForegroundWindow();
            
            [DllImport("user32.dll")]
            public static extern int GetWindowText(IntPtr hWnd, StringBuilder text, int count);
            
            [DllImport("user32.dll")]
            public static extern bool GetWindowRect(IntPtr hWnd, out RECT lpRect);
            
            public struct RECT {
                public int Left;
                public int Top;
                public int Right;
                public int Bottom;
            }
        }
"@
        
        $hwnd = [Win32]::GetForegroundWindow()
        $title = New-Object System.Text.StringBuilder 256
        [Win32]::GetWindowText($hwnd, $title, 256) | Out-Null
        
        $rect = New-Object Win32+RECT
        [Win32]::GetWindowRect($hwnd, [ref]$rect) | Out-Null
        
        @{
            Handle = $hwnd
            Title = $title.ToString()
            Left = $rect.Left
            Top = $rect.Top
            Width = $rect.Right - $rect.Left
            Height = $rect.Bottom - $rect.Top
        } | ConvertTo-Json
        """
        
        result = await self.execute(command)
        if result['success'] and result['stdout']:
            try:
                window_info = json.loads(result['stdout'])
                result['window_info'] = window_info
            except:
                pass
        
        return result
    
    async def send_keys(self, keys: str) -> Dict[str, Any]:
        """Send keyboard input"""
        command = f"""
        Add-Type -AssemblyName System.Windows.Forms
        [System.Windows.Forms.SendKeys]::SendWait("{keys}")
        """
        
        return await self.execute(command)
    
    async def start_application(self, app_name: str, arguments: str = "") -> Dict[str, Any]:
        """Start an application"""
        command = f"""
        Start-Process -FilePath "{app_name}" {f'-ArgumentList "{arguments}"' if arguments else ''} -PassThru | 
        Select-Object -Property Id, ProcessName, StartTime | 
        ConvertTo-Json
        """
        
        result = await self.execute(command)
        if result['success'] and result['stdout']:
            try:
                process_info = json.loads(result['stdout'])
                result['process_info'] = process_info
            except:
                pass
        
        return result
    
    async def close_application(self, app_name: str) -> Dict[str, Any]:
        """Close an application gracefully"""
        command = f"""
        $processes = Get-Process | Where-Object {{$_.ProcessName -like "*{app_name}*"}}
        foreach ($proc in $processes) {{
            $proc.CloseMainWindow() | Out-Null
            Start-Sleep -Milliseconds 500
            if (!$proc.HasExited) {{
                $proc | Stop-Process -Force
            }}
        }}
        Write-Output "Closed {app_name} processes: $($processes.Count)"
        """
        
        return await self.execute(command)
    
    async def execute_ui_automation(self, task: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """Execute a UI automation task"""
        
        # Map task to appropriate function
        task_mapping = {
            'close_dialog': self._close_dialog,
            'click_button': self._click_button,
            'fill_form': self._fill_form,
            'navigate_menu': self._navigate_menu
        }
        
        if task in task_mapping:
            return await task_mapping[task](params or {})
        else:
            return {
                'success': False,
                'error': f"Unknown UI automation task: {task}"
            }
    
    async def _close_dialog(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Close a dialog box"""
        # Try multiple methods
        methods = [
            # Method 1: Click known close button position
            lambda: self.click_at_position(
                params.get('x', 1271),
                params.get('y', 497),
                'safe'
            ),
            # Method 2: Send ESC key
            lambda: self.send_keys("{ESC}"),
            # Method 3: Alt+F4
            lambda: self.send_keys("%{F4}")
        ]
        
        for i, method in enumerate(methods):
            logger.info(f"Trying close method {i+1}")
            result = await method()
            if result.get('success'):
                return result
            await asyncio.sleep(0.5)
        
        return {
            'success': False,
            'error': "All close methods failed"
        }
    
    async def _click_button(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Click a button"""
        x = params.get('x')
        y = params.get('y')
        
        if x and y:
            return await self.click_at_position(x, y)
        else:
            return {
                'success': False,
                'error': "Button coordinates not provided"
            }
    
    async def _fill_form(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Fill a form field"""
        text = params.get('text', '')
        
        # Click on field if coordinates provided
        if 'x' in params and 'y' in params:
            await self.click_at_position(params['x'], params['y'])
            await asyncio.sleep(0.5)
        
        # Clear existing text
        await self.send_keys("^a")
        await asyncio.sleep(0.1)
        
        # Type new text
        return await self.send_keys(text)
    
    async def _navigate_menu(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Navigate through menus"""
        menu_path = params.get('path', [])
        
        for menu_item in menu_path:
            if isinstance(menu_item, str):
                # Use Alt+letter for menu navigation
                await self.send_keys(f"%{menu_item[0].lower()}")
            else:
                # Click coordinates
                await self.click_at_position(menu_item['x'], menu_item['y'])
            
            await asyncio.sleep(0.3)
        
        return {'success': True}

# Test function
async def test_powershell_executor():
    """Test the PowerShell executor"""
    executor = PowerShellExecutor()
    
    print("PowerShell Executor Test")
    print("=======================")
    
    # Test 1: Get active window
    print("\nTest 1: Getting active window info...")
    result = await executor.get_active_window_info()
    if result['success'] and 'window_info' in result:
        print(f"Active window: {result['window_info']['Title']}")
    
    # Test 2: Take screenshot
    print("\nTest 2: Taking screenshot...")
    result = await executor.capture_screenshot("test_screenshot.png")
    if result['success']:
        print(f"Screenshot saved: {result.get('screenshot_path')}")
    
    # Test 3: UI automation
    print("\nTest 3: Testing UI automation...")
    result = await executor.execute_ui_automation('close_dialog')
    print(f"Close dialog result: {result['success']}")

if __name__ == "__main__":
    asyncio.run(test_powershell_executor())