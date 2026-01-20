# Test Generator Handler for Revit Code
import os
import re
from datetime import datetime
from pathlib import Path

def process_test_generation(input_file, output_dir):
    """Generate unit tests for Revit add-in code"""
    
    # Read the source code
    with open(input_file, 'r', encoding='utf-8') as f:
        source_code = f.read()
    
    # Parse the code to find classes and methods
    class_name = extract_class_name(source_code)
    methods = extract_methods(source_code)
    
    # Generate test code
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_filename = f"{class_name}_Tests_{timestamp}.cs"
    
    test_code = generate_test_code(class_name, methods)
    
    # Write the test file
    output_path = Path(output_dir) / output_filename
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(test_code)
    
    return output_path

def extract_class_name(code):
    """Extract the main class name from code"""
    match = re.search(r'public class (\w+)', code)
    return match.group(1) if match else "UnknownClass"

def extract_methods(code):
    """Extract public methods from code"""
    pattern = r'public\s+(\w+)\s+(\w+)\s*\([^)]*\)'
    return re.findall(pattern, code)

def generate_test_code(class_name, methods):
    """Generate NUnit test code"""
    
    test_code = f"""using System;
using NUnit.Framework;
using Moq;
using Autodesk.Revit.DB;
using Autodesk.Revit.UI;

namespace RevitTests
{{
    [TestFixture]
    public class {class_name}Tests
    {{
        private Mock<Document> mockDoc;
        private Mock<UIDocument> mockUiDoc;
        private {class_name} testInstance;
        
        [SetUp]
        public void Setup()
        {{
            // Setup mock objects
            mockDoc = new Mock<Document>();
            mockUiDoc = new Mock<UIDocument>();
            mockUiDoc.Setup(x => x.Document).Returns(mockDoc.Object);
            
            // Create test instance
            testInstance = new {class_name}();
        }}
        
        [Test]
        public void Constructor_ShouldInitializeCorrectly()
        {{
            // Arrange & Act
            var instance = new {class_name}();
            
            // Assert
            Assert.IsNotNull(instance);
        }}
"""
    
    # Add test methods for each public method
    for return_type, method_name in methods:
        if method_name != class_name:  # Skip constructor
            test_code += f"""
        [Test]
        public void {method_name}_ShouldExecuteWithoutError()
        {{
            // Arrange
            // TODO: Set up test data
            
            // Act
            // TODO: Call {method_name}
            
            // Assert
            // TODO: Verify expected behavior
        }}
"""
    
    test_code += """    }
}"""
    
    return test_code

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 2:
        input_file = sys.argv[1]
        output_dir = sys.argv[2]
        result = process_test_generation(input_file, output_dir)
        print(f"Generated tests: {result}")
