#!/usr/bin/env python3
"""
Autonomous Browser MCP Server
Unified interface for stealth browser automation with credential management

Tools:
- browser_start: Start the stealth browser
- browser_stop: Stop the browser
- browser_navigate: Navigate to URL
- browser_click: Click an element
- browser_type: Type into an element
- browser_screenshot: Take screenshot
- browser_scroll: Scroll the page
- browser_wait: Wait for element
- browser_execute_js: Execute JavaScript

- vault_store_credential: Store login credentials
- vault_get_credential: Get credentials (with approval flow)
- vault_list_credentials: List stored credentials
- vault_delete_credential: Delete credentials
- vault_store_totp: Store TOTP seed
- vault_get_totp: Generate TOTP code

- session_save: Save browser session
- session_restore: Restore browser session
- session_list: List saved sessions

- log_get_session: Get current session log
- log_list_sessions: List historical sessions
- log_search: Search action history

- auto_login: Automated login flow (navigate + fill + submit)
"""

import asyncio
import json
import sys
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

# Import our modules
from vault.credentials import get_vault
from vault.totp import generate_totp, get_totp_for_site, verify_totp_seed
from browser.stealth_browser import StealthBrowser
from browser.session_manager import get_session_manager
from browser.human_behavior import HumanBehavior
from logger.action_logger import get_logger, LogBrowser

# Initialize server
server = Server("autonomous-browser")

# Global browser instance
_browser = None
_logger = None


def get_browser_instance():
    global _browser
    if _browser is None:
        _browser = StealthBrowser()
    return _browser


def get_logger_instance():
    global _logger
    if _logger is None:
        _logger = get_logger()
    return _logger


# ==================== Browser Tools ====================

@server.list_tools()
async def list_tools():
    return [
        # Browser control
        Tool(
            name="browser_start",
            description="Start the stealth browser (undetected Chrome)",
            inputSchema={
                "type": "object",
                "properties": {
                    "headless": {
                        "type": "boolean",
                        "description": "Run without visible window (default: false)",
                        "default": False
                    },
                    "proxy": {
                        "type": "string",
                        "description": "Optional proxy server (host:port)"
                    }
                }
            }
        ),
        Tool(
            name="browser_stop",
            description="Stop the browser and save session",
            inputSchema={"type": "object", "properties": {}}
        ),
        Tool(
            name="browser_navigate",
            description="Navigate to a URL",
            inputSchema={
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "URL to navigate to"},
                    "wait_for_load": {
                        "type": "boolean",
                        "description": "Wait for page to fully load",
                        "default": True
                    }
                },
                "required": ["url"]
            }
        ),
        Tool(
            name="browser_click",
            description="Click an element on the page",
            inputSchema={
                "type": "object",
                "properties": {
                    "selector": {"type": "string", "description": "CSS selector, XPath, or ID"},
                    "by": {
                        "type": "string",
                        "enum": ["css", "xpath", "id", "name", "class"],
                        "default": "css"
                    },
                    "human_like": {
                        "type": "boolean",
                        "description": "Use human-like mouse movement",
                        "default": True
                    }
                },
                "required": ["selector"]
            }
        ),
        Tool(
            name="browser_type",
            description="Type text into an input field",
            inputSchema={
                "type": "object",
                "properties": {
                    "selector": {"type": "string", "description": "Element selector"},
                    "text": {"type": "string", "description": "Text to type"},
                    "by": {
                        "type": "string",
                        "enum": ["css", "xpath", "id", "name", "class"],
                        "default": "css"
                    },
                    "human_like": {
                        "type": "boolean",
                        "description": "Type with human-like speed variations",
                        "default": True
                    },
                    "clear_first": {
                        "type": "boolean",
                        "description": "Clear existing text first",
                        "default": True
                    }
                },
                "required": ["selector", "text"]
            }
        ),
        Tool(
            name="browser_screenshot",
            description="Take a screenshot of the current page",
            inputSchema={
                "type": "object",
                "properties": {
                    "filepath": {
                        "type": "string",
                        "description": "Where to save (auto-generated if not provided)"
                    }
                }
            }
        ),
        Tool(
            name="browser_scroll",
            description="Scroll the page",
            inputSchema={
                "type": "object",
                "properties": {
                    "direction": {
                        "type": "string",
                        "enum": ["up", "down", "top", "bottom"],
                        "default": "down"
                    },
                    "amount": {
                        "type": "integer",
                        "description": "Pixels to scroll",
                        "default": 500
                    }
                }
            }
        ),
        Tool(
            name="browser_wait",
            description="Wait for an element to appear",
            inputSchema={
                "type": "object",
                "properties": {
                    "selector": {"type": "string", "description": "Element selector"},
                    "by": {
                        "type": "string",
                        "enum": ["css", "xpath", "id", "name", "class"],
                        "default": "css"
                    },
                    "timeout": {
                        "type": "integer",
                        "description": "Max wait time in seconds",
                        "default": 30
                    },
                    "visible": {
                        "type": "boolean",
                        "description": "Wait for element to be visible",
                        "default": True
                    }
                },
                "required": ["selector"]
            }
        ),
        Tool(
            name="browser_execute_js",
            description="Execute JavaScript in the browser",
            inputSchema={
                "type": "object",
                "properties": {
                    "script": {"type": "string", "description": "JavaScript code to execute"}
                },
                "required": ["script"]
            }
        ),
        Tool(
            name="browser_get_page",
            description="Get current page info (URL, title, HTML)",
            inputSchema={
                "type": "object",
                "properties": {
                    "include_html": {
                        "type": "boolean",
                        "description": "Include full HTML source",
                        "default": False
                    }
                }
            }
        ),
        Tool(
            name="browser_find_element",
            description="Find an element and get its details",
            inputSchema={
                "type": "object",
                "properties": {
                    "selector": {"type": "string", "description": "Element selector"},
                    "by": {
                        "type": "string",
                        "enum": ["css", "xpath", "id", "name", "class"],
                        "default": "css"
                    }
                },
                "required": ["selector"]
            }
        ),
        Tool(
            name="browser_press_key",
            description="Press a keyboard key",
            inputSchema={
                "type": "object",
                "properties": {
                    "key": {
                        "type": "string",
                        "description": "Key to press (enter, tab, escape, etc.)"
                    }
                },
                "required": ["key"]
            }
        ),

        # Credential vault
        Tool(
            name="vault_store_credential",
            description="Store login credentials for a website",
            inputSchema={
                "type": "object",
                "properties": {
                    "site": {"type": "string", "description": "Website domain (e.g., github.com)"},
                    "username": {"type": "string", "description": "Login username or email"},
                    "password": {"type": "string", "description": "Login password"},
                    "notes": {"type": "string", "description": "Optional notes"},
                    "auto_login": {
                        "type": "boolean",
                        "description": "Allow Claude to use without asking (default: true)",
                        "default": True
                    }
                },
                "required": ["site", "username", "password"]
            }
        ),
        Tool(
            name="vault_get_credential",
            description="Get credentials for a site (respects auto_login setting)",
            inputSchema={
                "type": "object",
                "properties": {
                    "site": {"type": "string", "description": "Website domain"},
                    "require_approval": {
                        "type": "boolean",
                        "description": "Force manual approval even if auto_login is true",
                        "default": False
                    }
                },
                "required": ["site"]
            }
        ),
        Tool(
            name="vault_list_credentials",
            description="List all stored credentials (without passwords)",
            inputSchema={"type": "object", "properties": {}}
        ),
        Tool(
            name="vault_delete_credential",
            description="Delete stored credentials for a site",
            inputSchema={
                "type": "object",
                "properties": {
                    "site": {"type": "string", "description": "Website domain"}
                },
                "required": ["site"]
            }
        ),
        Tool(
            name="vault_update_auto_login",
            description="Update auto_login setting for a credential",
            inputSchema={
                "type": "object",
                "properties": {
                    "site": {"type": "string", "description": "Website domain"},
                    "auto_login": {
                        "type": "boolean",
                        "description": "New auto_login value"
                    }
                },
                "required": ["site", "auto_login"]
            }
        ),
        Tool(
            name="vault_store_totp",
            description="Store TOTP seed for 2FA",
            inputSchema={
                "type": "object",
                "properties": {
                    "site": {"type": "string", "description": "Website domain"},
                    "seed": {"type": "string", "description": "TOTP secret (base32)"},
                    "auto_generate": {
                        "type": "boolean",
                        "description": "Allow auto-generation without approval",
                        "default": True
                    }
                },
                "required": ["site", "seed"]
            }
        ),
        Tool(
            name="vault_get_totp",
            description="Generate TOTP code for a site",
            inputSchema={
                "type": "object",
                "properties": {
                    "site": {"type": "string", "description": "Website domain"},
                    "require_approval": {
                        "type": "boolean",
                        "description": "Force manual approval",
                        "default": False
                    }
                },
                "required": ["site"]
            }
        ),
        Tool(
            name="vault_verify_totp_seed",
            description="Verify a TOTP seed is valid",
            inputSchema={
                "type": "object",
                "properties": {
                    "seed": {"type": "string", "description": "TOTP seed to verify"}
                },
                "required": ["seed"]
            }
        ),

        # Session management
        Tool(
            name="session_save",
            description="Save current browser session (cookies, etc.)",
            inputSchema={
                "type": "object",
                "properties": {
                    "site": {"type": "string", "description": "Site identifier for the session"}
                },
                "required": ["site"]
            }
        ),
        Tool(
            name="session_restore",
            description="Restore a saved browser session",
            inputSchema={
                "type": "object",
                "properties": {
                    "site": {"type": "string", "description": "Site identifier"}
                },
                "required": ["site"]
            }
        ),
        Tool(
            name="session_list",
            description="List saved sessions",
            inputSchema={"type": "object", "properties": {}}
        ),
        Tool(
            name="session_delete",
            description="Delete a saved session",
            inputSchema={
                "type": "object",
                "properties": {
                    "site": {"type": "string", "description": "Site identifier"}
                },
                "required": ["site"]
            }
        ),

        # Action logging
        Tool(
            name="log_get_session",
            description="Get current session's action log",
            inputSchema={"type": "object", "properties": {}}
        ),
        Tool(
            name="log_list_sessions",
            description="List historical logging sessions",
            inputSchema={
                "type": "object",
                "properties": {
                    "days": {
                        "type": "integer",
                        "description": "How many days back to look",
                        "default": 30
                    }
                }
            }
        ),
        Tool(
            name="log_search",
            description="Search action history",
            inputSchema={
                "type": "object",
                "properties": {
                    "keyword": {"type": "string", "description": "Search keyword"},
                    "days": {
                        "type": "integer",
                        "description": "How many days back to search",
                        "default": 30
                    }
                },
                "required": ["keyword"]
            }
        ),
        Tool(
            name="log_credential_usage",
            description="Get credential usage history",
            inputSchema={
                "type": "object",
                "properties": {
                    "site": {"type": "string", "description": "Optional site filter"},
                    "days": {
                        "type": "integer",
                        "description": "How many days back",
                        "default": 30
                    }
                }
            }
        ),

        # High-level automation
        Tool(
            name="auto_login",
            description="Automated login flow: navigate to login page, fill credentials, submit",
            inputSchema={
                "type": "object",
                "properties": {
                    "site": {"type": "string", "description": "Website domain"},
                    "login_url": {"type": "string", "description": "Login page URL"},
                    "username_selector": {
                        "type": "string",
                        "description": "Username field selector",
                        "default": "input[name='username'], input[name='email'], input[type='email'], #username, #email"
                    },
                    "password_selector": {
                        "type": "string",
                        "description": "Password field selector",
                        "default": "input[name='password'], input[type='password'], #password"
                    },
                    "submit_selector": {
                        "type": "string",
                        "description": "Submit button selector",
                        "default": "button[type='submit'], input[type='submit'], #login, .login-button"
                    },
                    "require_approval": {
                        "type": "boolean",
                        "description": "Require manual approval",
                        "default": False
                    }
                },
                "required": ["site", "login_url"]
            }
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict):
    """Handle tool calls"""
    browser = get_browser_instance()
    vault = get_vault()
    session_mgr = get_session_manager()
    logger = get_logger_instance()

    try:
        # Browser tools
        if name == "browser_start":
            result = browser.start()
            logger.log_action("browser_start", arguments)

        elif name == "browser_stop":
            result = browser.stop()
            logger.end_session()

        elif name == "browser_navigate":
            result = browser.navigate(
                arguments["url"],
                arguments.get("wait_for_load", True)
            )
            logger.log_action("navigate", {"url": arguments["url"]}, result.get("status") == "success")

        elif name == "browser_click":
            result = browser.click(
                arguments["selector"],
                arguments.get("by", "css"),
                arguments.get("human_like", True)
            )
            logger.log_action("click", arguments, result.get("status") == "success")

        elif name == "browser_type":
            result = browser.type_text(
                arguments["selector"],
                arguments["text"],
                arguments.get("by", "css"),
                arguments.get("human_like", True),
                arguments.get("clear_first", True)
            )
            # Don't log the actual text (could be sensitive)
            logger.log_action("type", {"selector": arguments["selector"], "text_length": len(arguments["text"])})

        elif name == "browser_screenshot":
            result = browser.screenshot(arguments.get("filepath"))
            if result.get("status") == "success":
                logger.log_screenshot(result["filepath"])

        elif name == "browser_scroll":
            result = browser.scroll(
                arguments.get("direction", "down"),
                arguments.get("amount", 500)
            )

        elif name == "browser_wait":
            result = browser.wait_for_element(
                arguments["selector"],
                arguments.get("by", "css"),
                arguments.get("timeout", 30),
                arguments.get("visible", True)
            )

        elif name == "browser_execute_js":
            result = browser.execute_script(arguments["script"])
            logger.log_action("execute_js", {"script_length": len(arguments["script"])})

        elif name == "browser_get_page":
            if browser.driver:
                result = {
                    "status": "success",
                    "url": browser.driver.current_url,
                    "title": browser.driver.title
                }
                if arguments.get("include_html"):
                    result["html"] = browser.driver.page_source
            else:
                result = {"status": "error", "message": "Browser not started"}

        elif name == "browser_find_element":
            result = browser.find_element(
                arguments["selector"],
                arguments.get("by", "css")
            )

        elif name == "browser_press_key":
            result = browser.press_key(arguments["key"])

        # Vault tools
        elif name == "vault_store_credential":
            result = vault.store_credential(
                arguments["site"],
                arguments["username"],
                arguments["password"],
                arguments.get("notes", ""),
                arguments.get("auto_login", True)
            )

        elif name == "vault_get_credential":
            result = vault.get_credential(
                arguments["site"],
                arguments.get("require_approval", False)
            )
            if result.get("status") == "success":
                logger.log_credential_use(arguments["site"], result["username"], "password")

        elif name == "vault_list_credentials":
            result = {"credentials": vault.list_credentials()}

        elif name == "vault_delete_credential":
            result = vault.delete_credential(arguments["site"])

        elif name == "vault_update_auto_login":
            result = vault.update_auto_login(
                arguments["site"],
                arguments["auto_login"]
            )

        elif name == "vault_store_totp":
            result = vault.store_totp_seed(
                arguments["site"],
                arguments["seed"],
                arguments.get("auto_generate", True)
            )

        elif name == "vault_get_totp":
            result = get_totp_for_site(
                arguments["site"],
                arguments.get("require_approval", False)
            )
            if result.get("status") == "success":
                logger.log_credential_use(arguments["site"], "TOTP", "totp")

        elif name == "vault_verify_totp_seed":
            result = verify_totp_seed(arguments["seed"])

        # Session tools
        elif name == "session_save":
            if browser.driver:
                cookies = browser.driver.get_cookies()
                result = session_mgr.save_session(arguments["site"], cookies)
            else:
                result = {"status": "error", "message": "Browser not started"}

        elif name == "session_restore":
            session = session_mgr.get_session(arguments["site"])
            if session.get("status") == "success" and browser.driver:
                for cookie in session["cookies"]:
                    try:
                        browser.driver.add_cookie(cookie)
                    except:
                        pass
                result = {"status": "restored", "site": arguments["site"]}
            else:
                result = session

        elif name == "session_list":
            result = {"sessions": session_mgr.list_sessions()}

        elif name == "session_delete":
            result = session_mgr.delete_session(arguments["site"])

        # Logging tools
        elif name == "log_get_session":
            result = logger.get_session_log()

        elif name == "log_list_sessions":
            result = {"sessions": LogBrowser.list_sessions(arguments.get("days", 30))}

        elif name == "log_search":
            result = {"results": LogBrowser.search_actions(
                arguments["keyword"],
                arguments.get("days", 30)
            )}

        elif name == "log_credential_usage":
            result = {"usage": LogBrowser.get_credential_usage(
                arguments.get("site"),
                arguments.get("days", 30)
            )}

        # High-level automation
        elif name == "auto_login":
            # Get credentials
            creds = vault.get_credential(
                arguments["site"],
                arguments.get("require_approval", False)
            )

            if creds.get("status") == "approval_required":
                result = creds  # Return approval request to user
            elif creds.get("status") != "success":
                result = {"status": "error", "message": f"No credentials for {arguments['site']}"}
            else:
                # Start browser if not running
                if not browser.driver:
                    browser.start()

                # Navigate to login page
                nav = browser.navigate(arguments["login_url"])
                if nav.get("status") != "success":
                    result = nav
                else:
                    # Try to find and fill username field
                    username_selectors = arguments.get("username_selector",
                        "input[name='username'], input[name='email'], input[type='email'], #username, #email"
                    ).split(", ")

                    username_filled = False
                    for selector in username_selectors:
                        try:
                            r = browser.type_text(selector, creds["username"], human_like=True)
                            if r.get("status") == "success":
                                username_filled = True
                                break
                        except:
                            pass

                    if not username_filled:
                        result = {"status": "error", "message": "Could not find username field"}
                    else:
                        # Fill password
                        password_selectors = arguments.get("password_selector",
                            "input[name='password'], input[type='password'], #password"
                        ).split(", ")

                        password_filled = False
                        for selector in password_selectors:
                            try:
                                r = browser.type_text(selector, creds["password"], human_like=True)
                                if r.get("status") == "success":
                                    password_filled = True
                                    break
                            except:
                                pass

                        if not password_filled:
                            result = {"status": "error", "message": "Could not find password field"}
                        else:
                            # Click submit
                            submit_selectors = arguments.get("submit_selector",
                                "button[type='submit'], input[type='submit'], #login, .login-button"
                            ).split(", ")

                            submitted = False
                            for selector in submit_selectors:
                                try:
                                    r = browser.click(selector)
                                    if r.get("status") == "success":
                                        submitted = True
                                        break
                                except:
                                    pass

                            if submitted:
                                # Wait for navigation
                                import time
                                time.sleep(2)
                                result = {
                                    "status": "success",
                                    "message": f"Logged in to {arguments['site']}",
                                    "current_url": browser.driver.current_url
                                }
                                logger.log_credential_use(arguments["site"], creds["username"], "password")
                            else:
                                # Try pressing Enter instead
                                browser.press_key("enter")
                                time.sleep(2)
                                result = {
                                    "status": "success",
                                    "message": f"Submitted login for {arguments['site']}",
                                    "current_url": browser.driver.current_url
                                }

        else:
            result = {"status": "error", "message": f"Unknown tool: {name}"}

        return [TextContent(type="text", text=json.dumps(result, indent=2))]

    except Exception as e:
        logger.log_error("tool_error", str(e), {"tool": name, "arguments": arguments})
        return [TextContent(type="text", text=json.dumps({
            "status": "error",
            "message": str(e)
        }))]


async def main():
    """Run the MCP server"""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
