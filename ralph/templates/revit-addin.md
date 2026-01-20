# Revit Add-in Development

## Objective
[Describe the Revit add-in feature you want to build]

## Context
- This is a Revit API add-in project
- Use C# and the Revit API
- Check existing code patterns in the project
- Build with: dotnet build or MSBuild

## Working Directory
- Project: RevitMCPBridge2026 (or specify your project)
- Main files: Check src/ or the .csproj location

## Instructions
1. Read existing code to understand patterns
2. Implement the feature following Revit API best practices
3. Build the project and check for errors
4. If build succeeds, test in Revit
5. Commit working changes with descriptive messages

## Revit API Guidelines
- Always use transactions for model modifications
- Dispose of API objects properly
- Handle exceptions gracefully
- Use FilteredElementCollector for element queries
- Check for null before accessing properties

## Quality Standards
- Code compiles without warnings
- Follows existing naming conventions
- Includes XML documentation for public methods
- No hardcoded paths or magic numbers

## When Done
Update CHANGELOG.md and create DONE.md with summary.
