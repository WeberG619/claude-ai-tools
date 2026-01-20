# LoadBundle - Restore Previous Agent Context

## Purpose
Reload context from a previous agent session using context bundles

## Variables
- BUNDLE_PATH: Path to the context bundle file

## Workflow
1. Read the specified context bundle
2. Extract key operations:
   - Files read
   - Commands executed
   - Searches performed
   - Files written/modified
3. Replay essential read operations
4. Summarize work completed
5. Set up agent for continuation

## Usage
```
/loadbundle agents/context_bundles/bundle_20240115_143022.md
```

## Report
- Session summary
- Key findings from previous work
- Current context state
- Ready for continuation