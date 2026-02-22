# Step 2: README Patterns Analysis -- Top AI Agent Framework Repos

> **Research Date:** February 21, 2026
> **Repos Analyzed:** CrewAI, AutoGen, LangGraph, OpenAI Agents SDK, Semantic Kernel

---

## 1. Individual Repo Analysis

### 1.1 CrewAI (44.4k stars)

**Opening Hook (First 3 Lines):**
- Centered logo image (600px wide) with alt text "Open source Multi-AI Agent orchestration framework"
- TrendShift badge (social proof widget showing trending status)
- Navigation bar: Homepage | Docs | Start Cloud Trial | Blog | Forum

The hook is image-heavy. The first *text* a reader sees is:

> "Fast and Flexible Multi-Agent Automation Framework"
>
> CrewAI is a lean, lightning-fast Python framework built entirely from scratch -- completely **independent of LangChain or other agent frameworks**. It empowers developers with both high-level simplicity and precise low-level control, ideal for creating autonomous AI agents tailored to any scenario.

**What works:** The subtitle immediately differentiates ("independent of LangChain") and uses power words ("lightning-fast", "lean"). The blockquote format makes the value proposition visually distinct from body text.

**Badge Usage (8 badges across 2 rows):**
- Row 1: GitHub stars, forks, issues, pull requests, MIT license
- Row 2: PyPI version, PyPI downloads, Twitter follow

**Section Structure:**
1. Value proposition / tagline
2. Enterprise product pitch (CrewAI AMP Suite)
3. Table of Contents
4. Why CrewAI? (with architecture diagram)
5. Getting Started (with embedded YouTube video)
6. Learning Resources
7. Understanding Flows and Crews (conceptual)
8. Installation (very detailed, with troubleshooting)
9. Full code walkthrough (agents.yaml, tasks.yaml, crew.py, main.py)
10. Key Features (bullet list)
11. Examples (with YouTube video thumbnails)
12. Comparison to competitors
13. FAQ
14. Contribution / Telemetry / License

**Visual Elements:**
- Large centered logo
- TrendShift trending badge (animated/dynamic)
- Architecture diagram ("asset.png" -- full-width)
- Multiple YouTube video thumbnails (clickable, embedded as images)
- No GIFs, no terminal screenshots

**Code Examples:**
- YAML configuration files (agents.yaml, tasks.yaml)
- Full Python classes (crew.py, main.py)
- CLI commands (crewai create crew, crewai run)
- Code is VERY long -- the README walks through an entire project scaffold. This is more tutorial than quickstart.

**Social Proof:**
- "Over 100,000 developers certified through community courses" (repeated 3 times)
- TrendShift badge
- Star count badge
- Downloads badge

**Installation Quality:**
- Shows `uv pip install crewai` (modern tooling)
- Optional extras: `crewai[tools]`
- CLI scaffold: `crewai create crew <name>`
- Troubleshooting section with common errors (tiktoken, Rust compiler)
- Rating: **Very thorough** but possibly too long for a README

**Architecture Explanation:**
- Two concepts: Crews (autonomous agents) and Flows (event-driven workflows)
- Explained through prose paragraphs, not diagrams
- The architecture diagram exists but is a marketing image, not a technical diagram

**Competitive Differentiation:**
- Explicitly calls out "independent of LangChain" in the opening hook
- Has a dedicated "CrewAI vs LangGraph" section in the ToC
- Positions as "standalone" and "lean" repeatedly

**Call to Action:**
- "Start Cloud Trial" in the navigation bar (commercial CTA)
- YouTube video thumbnails drive engagement
- Links to courses at learn.crewai.com
- The README is primarily a funnel to the commercial platform

---

### 1.2 AutoGen (54.7k stars)

**Opening Hook (First 3 Lines):**
- Small centered logo (100px SVG)
- Row of social badges (Twitter, LinkedIn, Discord, Docs, Blog)
- One-line bold definition:

> **AutoGen** is a framework for creating multi-agent AI applications that can act autonomously or work alongside humans.

Then immediately a redirect notice:

> **Important:** if you are new to AutoGen, please checkout Microsoft Agent Framework.

**What works:** The definition is crisp and immediately understandable. However, the redirect notice is unusual -- it signals a framework in transition, which may confuse newcomers.

**Badge Usage (5 badges, 1 row):**
- Twitter follow
- LinkedIn company page
- Discord server
- Documentation link
- Blog link

Note: No star count badge, no PyPI version badge in the header. These appear later in a table.

**Section Structure:**
1. One-line definition + redirect notice
2. Installation (immediate -- no "Why" section first)
3. Quickstart (3 progressive examples: Hello World, MCP Server, Multi-Agent)
4. AutoGen Studio (no-code GUI)
5. Why Use AutoGen? (comes AFTER code examples)
6. Where to go next? (table with Python / .NET / Studio columns)
7. Contributing + FAQ
8. Legal Notices

**Visual Elements:**
- Small 100px logo (understated)
- Landing page image ("autogen-landing.jpg")
- AutoGen Studio screenshot
- Table with colored badge links (Python=blue, .NET=green, Studio=purple)
- No diagrams, no GIFs, no YouTube embeds

**Code Examples:**
- Hello World: 10 lines, async, clean
- MCP Server: ~25 lines, shows real-world MCP integration
- Multi-Agent: ~35 lines, shows AgentTool pattern
- All examples are **self-contained and runnable**
- Progressive complexity (simple -> realistic -> multi-agent)

**What works exceptionally well:** The code examples are the best of all five repos. They are short, realistic, progressive, and each one demonstrates a distinct capability. The Hello World is truly minimal (8 functional lines).

**Social Proof:**
- Microsoft brand name
- "Magentic-One" reference (state-of-the-art multi-agent team)
- Community mentions (Discord, office hours, weekly talks)
- No explicit star count or download numbers in text

**Installation Quality:**
- Two lines: `pip install -U "autogen-agentchat" "autogen-ext[openai]"`
- Separate line for Studio: `pip install -U "autogenstudio"`
- Migration guide linked for v0.2 users
- Rating: **Clean and minimal** -- gets you running in one command

**Architecture Explanation:**
- Layered design described in prose: Core API -> AgentChat API -> Extensions API
- Each layer gets a one-line description with link
- The architecture is explained as a design philosophy, not with diagrams

**Competitive Differentiation:**
- Positions as "ecosystem" not just framework (framework + Studio + Bench)
- Multi-language (Python + .NET) shown via the table
- Does NOT explicitly name competitors

**Call to Action:**
- "Where to go next?" table is the primary CTA
- Discord server for community
- Contributing guide
- No commercial product push

---

### 1.3 LangGraph (24.9k stars)

**Opening Hook (First 3 Lines):**
- Full-width logo with dark/light mode variants (uses HTML `<picture>` tag)
- 4 badges: PyPI version, monthly downloads, open issues, docs link
- Single trust-building sentence:

> Trusted by companies shaping the future of agents -- including Klarna, Replit, Elastic, and more -- LangGraph is a low-level orchestration framework for building, managing, and deploying long-running, stateful agents.

**What works:** This is the strongest opening sentence of all five repos. It leads with social proof (named companies), then delivers a precise technical definition. The word "low-level" is deliberately chosen to attract serious engineers and filter out tire-kickers.

**Badge Usage (4 badges, 1 row):**
- PyPI version
- Monthly downloads (via pepy.tech)
- Open issues count
- Docs link

Minimal badge count. Every badge serves an information purpose (no vanity badges).

**Section Structure:**
1. Trust sentence + definition
2. Get started (install + minimal code)
3. Core benefits (5 items)
4. LangGraph's ecosystem
5. Additional resources
6. Acknowledgements

**That is it.** Six sections. The entire README is approximately 80 lines of prose. This is by far the shortest and most focused README of the five.

**Visual Elements:**
- Logo only (dark/light variants)
- No screenshots, no diagrams, no GIFs, no YouTube
- Zero images in the body

**Code Examples:**
- ONE code example: 20 lines showing a simple two-node graph
- The example uses TypedDict for state, plain functions for nodes, and graph compilation
- Includes the output comment: `# {'text': 'ab'}`

**What works:** The code example demonstrates the core mental model (state + nodes + edges = graph) in the absolute minimum lines. It does NOT try to show an LLM call -- it shows the framework abstraction.

**Social Proof:**
- Named customers: Klarna, Replit, Elastic
- "Case studies" link
- LangChain Academy reference
- LangChain Forum reference
- No star count mentioned in text

**Installation Quality:**
- Single line: `pip install -U langgraph`
- That is it. No extras, no troubleshooting.
- Rating: **Absolute minimum** -- effective

**Architecture Explanation:**
- Five "core benefits" each with a one-line description and a docs link
- Durable execution, human-in-the-loop, memory, debugging, deployment
- Architecture is implied through benefits, not explained structurally

**Competitive Differentiation:**
- "Low-level" (implies other frameworks are too high-level/opinionated)
- Mentions it "does not abstract prompts or architecture"
- Inspired by Pregel, Apache Beam, NetworkX (academic credibility)
- "Built by LangChain Inc but can be used without LangChain" (defuses the coupling concern)

**Call to Action:**
- Quickstart docs link
- LangChain Agents link (for higher-level usage)
- LangSmith (observability product) and LangSmith Deployment (commercial)
- The commercial CTAs are woven into the ecosystem section, not shouted

---

### 1.4 OpenAI Agents SDK (19.1k stars)

**Opening Hook (First 3 Lines):**
```
# OpenAI Agents SDK [![PyPI badge](...)]
```
- H1 title with inline PyPI version badge
- One-sentence definition:

> The OpenAI Agents SDK is a lightweight yet powerful framework for building multi-agent workflows. It is provider-agnostic, supporting the OpenAI Responses and Chat Completions APIs, as well as 100+ other LLMs.

- Full-width product screenshot (Agents Tracing UI)

**What works:** "Lightweight yet powerful" is the positioning. "Provider-agnostic" immediately defuses the concern that it only works with OpenAI. The screenshot shows a polished tracing UI -- this is a signal of production readiness.

**Badge Usage (1 badge):**
- PyPI version only, inline with the H1 title

This is the most minimal badge usage of all five. The OpenAI brand carries enough weight that badges are unnecessary social proof.

**Section Structure:**
1. Definition + screenshot
2. Core concepts (numbered list: Agents, Handoffs, Guardrails, Sessions, Tracing)
3. Get started (install with venv and uv)
4. Hello world example
5. Handoffs example
6. Functions example
7. The agent loop (conceptual explanation)
8. Common agent patterns
9. Tracing
10. Long running agents & human-in-the-loop
11. Sessions (with quick start, options, custom implementations)
12. Development (contributor setup)
13. Acknowledgements

**Visual Elements:**
- Tracing UI screenshot (the only image)
- No diagrams, no GIFs, no YouTube

**Code Examples:**
- Hello World: 7 lines of functional code, synchronous `Runner.run_sync`
- Handoffs: ~20 lines, shows language-based routing between agents
- Functions: ~15 lines, shows tool decoration with `@function_tool`
- Sessions: Multiple examples showing SQLite, Redis, custom implementations
- All examples include **output comments** showing expected results

**What works exceptionally well:** Every example includes its expected output as a comment. This lets readers understand what the code does without running it. The examples are progressive and each one teaches exactly one concept.

**Social Proof:**
- The "OpenAI" brand name is the social proof
- "100+ other LLMs" (breadth signal)
- Tracing integrations list (Logfire, AgentOps, Braintrust, etc.)
- Acknowledgements section credits Pydantic, LiteLLM, etc. (community goodwill)

**Installation Quality:**
- Shows both venv and uv approaches
- Optional extras: `[voice]`, `[redis]`
- Rating: **Clean and practical** with multiple path options

**Architecture Explanation:**
- "The agent loop" section is a 5-step numbered list explaining the execution model
- "Final output" subsection explains termination conditions
- This is the clearest mental model explanation of all five repos -- the reader understands exactly how the framework works in 10 sentences

**Competitive Differentiation:**
- "Provider-agnostic" (not locked to OpenAI)
- "Lightweight" (implicit comparison to heavier frameworks)
- Does NOT name competitors
- The Acknowledgements section names Pydantic, PydanticAI, LiteLLM -- this is confident (acknowledging adjacent tools rather than ignoring them)

**Call to Action:**
- Documentation link
- Examples directory
- No commercial product push (OpenAI's business model is API usage, not framework licensing)

---

### 1.5 Semantic Kernel (27.3k stars)

**Opening Hook (First 3 Lines):**
```
# Semantic Kernel
**Build intelligent AI agents and multi-agent systems with this enterprise-ready orchestration framework**
```
- H1 title (plain text, no image)
- Bold subtitle that is a complete value proposition
- 4 badges: MIT License, PyPI version, NuGet version, Discord

**What works:** The subtitle is action-oriented ("Build...") and immediately communicates the target audience ("enterprise-ready"). No wasted words.

**Badge Usage (4 badges, 1 row):**
- MIT License
- PyPI version
- NuGet version (shows multi-language support)
- Discord community

**Section Structure:**
1. What is Semantic Kernel? (definition paragraph)
2. System Requirements
3. Key Features (bullet list)
4. Installation (Python, .NET, Java)
5. Quickstart (Basic Agent, Agent with Plugins, Multi-Agent -- each in Python AND .NET)
6. Where to Go Next (numbered list with emoji)
7. Troubleshooting
8. Join the community
9. Contributor Wall of Fame
10. Code of Conduct
11. License

**Visual Elements:**
- No logo in the README (unusual)
- Contributor wall of fame (contrib.rocks image showing contributor avatars)
- No screenshots, no diagrams, no GIFs

**Code Examples:**
- Basic Agent (Python): ~15 lines
- Basic Agent (.NET): ~20 lines
- Agent with Plugins (Python): ~45 lines with Pydantic models
- Agent with Plugins (.NET): ~40 lines
- Multi-Agent (Python): ~40 lines showing triage pattern
- All examples include **output comments**
- Every Python example has a matching .NET example

**What works:** The dual-language examples are unique among these repos. For an enterprise audience that may have both Python and .NET teams, this is a strong differentiator. The plugin example with MenuPlugin is concrete and easy to understand (not abstract "hello world" fluff).

**Social Proof:**
- Microsoft brand
- "Enterprise-ready" positioning
- contrib.rocks contributor wall
- Discord community with 1000+ implied members
- Microsoft Learn documentation links (signals corporate investment)

**Installation Quality:**
- Environment variable setup shown first (practical)
- Python: `pip install semantic-kernel`
- .NET: `dotnet add package Microsoft.SemanticKernel`
- Java: link to build instructions
- Rating: **Multi-language friendly** -- shows all three platforms

**Architecture Explanation:**
- Key Features bullet list covers capabilities, not architecture
- No layered architecture diagram
- Architecture is implied through the progressive code examples (agent -> agent+plugins -> multi-agent)

**Competitive Differentiation:**
- "Model-agnostic" (not locked to any LLM provider)
- Multi-language (Python, .NET, Java)
- "Enterprise-ready" (repeated)
- Microsoft Learn integration (signals this is a supported Microsoft product, not a side project)
- Does NOT name competitors

**Call to Action:**
- "Where to Go Next" with numbered list (Getting Started Guide, Samples, Concepts)
- Discord community
- Contributing guide
- Blog link

---

## 2. Cross-Cutting Pattern Analysis

### 2.1 Opening Hook Patterns

| Repo | Strategy | First Text Seen |
|------|----------|-----------------|
| CrewAI | Logo + badges + tagline | "Fast and Flexible Multi-Agent Automation Framework" |
| AutoGen | Small logo + one-line definition | "AutoGen is a framework for creating multi-agent AI applications" |
| LangGraph | Logo + trust sentence | "Trusted by companies shaping the future of agents..." |
| OpenAI Agents | Title + definition + screenshot | "A lightweight yet powerful framework for multi-agent workflows" |
| Semantic Kernel | Title + bold subtitle | "Build intelligent AI agents and multi-agent systems..." |

**Best Practice:** LangGraph's approach wins. It leads with named customers (Klarna, Replit, Elastic), then delivers a precise 20-word definition. This is the "proof then promise" pattern -- it earns trust before asking for attention.

**Runner-up:** OpenAI Agents SDK. The screenshot of the Tracing UI immediately signals "this is a real product, not a toy."

**Anti-pattern:** CrewAI's opening is too padded. The reader has to scroll past a logo, a TrendShift widget, a navigation bar, and two rows of badges before reaching any meaningful text. On a GitHub mobile view, this is several screens of non-content.

### 2.2 Badge Strategy

| Repo | Badge Count | Types |
|------|-------------|-------|
| CrewAI | 8 | Stars, forks, issues, PRs, license, PyPI version, downloads, Twitter |
| AutoGen | 5 | Twitter, LinkedIn, Discord, docs, blog |
| LangGraph | 4 | PyPI version, downloads, issues, docs |
| OpenAI Agents | 1 | PyPI version |
| Semantic Kernel | 4 | License, PyPI, NuGet, Discord |

**Best Practice:** 3-5 badges maximum. Each badge should serve a distinct purpose:
- **Version badge** (tells users it is actively maintained)
- **Downloads/month** (social proof through usage)
- **Discord/community badge** (shows there is help available)
- **License badge** (reduces friction for enterprise adoption)

**Anti-pattern:** Star count badges. If someone is already on your GitHub page, they can see the star count. The badge is redundant. Fork and PR count badges are noise -- they signal nothing useful to a potential user.

### 2.3 Section Ordering

**Consensus pattern across all five repos:**

```
1. Identity       (logo + tagline + badges)
2. Definition     (what is this? -- 1-2 sentences)
3. Installation   (how do I get it? -- 1-3 lines)
4. Quick example  (show me it works -- minimal code)
5. Why/Features   (why should I care? -- bullet list)
6. Architecture   (how does it work conceptually?)
7. More examples  (progressive complexity)
8. Ecosystem      (what else integrates with this?)
9. Resources      (docs, tutorials, community)
10. Contributing  (how to help)
11. License
```

**Key insight:** The repos that put "Why" BEFORE code (CrewAI) feel like marketing. The repos that put code BEFORE "Why" (AutoGen, LangGraph, OpenAI Agents) feel like engineering tools. For a developer audience, **code first, philosophy second** is the winning order.

LangGraph takes this furthest: install command + 20-line example appears within the first screen of content.

### 2.4 Code Example Patterns

**Length comparison:**

| Repo | First Example | Lines | Runnable? | Output Shown? |
|------|---------------|-------|-----------|---------------|
| CrewAI | Full project scaffold | 100+ | Requires CLI tool | No |
| AutoGen | Hello World | 10 | Yes (copy-paste) | No |
| LangGraph | Two-node graph | 20 | Yes (copy-paste) | Yes (`# {'text': 'ab'}`) |
| OpenAI Agents | Hello World | 7 | Yes (copy-paste) | Yes (`# Code within the code...`) |
| Semantic Kernel | Basic Agent | 15 | Yes (copy-paste) | Yes (`# Language's essence...`) |

**Best Practice: The "7-Line Rule"**

The first code example should be **copy-paste-run** in under 10 lines. It should demonstrate the core value proposition in the absolute minimum code. OpenAI Agents SDK's 7-line hello world is the gold standard:

```python
from agents import Agent, Runner

agent = Agent(name="Assistant", instructions="You are a helpful assistant")

result = Runner.run_sync(agent, "Write a haiku about recursion in programming.")
print(result.final_output)

# Code within the code,
# Functions calling themselves,
# Infinite loop's dance.
```

This works because:
1. One import line
2. One agent definition
3. One execution call
4. One print
5. Expected output shown as comment
6. The output is *interesting* (a haiku), not boring ("Hello World")

**Anti-pattern:** CrewAI's first code example requires generating a project scaffold with a CLI tool, editing YAML files, and running `crewai run`. This is a 15-minute tutorial, not a quickstart. It belongs in documentation, not in a README.

**Progressive complexity pattern (AutoGen and OpenAI Agents do this best):**
1. Hello World (one agent, one message)
2. Tool usage (agent with a function/tool)
3. Multi-agent (two+ agents collaborating)

Each example should teach exactly ONE new concept.

### 2.5 Visual Element Strategy

| Repo | Logo | Architecture Diagram | Screenshot | YouTube | GIFs | Contributor Wall |
|------|------|---------------------|------------|---------|------|-----------------|
| CrewAI | Yes (large) | Yes (marketing-style) | No | Yes (3) | No | No |
| AutoGen | Yes (small) | No | Yes (Studio) | No | No | No |
| LangGraph | Yes (responsive) | No | No | No | No | No |
| OpenAI Agents | No | No | Yes (Tracing UI) | No | No | No |
| Semantic Kernel | No | No | No | No | No | Yes |

**Best Practice:**
- **One hero image** that shows the product in action (a screenshot beats a diagram)
- **Responsive logo** with dark/light variants (LangGraph's `<picture>` approach)
- YouTube video thumbnails are effective if the content is genuinely useful (not just marketing)

**Anti-pattern:** Multiple YouTube embeds make a README feel like a marketing landing page. One video max.

**Missing from all five:** Architecture diagrams that actually explain how the framework works. CrewAI has a marketing image, but none of the repos have a clean technical diagram showing data flow, component relationships, or execution model. This is a gap -- a simple boxes-and-arrows diagram explaining the mental model would be extremely valuable.

### 2.6 Social Proof Patterns

**Ranked by effectiveness:**

1. **Named customers** (LangGraph: "Klarna, Replit, Elastic") -- Strongest. Real companies using your tool in production.
2. **Brand name** (AutoGen/Microsoft, OpenAI, Semantic Kernel/Microsoft) -- Strong. Institutional credibility.
3. **Certified developer count** (CrewAI: "100,000+") -- Medium. Large number but "certified" is a soft metric.
4. **Download badges** (LangGraph, CrewAI) -- Medium. Objective and verifiable.
5. **Star count badges** (CrewAI) -- Weak on the repo page itself (redundant).
6. **TrendShift widgets** (CrewAI) -- Weak. Most developers don't know what TrendShift is.

**Best Practice:** If you have named customers, lead with them. If you do not, lead with download counts or a brand name. Avoid self-reported metrics that cannot be verified.

### 2.7 Installation Section Comparison

**Best:** LangGraph -- one line: `pip install -U langgraph`. Done.

**Most thorough:** Semantic Kernel -- shows Python, .NET, and Java installation, plus environment variable setup.

**Most practical:** OpenAI Agents SDK -- shows both venv and uv approaches, plus optional extras.

**Best Practice:** Lead with the single-line install. Then show optional extras. Then show environment setup. Never make the reader figure out which package to install -- have ONE clear default.

### 2.8 Architecture Communication

**Approaches ranked:**

1. **Numbered execution loop** (OpenAI Agents SDK): "When you call Runner.run(), we run a loop: 1) Call LLM, 2) Check for tool calls, 3) Check for final output..." -- This is the clearest mental model. It explains the runtime behavior in 5 numbered steps.

2. **Named abstractions** (LangGraph): "Durable execution, human-in-the-loop, memory, debugging, deployment" -- Each concept is named and linked. The reader can explore what matters to them.

3. **Layered design** (AutoGen): "Core API -> AgentChat API -> Extensions API" -- Shows the stack, implies the separation of concerns.

4. **Dual concept** (CrewAI): "Crews for autonomy, Flows for control" -- Clean dichotomy but takes many paragraphs to explain.

5. **Feature list** (Semantic Kernel): Bullet points of capabilities -- Informative but does not convey how the pieces fit together.

**Best Practice:** Explain the execution model in a numbered list. Developers think in terms of "what happens when I call run()?" Answer that question in 5 steps or fewer.

### 2.9 Competitive Differentiation

| Repo | Strategy | How They Differentiate |
|------|----------|----------------------|
| CrewAI | Direct comparison | "Independent of LangChain", has explicit "CrewAI vs LangGraph" section |
| AutoGen | Ecosystem breadth | Multi-language, Studio GUI, Bench benchmarking |
| LangGraph | Technical precision | "Low-level", "does not abstract prompts or architecture" |
| OpenAI Agents | Lightweight + breadth | "Lightweight yet powerful", "100+ LLMs", "provider-agnostic" |
| Semantic Kernel | Enterprise + multi-lang | "Enterprise-ready", Python + .NET + Java |

**Best Practice:** Differentiate through WHAT YOU ARE, not through what competitors are not. LangGraph ("low-level orchestration framework") and OpenAI Agents ("lightweight yet powerful") define their category clearly. The reader self-selects.

**Anti-pattern:** Explicitly comparing to named competitors (CrewAI's "CrewAI vs LangGraph" section). This can feel defensive and date quickly. It also sends traffic to the competitor's repo.

### 2.10 Call to Action

| Repo | Primary CTA | Secondary CTA |
|------|-------------|---------------|
| CrewAI | Start Cloud Trial | YouTube tutorials |
| AutoGen | "Where to go next?" table | Discord |
| LangGraph | Quickstart docs | LangSmith (commercial) |
| OpenAI Agents | Documentation + examples | Contributing |
| Semantic Kernel | Getting Started Guide | Discord + Samples |

**Best Practice:** The primary CTA should be "get deeper into the documentation." The README's job is to convert a scroller into a reader, and then hand them off to docs. Semantic Kernel's "Where to Go Next" with three numbered steps (Guide, Samples, Concepts) is effective because it gives the reader a clear path.

---

## 3. Synthesized Best Practices

### The Anatomy of a Scroll-Stopping README

Based on the analysis of all five repos, here is the optimal README structure for an AI agent framework:

#### Section 1: Identity (5 lines max)
```
[Responsive logo with dark/light mode]
[3-5 functional badges: version, downloads, license, community]
```

#### Section 2: Trust + Definition (3 lines max)
One sentence that combines social proof with a precise definition. The LangGraph formula:

> **[Social proof]** -- [Precise technical definition].

Example:
> Used by [Customer A], [Customer B], and [Customer C], **[ProjectName]** is a [adjective] framework for [specific capability].

If you do not have named customers, lead with the definition alone. Never waste this sentence on vague marketing language.

#### Section 3: Install (3 lines max)
```bash
pip install your-package
```
One line. Then a link to "detailed installation options" if needed.

#### Section 4: Hello World (15 lines max)
A copy-paste-runnable example that:
- Fits in one screen
- Shows the core abstraction in action
- Includes expected output as a comment
- Produces interesting output (not "Hello World" -- use something memorable)
- Requires exactly ONE environment variable (API key)

#### Section 5: Core Concepts (5-7 items)
A numbered or bulleted list where each item is:
- A **bolded concept name** (2-3 words)
- A one-sentence explanation
- A link to detailed docs

This section should answer: "What are the 5 things I need to understand to use this framework?"

#### Section 6: Progressive Examples (2-3 examples)
Each example teaches ONE new concept on top of the previous:
1. Single agent + tool
2. Multi-agent handoff/collaboration
3. (Optional) Production pattern (memory, tracing, deployment)

Each example should be 15-30 lines and include output comments.

#### Section 7: Why This Framework (5-7 bullets)
Feature/benefit bullets. Each bullet should follow the pattern:
- **Feature Name**: One-sentence benefit explanation with a docs link.

This section comes AFTER code because developers trust what they have seen over what they are told.

#### Section 8: Ecosystem + Resources
- Related tools/products
- Documentation link
- Tutorials/courses
- Community (Discord/Forum)
- Case studies or examples repo

#### Section 9: Contributing + License
Standard sections. Keep brief.

### The "Golden Rules" of Agent Framework READMEs

1. **Code before philosophy.** Show me it works before telling me why it is great.

2. **One concept per example.** Never combine tool usage, multi-agent, and memory in the same code block.

3. **Show the output.** Every code example should include the expected output as a comment. This lets readers evaluate the framework without cloning the repo.

4. **Install in one line.** The first install command should be a single `pip install` or `npm install`. Extras and options come after.

5. **Name your mental model.** Every framework has an execution loop. Explain it in 5 numbered steps. OpenAI Agents SDK does this perfectly.

6. **Lead with proof, not promises.** Named customers > download counts > star badges > self-reported metrics.

7. **Differentiate through identity, not comparison.** Say what you ARE ("low-level", "lightweight", "enterprise-ready"). Do not say what competitors are not.

8. **Keep it under 300 lines.** LangGraph's ~80-line README with focused links to docs outperforms CrewAI's 500+ line tutorial-in-a-README. The README's job is to convert interest into action, not to be the documentation.

9. **One hero image maximum.** A screenshot of the tool in action beats any number of architecture diagrams or marketing images.

10. **Make the next step obvious.** End with a "Where to Go Next" section that gives 2-3 numbered paths (quickstart guide, examples, API reference).

### What Stops a Scroller on GitHub

The critical moment is the first 5 lines of visible content (approximately what shows "above the fold" on GitHub without scrolling). Based on this analysis, the optimal above-the-fold content is:

```
[Clean logo -- responsive, not oversized]

[3-4 badges: version | downloads/month | license | discord]

> [One sentence: Social proof + precise definition]

## Get Started

pip install your-package
```

That is: identity, proof, definition, install. All in under 10 lines. Everything else goes below the fold.

The scroll stops when a developer sees:
1. A **name they recognize** (or that signals credibility)
2. A **clear definition** of what this does (not what it aspires to be)
3. A **download count** that shows adoption
4. An **install command** that shows they can be running in 30 seconds

Miss any of these four, and the developer keeps scrolling.

---

## 4. Data Summary Table

| Dimension | CrewAI | AutoGen | LangGraph | OpenAI Agents | Semantic Kernel |
|-----------|--------|---------|-----------|---------------|-----------------|
| Stars | 44.4k | 54.7k | 24.9k | 19.1k | 27.3k |
| README Length | ~500+ lines | ~300 lines | ~80 lines | ~350 lines | ~350 lines |
| Badges | 8 | 5 | 4 | 1 | 4 |
| First Code Example | ~100 lines (scaffold) | 10 lines | 20 lines | 7 lines | 15 lines |
| Images | 5+ (logo, diagram, YouTubes) | 3 (logo, landing, screenshot) | 1 (logo) | 1 (screenshot) | 1 (contributor wall) |
| Named Customers | No | No | Yes (Klarna, Replit, Elastic) | No | No |
| Output in Examples | No | No | Yes | Yes | Yes |
| Explicit Competitor Mention | Yes (vs LangGraph) | No | No | No | No |
| Multi-Language | No (Python only) | Yes (Python + .NET) | No (Python, JS separate) | No (Python, JS separate) | Yes (Python + .NET + Java) |
| Commercial CTA | Yes (Cloud Trial) | No | Yes (LangSmith) | No | No |
| Time to First `pip install` | ~40 lines down | ~15 lines down | ~8 lines down | ~15 lines down | ~30 lines down |

---

## 5. Recommendations for Our README

Based on this analysis, the highest-impact patterns to adopt:

1. **Steal LangGraph's opening formula:** Trust sentence with named users + precise definition in one line.
2. **Steal OpenAI Agents' code examples:** 7-line hello world with output comment, then progressive examples each teaching one concept.
3. **Steal OpenAI Agents' "agent loop" explanation:** Numbered steps explaining the execution model.
4. **Steal Semantic Kernel's dual-language examples:** If supporting multiple languages, show them side by side.
5. **Steal LangGraph's brevity:** Keep the README under 150 lines. Link to docs for everything else.
6. **Steal AutoGen's "Where to go next?" table:** Give readers 2-3 clear paths forward.
7. **Avoid CrewAI's tutorial-in-README pattern:** The README is a landing page, not documentation.
8. **Avoid explicit competitor comparisons:** Differentiate through identity.
9. **Include output comments in every code example.**
10. **Put the install command within the first 10 lines of visible content.**
