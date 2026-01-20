# Error Debugger Handler for Revit API
import os
import re
import json
from datetime import datetime
from pathlib import Path

def process_error_debug(input_file, output_dir):
    """Process Revit API errors and provide fixes"""
    
    # Read the error report
    with open(input_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Parse error information
    error_pattern = r'ERROR MESSAGE:\s*(.+?)(?=

|CODE THAT CAUSED ERROR:|$)'
    code_pattern = r'CODE THAT CAUSED ERROR:\s*(.+?)(?=

|REVIT VERSION:|$)'
    
    error_match = re.search(error_pattern, content, re.DOTALL)
    code_match = re.search(code_pattern, content, re.DOTALL)
    
    error_msg = error_match.group(1).strip() if error_match else "Unknown error"
    problem_code = code_match.group(1).strip() if code_match else ""
    
    # Analyze common Revit API errors
    fixes = analyze_revit_error(error_msg, problem_code)
    
    # Generate fixed code
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_filename = f"FixedCode_{timestamp}.cs"
    
    fixed_code = generate_fixed_code(error_msg, problem_code, fixes)
    
    # Write the fixed code
    output_path = Path(output_dir) / output_filename
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(fixed_code)
    
    # Create explanation file
    explanation = f"""# Revit API Error Fix Report

## Original Error:
{error_msg}

## Analysis:
{fixes['analysis']}

## Solution:
{fixes['solution']}

## Fixed Code:
See: {output_filename}

## Prevention Tips:
{fixes['prevention']}

Generated: {datetime.now().isoformat()}
"""
    
    explanation_path = Path(output_dir) / f"ErrorFix_Explanation_{timestamp}.md"
    with open(explanation_path, 'w') as f:
        f.write(explanation)
    
    return output_path

def analyze_revit_error(error_msg, code):
    """Analyze common Revit API errors"""
    
    fixes = {
        'analysis': '',
        'solution': '',
        'prevention': ''
    }
    
    # Transaction errors
    if 'without an active transaction' in error_msg.lower():
        fixes['analysis'] = "Attempting to modify the model without a transaction."
        fixes['solution'] = "Wrap the modification code in a Transaction."
        fixes['prevention'] = "Always use transactions for any model modifications."
    
    # Null reference
    elif 'object reference not set' in error_msg.lower():
        fixes['analysis'] = "Accessing a null object, likely an element that doesn't exist."
        fixes['solution'] = "Add null checks before accessing objects."
        fixes['prevention'] = "Always verify elements exist before use."
    
    # Invalid element
    elif 'invalid element' in error_msg.lower():
        fixes['analysis'] = "Trying to access a deleted or invalid element."
        fixes['solution'] = "Check element validity with IsValidObject."
        fixes['prevention'] = "Store element IDs instead of elements across transactions."
    
    else:
        fixes['analysis'] = "Generic Revit API error detected."
        fixes['solution'] = "Review Revit API documentation for proper usage."
        fixes['prevention'] = "Follow Revit API best practices."
    
    return fixes

def generate_fixed_code(error_msg, problem_code, fixes):
    """Generate fixed version of the code"""
    
    # For transaction errors
    if 'without an active transaction' in error_msg.lower():
        return f"""using Autodesk.Revit.DB;
using Autodesk.Revit.UI;

public Result ExecuteFixed(ExternalCommandData commandData, ref string message, ElementSet elements)
{{
    Document doc = commandData.Application.ActiveUIDocument.Document;
    
    // Fixed: Added transaction
    using (Transaction trans = new Transaction(doc, "Fixed Operation"))
    {{
        trans.Start();
        
        try
        {{
            {problem_code}
            
            trans.Commit();
            return Result.Succeeded;
        }}
        catch (Exception ex)
        {{
            trans.RollBack();
            message = ex.Message;
            return Result.Failed;
        }}
    }}
}}"""
    
    # Default fix template
    return f"""// Fixed code based on error analysis
// Original error: {error_msg}

{problem_code}

// TODO: Apply fix based on analysis
// Fix: {fixes['solution']}
"""

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 2:
        input_file = sys.argv[1]
        output_dir = sys.argv[2]
        result = process_error_debug(input_file, output_dir)
        print(f"Fixed code: {result}")
