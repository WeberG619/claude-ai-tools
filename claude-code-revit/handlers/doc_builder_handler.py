# Documentation Builder Handler for Revit Add-ins
import os
import re
from datetime import datetime
from pathlib import Path

def process_documentation(input_file, output_dir):
    """Generate documentation for Revit add-in code"""
    
    # Read the source code
    with open(input_file, 'r', encoding='utf-8') as f:
        source_code = f.read()
    
    # Extract information
    info = extract_code_info(source_code)
    
    # Generate documentation
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_filename = f"{info['name']}_Documentation_{timestamp}.md"
    
    documentation = generate_documentation(info)
    
    # Write the documentation
    output_path = Path(output_dir) / output_filename
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(documentation)
    
    # Also generate README
    readme_path = Path(output_dir) / f"{info['name']}_README_{timestamp}.md"
    with open(readme_path, 'w') as f:
        f.write(generate_readme(info))
    
    return output_path

def extract_code_info(code):
    """Extract information from code"""
    info = {
        'name': 'RevitAddin',
        'classes': [],
        'methods': [],
        'description': ''
    }
    
    # Extract class names
    class_matches = re.findall(r'public class (\w+)', code)
    info['classes'] = class_matches
    
    # Extract main class name
    if class_matches:
        info['name'] = class_matches[0]
    
    # Extract methods with documentation
    method_pattern = r'///\s*<summary>\s*
\s*///\s*(.+?)\s*
\s*///\s*</summary>\s*
\s*public\s+(\w+)\s+(\w+)'
    method_matches = re.findall(method_pattern, code)
    
    for doc, return_type, method_name in method_matches:
        info['methods'].append({
            'name': method_name,
            'return_type': return_type,
            'description': doc.strip()
        })
    
    return info

def generate_documentation(info):
    """Generate comprehensive documentation"""
    
    doc = f"""# {info['name']} - API Documentation

Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}

## Overview

This documentation covers the {info['name']} Revit add-in.

## Classes

"""
    
    for class_name in info['classes']:
        doc += f"### {class_name}

"
        doc += f"Main class for the add-in functionality.

"
    
    doc += "## Methods

"
    
    for method in info['methods']:
        doc += f"### {method['name']}

"
        doc += f"**Returns:** `{method['return_type']}`

"
        doc += f"**Description:** {method['description']}

"
        doc += "**Example:**
```csharp
// TODO: Add usage example
```

"
    
    doc += """## Error Handling

The add-in implements comprehensive error handling:
- All Revit API calls are wrapped in try-catch blocks
- Transactions are properly managed with rollback on failure
- User-friendly error messages via TaskDialog

## Best Practices

1. Always use transactions for model modifications
2. Check element validity before access
3. Dispose of transactions properly
4. Handle user cancellation gracefully

## Troubleshooting

### Common Issues

1. **Transaction Error**: Ensure all model modifications are within a transaction
2. **Null Reference**: Check if elements exist before accessing
3. **Invalid Element**: Verify element hasn't been deleted

## Support

For issues or questions, please contact the development team.
"""
    
    return doc

def generate_readme(info):
    """Generate README file"""
    
    readme = f"""# {info['name']}

A Revit add-in for [describe purpose].

## Installation

1. Copy the .dll file to your Revit Add-ins folder:
   - `%appdata%\Autodesk\Revit\Addins\2024\`

2. Copy the .addin manifest file to the same location

3. Restart Revit

## Usage

1. In Revit, go to the Add-ins tab
2. Look for {info['name']} in the ribbon
3. Click to execute

## Features

- Feature 1: Description
- Feature 2: Description
- Feature 3: Description

## Requirements

- Revit 2024 or later
- .NET Framework 4.8

## Configuration

No additional configuration required.

## Known Issues

None at this time.

## Version History

- v1.0.0 - Initial release

## License

[Your license here]

## Contact

[Your contact information]
"""
    
    return readme

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 2:
        input_file = sys.argv[1]
        output_dir = sys.argv[2]
        result = process_documentation(input_file, output_dir)
        print(f"Generated documentation: {result}")
