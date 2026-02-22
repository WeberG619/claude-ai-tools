# GitHub MCP Server: Comprehensive Setup Guide

> **Last Updated:** 2026-02-21
> **Source Repository:** [github/github-mcp-server](https://github.com/github/github-mcp-server) (27.1k stars)
> **Status:** Production-ready. The old `@modelcontextprotocol/server-github` npm package is **deprecated** as of April 2025.

---

## Overview: What This Gives You

The GitHub MCP Server connects AI agents (Claude Code, Claude Desktop, Cursor, etc.) directly to the GitHub API via the Model Context Protocol. Instead of agents using `gh` CLI commands through bash, the MCP server provides **structured, typed tool calls** that the LLM can invoke natively.

**What changes when you enable this:**
- Claude can directly read private repo contents, search code, browse issues, create PRs, manage workflows, and review security alerts -- all as first-class tool calls.
- No more "let me run a bash command" indirection for GitHub operations.
- The agent gets structured JSON responses instead of parsing CLI text output.
- Access to **51+ tools** across repositories, issues, pull requests, actions, code security, discussions, notifications, and more.

**Important caveat:** For many GitHub tasks in Claude Code, the `gh` CLI is actually **more context-efficient** and produces better results. The MCP server shines for natural language orchestration and when you want the LLM to have direct, structured access to GitHub data. See the "MCP vs gh CLI" section below.

---

## Prerequisites

1. **GitHub Account** -- free tier works; MCP server is available to all GitHub users regardless of plan.
2. **GitHub Personal Access Token (PAT)** -- classic (ghp_) or fine-grained.
3. **One of:**
   - Docker (for local server via container)
   - Go toolchain (for building from source)
   - Nothing extra (for remote hosted server -- recommended)
4. **An MCP host:** Claude Code 2.1.1+, Claude Desktop, Cursor, VS Code, etc.

---

## Authentication & Token Setup

### Token Types

| Token Type | Prefix | Behavior with MCP Server |
|-----------|--------|--------------------------|
| Classic PAT | `ghp_` | Tools auto-filtered at startup based on token scopes. You only see tools you have permission to use. |
| Fine-grained PAT | `github_pat_` | Permissions enforced at API level. |
| OAuth token | `gho_` | Uses scope challenges -- prompts appear when needed authorizations are missing. |

### Recommended Token Scopes (Classic PAT)

For **full functionality** across all toolsets:

| Scope | Required For |
|-------|-------------|
| `repo` | All repository operations (read/write code, issues, PRs, commits) |
| `read:org` | Organization and team information |
| `read:packages` | Docker image access (if using Docker install) |
| `workflow` | GitHub Actions workflow management |
| `gist` | Gist operations |
| `read:discussion` | Discussion access |
| `security_events` | Code scanning and secret scanning alerts |
| `notifications` | Notification management |
| `project` | GitHub Projects (v2) operations |

**Minimum for basic use** (repos, issues, PRs): `repo` and `read:org`.

### Creating a Token

1. Go to https://github.com/settings/tokens
2. Click "Generate new token" > "Generate new token (classic)"
3. Name it something like `mcp-server-claude`
4. Select the scopes above
5. Generate and **copy immediately** (you cannot see it again)

### Relationship to Existing `gh` CLI Auth

Your system currently has `gh` CLI authenticated:
```
Account: WeberG619
Token type: OAuth (gho_)
Scopes: delete_repo, gist, read:org, repo, workflow
```

**The MCP server does NOT reuse your `gh` CLI token automatically.** They are separate authentication paths:
- `gh` CLI stores its token in `~/.config/gh/hosts.yml`
- The MCP server needs its own token via `GITHUB_PERSONAL_ACCESS_TOKEN` env var or `Authorization` header

**However**, you can extract the gh token and reuse it:
```bash
# Get your existing gh token
gh auth token

# Use it for the MCP server (they share the same GitHub API)
export GITHUB_PERSONAL_ACCESS_TOKEN=$(gh auth token)
```

**Note:** Your `gho_` OAuth token already has the key scopes (`repo`, `read:org`, `workflow`, `gist`, `delete_repo`), so it will work with most MCP toolsets. You may need `security_events` and `notifications` scopes for those specific toolsets.

---

## Installation Methods

### Method 1: Remote Hosted Server (Recommended)

GitHub hosts the MCP server at `https://api.githubcopilot.com/mcp/` -- no Docker, no build, no maintenance.

**For Claude Code:**
```bash
claude mcp add-json github '{"type":"http","url":"https://api.githubcopilot.com/mcp/","headers":{"Authorization":"Bearer YOUR_GITHUB_PAT"}}'
```

Or using your existing gh token:
```bash
claude mcp add-json github "{\"type\":\"http\",\"url\":\"https://api.githubcopilot.com/mcp/\",\"headers\":{\"Authorization\":\"Bearer $(gh auth token)\"}}"
```

Scope options:
- `--scope local` (default) -- only this project
- `--scope user` -- all your projects
- `--scope project` -- shared via `.mcp.json` in repo

**For Claude Code 2.1.0 and earlier:**
```bash
claude mcp add --transport http github https://api.githubcopilot.com/mcp -H "Authorization: Bearer YOUR_GITHUB_PAT"
```

### Method 2: Local Server via Docker

```bash
claude mcp add github \
  -e GITHUB_PERSONAL_ACCESS_TOKEN=YOUR_GITHUB_PAT \
  -- docker run -i --rm \
  -e GITHUB_PERSONAL_ACCESS_TOKEN \
  ghcr.io/github/github-mcp-server
```

Or add to Claude Code settings JSON directly:
```json
{
  "mcpServers": {
    "github": {
      "command": "docker",
      "args": [
        "run", "-i", "--rm",
        "-e", "GITHUB_PERSONAL_ACCESS_TOKEN",
        "ghcr.io/github/github-mcp-server"
      ],
      "env": {
        "GITHUB_PERSONAL_ACCESS_TOKEN": "YOUR_TOKEN_HERE"
      }
    }
  }
}
```

### Method 3: Build from Source (Go)

```bash
git clone https://github.com/github/github-mcp-server.git
cd github-mcp-server
go build -o github-mcp-server ./cmd/github-mcp-server
```

Then configure:
```json
{
  "mcpServers": {
    "github": {
      "command": "/path/to/github-mcp-server",
      "args": ["stdio"],
      "env": {
        "GITHUB_PERSONAL_ACCESS_TOKEN": "YOUR_TOKEN_HERE"
      }
    }
  }
}
```

---

## Claude Code Integration (Exact Config)

### Option A: Remote Server (Simplest -- Recommended)

Add to `~/.claude/settings.json` under the `mcpServers` key:

```json
{
  "mcpServers": {
    "github": {
      "type": "http",
      "url": "https://api.githubcopilot.com/mcp/",
      "headers": {
        "Authorization": "Bearer YOUR_GITHUB_PAT"
      }
    }
  }
}
```

### Option B: Remote Server with All Toolsets

```json
{
  "mcpServers": {
    "github": {
      "type": "http",
      "url": "https://api.githubcopilot.com/mcp/x/all",
      "headers": {
        "Authorization": "Bearer YOUR_GITHUB_PAT"
      }
    }
  }
}
```

### Option C: Remote Server with Specific Toolsets via Headers

```json
{
  "mcpServers": {
    "github": {
      "type": "http",
      "url": "https://api.githubcopilot.com/mcp/",
      "headers": {
        "Authorization": "Bearer YOUR_GITHUB_PAT",
        "X-MCP-Toolsets": "repos,issues,pull_requests,actions,code_security,discussions,notifications"
      }
    }
  }
}
```

### Option D: Docker Local Server

```json
{
  "mcpServers": {
    "github": {
      "command": "docker",
      "args": [
        "run", "-i", "--rm",
        "-e", "GITHUB_PERSONAL_ACCESS_TOKEN",
        "-e", "GITHUB_TOOLSETS=repos,issues,pull_requests,actions,code_security",
        "ghcr.io/github/github-mcp-server"
      ],
      "env": {
        "GITHUB_PERSONAL_ACCESS_TOKEN": "YOUR_TOKEN_HERE"
      }
    }
  }
}
```

### Option E: Read-Only Mode (Safer for Research Tasks)

```json
{
  "mcpServers": {
    "github": {
      "type": "http",
      "url": "https://api.githubcopilot.com/mcp/x/all/readonly",
      "headers": {
        "Authorization": "Bearer YOUR_GITHUB_PAT"
      }
    }
  }
}
```

### Verification

After adding, restart Claude Code and verify:
```bash
claude mcp list
```

Or inside Claude Code, use the `/mcp` command to see connected servers and their tools.

---

## Available Toolsets (Complete List)

### Standard Toolsets (Available on Both Remote & Local)

| Toolset | Purpose | URL Path |
|---------|---------|----------|
| `repos` | Repository browsing, file contents, commits, branches, tags | `/mcp/x/repos` |
| `issues` | Issue CRUD, comments, search | `/mcp/x/issues` |
| `pull_requests` | PR creation, review, merge, diff, comments | `/mcp/x/pull_requests` |
| `actions` | GitHub Actions workflows, runs, logs | `/mcp/x/actions` |
| `code_security` | Code scanning alerts, analysis | `/mcp/x/code_security` |
| `secret_protection` | Secret scanning alerts | `/mcp/x/secret_protection` |
| `dependabot` | Dependabot alerts, dependency management | `/mcp/x/dependabot` |
| `security_advisories` | Security advisory tools | `/mcp/x/security_advisories` |
| `discussions` | Discussion threads, comments | `/mcp/x/discussions` |
| `notifications` | Notification management | `/mcp/x/notifications` |
| `git` | Low-level git operations | `/mcp/x/git` |
| `gists` | Gist management | `/mcp/x/gists` |
| `labels` | Label management | `/mcp/x/labels` |
| `orgs` | Organization and team tools | `/mcp/x/orgs` |
| `projects` | GitHub Projects (v2) management | `/mcp/x/projects` |
| `stargazers` | Star tracking | `/mcp/x/stargazers` |
| `users` | User information, search | `/mcp/x/users` |

### Remote-Only Toolsets (Hosted Server Exclusive)

| Toolset | Purpose | URL Path |
|---------|---------|----------|
| `copilot` | Copilot integration, assign Copilot to issues | `/mcp/x/copilot` |
| `copilot_spaces` | Copilot Spaces functionality | `/mcp/x/copilot_spaces` |
| `github_support_docs_search` | Search GitHub product/support documentation | `/mcp/x/github_support_docs_search` |

### Default Toolsets (When None Specified)

When you do not configure any toolsets, the server enables: **context, issues, pull_requests, repos, users**.

### Special Keywords

- `all` -- enables every available toolset
- `default` -- the standard set (useful in combination, e.g., `default,stargazers,actions`)

---

## Available Tools (Complete List -- 51+ Tools)

### Repository Tools (`repos`)
| Tool | Description |
|------|-------------|
| `get_file_contents` | Get contents of a file or directory from a GitHub repository |
| `create_or_update_file` | Create or update a single file in a GitHub repository |
| `delete_file` | Delete a file from a GitHub repository |
| `push_files` | Push multiple files to a GitHub repository in a single commit |
| `create_repository` | Create a new GitHub repository in your account |
| `fork_repository` | Fork a GitHub repository to your account or specified organization |
| `create_branch` | Create a new branch in a GitHub repository |
| `list_branches` | List branches in a GitHub repository |
| `list_commits` | Get list of commits of a branch in a GitHub repository |
| `get_commit` | Get details for a commit from a GitHub repository |
| `search_repositories` | Search for GitHub repositories |
| `search_code` | Search for code across GitHub repositories |
| `list_tags` | List git tags in a GitHub repository |
| `get_tag` | Get details about a specific git tag |

### Issue Tools (`issues`)
| Tool | Description |
|------|-------------|
| `create_issue` | Create a new issue in a GitHub repository |
| `get_issue` | Get details of a specific issue |
| `update_issue` | Update an existing issue |
| `list_issues` | List issues in a GitHub repository |
| `search_issues` | Search for issues across GitHub repositories |
| `get_issue_comments` | Get comments for a specific issue |
| `add_issue_comment` | Add a comment to a specific issue |

### Pull Request Tools (`pull_requests`)
| Tool | Description |
|------|-------------|
| `create_pull_request` | Create a new pull request |
| `get_pull_request` | Get details of a specific pull request |
| `update_pull_request` | Update an existing pull request |
| `list_pull_requests` | List pull requests in a repository |
| `get_pull_request_diff` | Get the diff of a pull request |
| `get_pull_request_files` | Get the files changed in a pull request |
| `get_pull_request_comments` | Get comments for a specific pull request |
| `get_pull_request_reviews` | Get reviews for a specific pull request |
| `get_pull_request_status` | Get the combined status of a pull request |
| `merge_pull_request` | Merge a pull request |
| `update_pull_request_branch` | Update PR branch with latest changes from base |
| `create_pending_pull_request_review` | Create a pending review for a PR |
| `add_pull_request_review_comment_to_pending_review` | Add a comment to a pending review |
| `submit_pending_pull_request_review` | Submit a pending review |
| `delete_pending_pull_request_review` | Delete a pending review |
| `create_and_submit_pull_request_review` | Create and submit a review in one step |

### Notification Tools (`notifications`)
| Tool | Description |
|------|-------------|
| `list_notifications` | List all GitHub notifications for the authenticated user |
| `get_notification_details` | Get detailed information for a specific notification |
| `dismiss_notification` | Dismiss a notification (mark as read or done) |
| `mark_all_notifications_read` | Mark all notifications as read |
| `manage_notification_subscription` | Manage a notification subscription (ignore, watch, delete) |
| `manage_repository_notification_subscription` | Manage repository notification subscription |

### User & Search Tools (`users`)
| Tool | Description |
|------|-------------|
| `get_me` | Get details of the authenticated GitHub user |
| `search_users` | Search for GitHub users |

### Code Security Tools (`code_security`)
| Tool | Description |
|------|-------------|
| `list_code_scanning_alerts` | List code scanning alerts in a repository |
| `get_code_scanning_alert` | Get details of a specific code scanning alert |

### Secret Protection Tools (`secret_protection`)
| Tool | Description |
|------|-------------|
| `list_secret_scanning_alerts` | List secret scanning alerts in a repository |
| `get_secret_scanning_alert` | Get details of a specific secret scanning alert |

### Copilot Tools (`copilot` -- Remote Only)
| Tool | Description |
|------|-------------|
| `assign_copilot_to_issue` | Assign Copilot to a specific issue |
| `request_copilot_review` | Request a GitHub Copilot code review for a PR |

---

## Configuration Options (Advanced)

### Environment Variables

| Variable | Purpose | Default |
|----------|---------|---------|
| `GITHUB_PERSONAL_ACCESS_TOKEN` | Auth token (required for local) | None |
| `GITHUB_HOST` | GitHub Enterprise host URL | `github.com` |
| `GITHUB_TOOLSETS` | Comma-separated enabled toolsets | `context,issues,pull_requests,repos,users` |
| `GITHUB_TOOLS` | Comma-separated individual tools | None |
| `GITHUB_EXCLUDE_TOOLS` | Tools to exclude (overrides toolsets) | None |
| `GITHUB_READ_ONLY` | Read-only mode | `false` |
| `GITHUB_DYNAMIC_TOOLSETS` | Enable dynamic toolset discovery (local only) | `false` |
| `GITHUB_LOCKDOWN_MODE` | Restrict public repo content to push-access users | `false` |

### Dynamic Toolset Discovery (Local Server Only)

Starts with minimal tools and lets the LLM discover/enable toolsets on demand:
```bash
github-mcp-server --dynamic-toolsets --tools=get_me,search_code
```

This exposes three discovery tools:
- `enable_toolset` -- activate a toolset at runtime
- `list_available_toolsets` -- see what toolsets exist
- `get_toolset_tools` -- see what tools are in a toolset

### Read-Only Mode

Blocks all write operations. Useful for research/analysis agents:
- Remote: append `/readonly` to URL or set `X-MCP-Readonly: true`
- Local: `--read-only` flag or `GITHUB_READ_ONLY=true`

### Lockdown Mode

Restricts public repository content to users with push access. Private repo access is unaffected.
- Remote: `X-MCP-Lockdown: true`
- Local: `--lockdown-mode` flag

### Insiders Mode (Experimental Features)

Access pre-release tools and features:
- Remote URL: `https://api.githubcopilot.com/mcp/insiders`
- Remote header: `X-MCP-Insiders: true`

### Tool Search (CLI Utility)

```bash
# Search available tools by keyword
github-mcp-server tool-search "issue" --max-results 10

# Via Docker
docker run -it --rm ghcr.io/github/github-mcp-server tool-search "pull request" --max-results 5
```

---

## What "Deep Web" Data Becomes Accessible

When the GitHub MCP server is connected, Claude gains structured access to data that is **not publicly indexed** or accessible via web search:

### Private Repository Data
- **Source code** -- read any file from any private repo you have access to
- **Commit history** -- full commit logs, diffs, author information
- **Branch structure** -- all branches, their status, protection rules
- **Tags and releases** -- version history

### Issue and PR Threads (Private Repos)
- **Issue discussions** -- full conversation threads including internal team discussions
- **PR review comments** -- line-by-line code review feedback
- **PR diffs** -- exact code changes with context
- **PR status** -- CI/CD check results, merge conflicts, approval status
- **Linked issues** -- cross-references between issues and PRs

### Security Intelligence
- **Code scanning alerts** -- SAST findings, vulnerability details
- **Secret scanning alerts** -- exposed credentials, tokens, keys
- **Dependabot alerts** -- vulnerable dependency information
- **Security advisories** -- repository-specific security advisories

### Organization Data
- **Team membership** -- who belongs to which teams
- **Organization structure** -- repos, teams, permissions
- **Internal discussions** -- organization discussion threads

### Workflow and CI/CD Data
- **GitHub Actions runs** -- build logs, failure details, timing
- **Workflow configurations** -- pipeline definitions
- **Deployment status** -- release and deployment tracking

### Notification Stream
- **Personal notifications** -- mentions, review requests, assignments
- **Repository watching** -- activity across watched repos

### What This Means in Practice

Before MCP, Claude could only access GitHub data by:
1. Running `gh` CLI commands (text output, requires bash)
2. Fetching public web pages (limited, no auth)
3. You copy-pasting content into the conversation

With MCP, Claude can **autonomously navigate** your entire GitHub universe -- searching across all your private repos, reading internal discussions, analyzing security alerts, and correlating information across issues, PRs, and code -- all through structured API calls with proper authentication.

---

## MCP Server vs `gh` CLI: When to Use Which

### Use `gh` CLI (via bash tool) when:
- Doing **batch operations** (bulk issue creation, scripted workflows)
- **Context efficiency matters** -- gh uses less LLM context than MCP tool calls
- Running in **CI/CD pipelines** or scripts
- You need **reproducible, auditable** commands
- The operation is a single, well-defined command

### Use MCP server when:
- You want **natural language orchestration** ("review the latest bug fix PR")
- The agent needs to **explore and discover** information across repos
- You want **structured data** back (JSON objects vs. text parsing)
- Operations involve **multiple correlated steps** (search issues, read related PRs, check CI status)
- You are building **autonomous agent workflows** that need direct GitHub access

### Hybrid Approach (Recommended)
Keep both available. Claude Code already has `gh` CLI access via bash. Adding the MCP server gives it a second, structured path. The agent can choose the most efficient method per task.

---

## Limitations and Gotchas

1. **Rate Limiting** -- The MCP server uses the GitHub API, which has rate limits (5,000 requests/hour for authenticated users). Heavy agent usage can hit this.

2. **Token Expiration** -- PATs can expire. If things stop working, check your token first.

3. **No File Upload** -- The MCP server can create/update files via API (base64 encoded), but not upload binary assets to releases.

4. **Large Repo Limitations** -- `get_file_contents` on very large files may truncate or fail. Code search has GitHub's standard limitations.

5. **No Webhook Management** -- Cannot create or manage webhooks through the MCP server.

6. **Context Bloat** -- Enabling `all` toolsets loads 51+ tool definitions into the LLM context, which can degrade tool selection accuracy. Enable only what you need.

7. **Remote vs Local Feature Parity** -- `copilot`, `copilot_spaces`, and `github_support_docs_search` toolsets are remote-only. Dynamic toolset discovery is local-only.

8. **OAuth Token Scope Challenges** -- If using an OAuth token (like `gho_` from `gh` CLI), you may get scope challenge prompts when accessing toolsets your token does not cover.

9. **Deprecated npm Package** -- The old `@modelcontextprotocol/server-github` (from `modelcontextprotocol/servers` repo) is **deprecated since April 2025**. Use `github/github-mcp-server` instead.

10. **Enterprise Requires GITHUB_HOST** -- For GitHub Enterprise Server, you must set `GITHUB_HOST=https://your.ghes.domain`. For GitHub Enterprise Cloud (ghe.com), use `https://yoursubdomain.ghe.com`.

---

## Alternative and Complementary MCP Servers

### GitMCP (gitmcp.io)
- **Repo:** [idosal/git-mcp](https://github.com/idosal/git-mcp)
- **Purpose:** Turns any GitHub repo into a documentation source for LLMs. Prioritizes `llms.txt`, falls back to README.
- **Usage:** Replace `github.com` with `gitmcp.io` in any repo URL.
- **Best for:** Documentation access, not full API operations.

### Git MCP Server (cyanheads)
- **Repo:** [cyanheads/git-mcp-server](https://github.com/cyanheads/git-mcp-server)
- **Purpose:** Low-level Git operations (clone, commit, branch, diff, merge, rebase, worktree, tag).
- **Best for:** Local git operations beyond what GitHub's API offers.

### GitLab MCP Server
- **Purpose:** Same concept as GitHub MCP but for GitLab. CI/CD pipelines, merge requests, issue tracking.
- **Best for:** Teams using GitLab instead of or alongside GitHub.

### Grounded Docs MCP Server
- **Repo:** [arabold/docs-mcp-server](https://github.com/arabold/docs-mcp-server)
- **Purpose:** Index websites, GitHub repos, local folders. Processes HTML, Markdown, PDF, Word, Excel, source code.
- **Best for:** Documentation search across multiple sources.

### The modelcontextprotocol/servers Git Server
- **Repo:** [modelcontextprotocol/servers](https://github.com/modelcontextprotocol/servers) (reference implementation)
- **Purpose:** Local git repo operations (read, search, manipulate). This is NOT a GitHub API server -- it works with local `.git` repos.
- **Best for:** Working with local repositories, not GitHub cloud operations.

---

## Quick Start Checklist

1. [ ] Decide: remote hosted server (easiest) or local Docker
2. [ ] Create a GitHub PAT with scopes: `repo`, `read:org`, `workflow`, `gist`, `notifications`, `security_events`
3. [ ] Run:
   ```bash
   claude mcp add-json github '{"type":"http","url":"https://api.githubcopilot.com/mcp/x/all","headers":{"Authorization":"Bearer YOUR_PAT_HERE"}}' --scope user
   ```
4. [ ] Restart Claude Code
5. [ ] Verify with `claude mcp list` or `/mcp` inside Claude Code
6. [ ] Test: Ask Claude "What are my recent GitHub notifications?" or "Search my repos for files named Dockerfile"

---

## References

- [github/github-mcp-server](https://github.com/github/github-mcp-server) -- Official repository
- [GitHub Docs: Using the GitHub MCP Server](https://docs.github.com/en/copilot/how-tos/provide-context/use-mcp/use-the-github-mcp-server)
- [GitHub Docs: Configuring Toolsets](https://docs.github.com/en/copilot/how-tos/provide-context/use-mcp/configure-toolsets)
- [Claude Code MCP Docs](https://code.claude.com/docs/en/mcp)
- [Installation Guide for Claude](https://github.com/github/github-mcp-server/blob/main/docs/installation-guides/install-claude.md)
- [Server Configuration Reference](https://github.com/github/github-mcp-server/blob/main/docs/server-configuration.md)
- [Remote Server Reference](https://github.com/github/github-mcp-server/blob/main/docs/remote-server.md)
- [Complete Tool List Gist (51 tools)](https://gist.github.com/didier-durand/2970be82fec6c84d522f7953ac7881b4)
- [MCP vs CLI Benchmark](https://mariozechner.at/posts/2025-08-15-mcp-vs-cli/)
- [aihero.dev: Connect Claude Code to GitHub MCP](https://www.aihero.dev/connect-claude-code-to-github)
