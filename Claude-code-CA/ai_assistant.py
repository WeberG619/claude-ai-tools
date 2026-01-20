#!/usr/bin/env python3
"""
AI Assistant - Complete Enhanced System
Main entry point that integrates all modules for intelligent automation
"""

import os
import sys
import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
import uuid
import argparse
from pathlib import Path

# Import all modules
from ai_orchestrator import AIOrchestrator, TaskContext, TaskStatus, TaskType
from ai_memory import AIMemory, Experience
from screen_analyzer import ScreenAnalyzer
from powershell_executor import PowerShellExecutor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('ai_assistant.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class AIAssistant:
    """Complete AI-enhanced automation assistant"""
    
    def __init__(self):
        self.orchestrator = AIOrchestrator()
        self.memory = AIMemory()
        self.screen_analyzer = ScreenAnalyzer()
        self.powershell = PowerShellExecutor()
        self.context_stack = []
        self.learning_mode = True
        self.verbose = True
        
        # Enhanced executors
        self._enhance_orchestrator()
        
        logger.info("AI Assistant initialized")
    
    def _enhance_orchestrator(self):
        """Enhance orchestrator with memory and advanced capabilities"""
        # Replace basic executors with enhanced versions
        self.orchestrator.executors['screen'] = self.screen_analyzer
        self.orchestrator.executors['powershell'] = self.powershell
        
        # Add memory integration
        original_execute = self.orchestrator._execute_step
        
        async def enhanced_execute(step, context):
            # Check memory for better solutions
            if self.learning_mode:
                solution = await self.memory.get_best_solution(context.intent)
                if solution and solution['confidence'] > 0.8:
                    logger.info(f"Using learned solution with confidence {solution['confidence']}")
                    # Modify step based on learned solution
                    if 'actions' in solution['solution']:
                        step = solution['solution']['actions'][0]
            
            # Execute original
            result = await original_execute(step, context)
            
            # Learn from result
            if self.learning_mode:
                self.memory.update_working_memory('last_action', step)
                self.memory.update_working_memory('last_result', result)
            
            return result
        
        self.orchestrator._execute_step = enhanced_execute
    
    async def process_request(self, user_input: str) -> Dict[str, Any]:
        """Process user request with full AI enhancement"""
        request_id = str(uuid.uuid4())
        start_time = datetime.now()
        
        logger.info(f"Processing request {request_id}: {user_input}")
        
        try:
            # Check memory for similar past requests
            similar_experiences = await self.memory.recall_similar_experiences(
                user_input, 
                {'raw_input': user_input}
            )
            
            if similar_experiences and self.verbose:
                print(f"\n💭 Found {len(similar_experiences)} similar past experiences")
                
                # Use the most successful one as a guide
                best_experience = similar_experiences[0]
                if best_experience.outcome == 'success':
                    print(f"   Using successful pattern from {best_experience.timestamp}")
            
            # Process with orchestrator
            result = await self.orchestrator.process_request(user_input)
            
            # Get the context that was created
            context = self.orchestrator.active_contexts[-1] if self.orchestrator.active_contexts else None
            
            # Create experience record
            if context:
                experience = Experience(
                    id=request_id,
                    timestamp=start_time,
                    request=user_input,
                    intent=context.intent,
                    actions_taken=[
                        {'action': step['action'], 'params': step.get('params', {})}
                        for step in context.steps[:context.current_step + 1]
                    ],
                    outcome='success' if result['success'] else 'failure',
                    error_details=result.get('error'),
                    recovery_attempts=[],  # TODO: Track recovery attempts
                    performance_metrics={
                        'duration': result.get('duration', 0),
                        'steps_executed': result.get('steps_executed', 0)
                    }
                )
                
                # Store experience for learning
                await self.memory.store_experience(experience)
            
            # Add insights to result
            if self.verbose:
                performance = await self.memory.analyze_performance_trends()
                result['insights'] = {
                    'total_experiences': performance['total_experiences'],
                    'patterns_learned': performance['total_patterns'],
                    'similar_successes': len([e for e in similar_experiences if e.outcome == 'success'])
                }
            
            return result
            
        except Exception as e:
            logger.error(f"Request processing failed: {e}", exc_info=True)
            
            # Try to recover using memory
            if self.learning_mode:
                recovery = await self.memory.get_recovery_strategy(
                    str(e),
                    self.memory.working_memory
                )
                
                if recovery:
                    logger.info("Attempting learned recovery strategy")
                    try:
                        # Execute recovery
                        recovery_result = await self._execute_recovery(recovery)
                        if recovery_result['success']:
                            return recovery_result
                    except Exception as recovery_error:
                        logger.error(f"Recovery failed: {recovery_error}")
            
            return {
                'success': False,
                'error': str(e),
                'request_id': request_id
            }
    
    async def _execute_recovery(self, recovery: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a recovery strategy"""
        # Implementation depends on recovery type
        if recovery.get('type') == 'retry':
            # Retry with modifications
            modified_request = recovery.get('modified_request')
            if modified_request:
                return await self.orchestrator.process_request(modified_request)
        elif recovery.get('type') == 'alternative':
            # Try alternative approach
            alternative_steps = recovery.get('steps', [])
            # Execute alternative steps
            # ... implementation ...
        
        return {'success': False, 'error': 'Recovery not implemented'}
    
    async def interactive_mode(self):
        """Run in interactive mode"""
        print("\n🤖 AI-Enhanced Automation Assistant")
        print("=" * 50)
        print("\nI understand natural language commands like:")
        print("  • Close the Copilot dialog in PowerPoint")
        print("  • Create a new presentation about AI")
        print("  • Take a screenshot and save it")
        print("  • Open Excel and create a budget")
        print("  • Find all Python files in the project")
        print("\nSpecial commands:")
        print("  • 'status' - Show system status")
        print("  • 'learn' - Toggle learning mode")
        print("  • 'analyze' - Show performance analysis")
        print("  • 'exit' - Quit")
        print("\n" + "=" * 50 + "\n")
        
        while True:
            try:
                user_input = input("🎯 What would you like me to do? > ").strip()
                
                if not user_input:
                    continue
                
                if user_input.lower() == 'exit':
                    print("\n👋 Goodbye!")
                    break
                
                if user_input.lower() == 'status':
                    await self._show_status()
                    continue
                
                if user_input.lower() == 'learn':
                    self.learning_mode = not self.learning_mode
                    print(f"\n📚 Learning mode: {'ON' if self.learning_mode else 'OFF'}")
                    continue
                
                if user_input.lower() == 'analyze':
                    await self._show_analysis()
                    continue
                
                # Process the request
                print(f"\n🔄 Processing: {user_input}")
                result = await self.process_request(user_input)
                
                # Display results
                if result['success']:
                    print(f"\n✅ Task completed successfully!")
                    if 'task_type' in result:
                        print(f"   Type: {result['task_type']}")
                    if 'steps_executed' in result:
                        print(f"   Steps: {result['steps_executed']}")
                    if 'duration' in result:
                        print(f"   Time: {result['duration']:.2f}s")
                    
                    if 'insights' in result and self.verbose:
                        insights = result['insights']
                        print(f"\n📊 Insights:")
                        print(f"   Total experiences: {insights['total_experiences']}")
                        print(f"   Patterns learned: {insights['patterns_learned']}")
                        print(f"   Similar successes: {insights['similar_successes']}")
                else:
                    print(f"\n❌ Task failed")
                    print(f"   Error: {result.get('error', 'Unknown error')}")
                    
                    # Suggest alternatives
                    print(f"\n💡 Suggestions:")
                    print(f"   • Try rephrasing your request")
                    print(f"   • Make sure the target application is open")
                    print(f"   • Check if you have necessary permissions")
                
                print("\n" + "-" * 50 + "\n")
                
            except KeyboardInterrupt:
                print("\n\n⚠️  Interrupted. Type 'exit' to quit properly.")
            except Exception as e:
                print(f"\n🚨 Unexpected error: {e}")
                logger.error(f"Interactive mode error: {e}", exc_info=True)
    
    async def _show_status(self):
        """Show system status"""
        print("\n📊 System Status")
        print("=" * 40)
        
        # Memory status
        performance = await self.memory.analyze_performance_trends()
        print(f"Memory:")
        print(f"  • Experiences: {performance['total_experiences']}")
        print(f"  • Patterns: {performance['total_patterns']}")
        
        # Recent performance
        if performance['daily_performance']:
            recent = performance['daily_performance'][-1]
            print(f"\nToday's Performance:")
            print(f"  • Tasks: {recent['total']}")
            print(f"  • Success Rate: {recent['success_rate']*100:.1f}%")
        
        # Common errors
        if performance['common_errors']:
            print(f"\nCommon Issues:")
            for error in performance['common_errors'][:3]:
                print(f"  • {error['error'][:50]}... ({error['count']} times)")
        
        # Active modules
        print(f"\nActive Modules:")
        print(f"  • Screen Analyzer: {'✓' if hasattr(self, 'screen_analyzer') else '✗'}")
        print(f"  • PowerShell: {'✓' if hasattr(self, 'powershell') else '✗'}")
        print(f"  • Learning: {'✓' if self.learning_mode else '✗'}")
    
    async def _show_analysis(self):
        """Show performance analysis"""
        print("\n📈 Performance Analysis")
        print("=" * 40)
        
        analysis = await self.memory.analyze_performance_trends()
        
        # Success trends
        if analysis['daily_performance']:
            print("\nSuccess Rate Trend (Last 7 days):")
            for stat in analysis['daily_performance'][-7:]:
                bar_length = int(stat['success_rate'] * 20)
                bar = '█' * bar_length + '░' * (20 - bar_length)
                print(f"  {stat['date']}: {bar} {stat['success_rate']*100:.1f}%")
        
        # Best patterns
        if analysis['best_patterns']:
            print("\nMost Effective Patterns:")
            for i, pattern in enumerate(analysis['best_patterns'], 1):
                print(f"  {i}. {pattern['type']}")
                print(f"     Success: {pattern['success_rate']*100:.1f}% | Used: {pattern['usage_count']} times")
        
        # Recommendations
        print("\n💡 Recommendations:")
        if analysis['common_errors']:
            print(f"  • Focus on fixing: {analysis['common_errors'][0]['error'][:40]}...")
        print(f"  • Keep using successful patterns")
        print(f"  • Continue learning from new experiences")
    
    async def execute_task(self, task_description: str) -> Dict[str, Any]:
        """Execute a specific task (API mode)"""
        return await self.process_request(task_description)
    
    def cleanup(self):
        """Cleanup resources"""
        if hasattr(self, 'memory'):
            self.memory.close()
        logger.info("AI Assistant cleaned up")

async def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='AI-Enhanced Automation Assistant')
    parser.add_argument('command', nargs='?', help='Command to execute')
    parser.add_argument('--no-learn', action='store_true', help='Disable learning mode')
    parser.add_argument('--quiet', action='store_true', help='Reduce output verbosity')
    parser.add_argument('--api', action='store_true', help='Run in API mode')
    
    args = parser.parse_args()
    
    # Create assistant
    assistant = AIAssistant()
    assistant.learning_mode = not args.no_learn
    assistant.verbose = not args.quiet
    
    try:
        if args.command:
            # Execute single command
            result = await assistant.execute_task(args.command)
            
            if args.api:
                # API mode - return JSON
                print(json.dumps(result, indent=2))
            else:
                # Human-readable output
                if result['success']:
                    print(f"✅ Success: {args.command}")
                else:
                    print(f"❌ Failed: {result.get('error', 'Unknown error')}")
        else:
            # Interactive mode
            await assistant.interactive_mode()
    
    finally:
        assistant.cleanup()

if __name__ == "__main__":
    # Handle Windows event loop
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    
    asyncio.run(main())