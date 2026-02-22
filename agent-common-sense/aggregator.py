"""
Aggregator v1.0
================
Active context compression between pipeline stages.
Inspired by ROMA's Aggregator role — compresses agent output into
structured context packages before passing to the next agent.

Prevents context explosion across multi-step pipelines by extracting
key facts, artifacts, and decisions while dropping intermediate reasoning.

Three aggregation strategies:
  1. heuristic  — regex + keyword extraction (fast, no LLM call)
  2. structured — parse known output formats (JSON, markdown sections)
  3. passthrough — output small enough, no compression needed

Usage:
    from aggregator import Aggregator

    agg = Aggregator(strategy="auto")
    compressed = agg.aggregate_for_prompt(
        output=agent_result,
        step_config={"agent": "floor-plan-processor", "data_key": "spec"}
    )
"""

import json
import re
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional


@dataclass
class AggregatedContext:
    """Compressed context package for the next pipeline stage."""
    source_agent: str = ""
    step_index: int = 0
    key_facts: list[str] = field(default_factory=list)
    artifacts: dict = field(default_factory=dict)
    decisions: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    raw_summary: str = ""
    char_count_original: int = 0
    char_count_compressed: int = 0

    @property
    def compression_ratio(self) -> float:
        if self.char_count_original == 0:
            return 1.0
        return self.char_count_compressed / self.char_count_original

    def to_dict(self) -> dict:
        return {
            "source_agent": self.source_agent,
            "step_index": self.step_index,
            "key_facts": self.key_facts,
            "artifacts": self.artifacts,
            "decisions": self.decisions,
            "warnings": self.warnings,
            "raw_summary": self.raw_summary,
            "compression_ratio": round(self.compression_ratio, 3),
        }


# ─── PATTERNS ──────────────────────────────────────────────────

# Lines that typically contain key information
RESULT_PATTERNS = [
    re.compile(r"^\s*(?:Result|Output|Found|Created|Error|Warning|Status|Total|Count|Summary)[:\s]", re.IGNORECASE),
    re.compile(r"^\s*[-*]\s+\*\*[^*]+\*\*"),  # Bold markdown list items
    re.compile(r"^\s*\d+\.\s+\*\*"),  # Numbered list with bold
    re.compile(r"^\s*#{1,3}\s+"),  # Markdown headers (h1-h3)
]

# Lines that are typically intermediate reasoning (droppable)
NOISE_PATTERNS = [
    re.compile(r"^\s*(?:Let me|I'll|I will|I need to|First,? let|Now I|Okay|Sure)", re.IGNORECASE),
    re.compile(r"^\s*(?:Searching|Reading|Checking|Looking|Loading|Processing)", re.IGNORECASE),
    re.compile(r"^\s*(?:```\s*$|```\w+\s*$)"),  # Code fence markers alone
    re.compile(r"^\s*$"),  # Blank lines
]

# Patterns for extracting decisions
DECISION_PATTERNS = [
    re.compile(r"(?:decided|choosing|selected|using|will use|recommend|best option)[:\s](.{20,120})", re.IGNORECASE),
    re.compile(r"(?:approach|strategy|method|solution)[:\s](.{20,120})", re.IGNORECASE),
]

# Patterns for warnings/issues
WARNING_PATTERNS = [
    re.compile(r"(?:warning|caution|note|issue|problem|limitation|caveat|risk)[:\s](.{20,120})", re.IGNORECASE),
    re.compile(r"(?:could not|failed to|unable to|missing|not found)[:\s]?(.{10,120})", re.IGNORECASE),
]

# Numeric values with context
NUMERIC_PATTERN = re.compile(r"(\w[\w\s]{2,30})[:\s]+(\d+[\d.,]*\s*(?:ft|m|mm|in|px|%|items?|files?|walls?|rooms?|doors?|windows?)?)\b")

# File paths
FILE_PATH_PATTERN = re.compile(r"(?:/[\w./-]+(?:\.\w{1,5}))")


class Aggregator:
    """
    Compresses agent output between pipeline stages.

    Three aggregation strategies (configurable per pipeline):
      1. heuristic  — regex + keyword extraction (fast, no LLM call)
      2. structured — parse known output formats (JSON, markdown sections)
      3. passthrough — output small enough, no compression needed
    """

    MAX_COMPRESSED_CHARS = 2000
    MAX_KEY_FACTS = 10
    MAX_DECISIONS = 5
    MAX_WARNINGS = 5
    MAX_INPUT_CHARS = 50000  # Hard cap on input before processing
    PASSTHROUGH_THRESHOLD = 1000  # Below this, no compression needed

    def __init__(self, strategy: str = "auto", db_path: Optional[str] = None):
        self.strategy = strategy
        self.db_path = db_path or self._find_db()
        if self.db_path:
            try:
                self._ensure_schema()
            except Exception:
                self.db_path = None  # Degrade gracefully

    def _find_db(self) -> Optional[str]:
        candidates = [
            Path("/mnt/d/_CLAUDE-TOOLS/claude-memory-server/data/memories.db"),
            Path.home() / ".claude-memory" / "memories.db",
        ]
        for p in candidates:
            if p.exists():
                return str(p)
        return None

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _ensure_schema(self):
        conn = self._conn()
        conn.execute("""
            CREATE TABLE IF NOT EXISTS aggregation_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pipeline_name TEXT NOT NULL DEFAULT '',
                step_index INTEGER NOT NULL DEFAULT 0,
                agent_name TEXT NOT NULL DEFAULT '',
                strategy_used TEXT NOT NULL DEFAULT '',
                original_chars INTEGER NOT NULL DEFAULT 0,
                compressed_chars INTEGER NOT NULL DEFAULT 0,
                compression_ratio REAL NOT NULL DEFAULT 1.0,
                key_facts_extracted INTEGER DEFAULT 0,
                artifacts_extracted INTEGER DEFAULT 0,
                timestamp TEXT NOT NULL
            )
        """)
        conn.commit()
        conn.close()

    # ─── MAIN API ──────────────────────────────────────────────

    def aggregate(self, output: str, step_config: Optional[dict] = None,
                  pipeline_context: Optional[dict] = None) -> AggregatedContext:
        """
        Main entry point. Compress an agent's output for the next stage.

        Args:
            output: raw agent output string
            step_config: pipeline step dict (has "agent", "data_key", etc.)
            pipeline_context: accumulated context from prior steps
        """
        if not output:
            return AggregatedContext(
                raw_summary="No output produced.",
                char_count_original=0,
                char_count_compressed=len("No output produced."),
            )

        step_config = step_config or {}
        pipeline_context = pipeline_context or {}
        agent_name = step_config.get("agent", "unknown")
        data_key = step_config.get("data_key", "")
        step_index = pipeline_context.get("step", 0)

        # Hard cap on input
        if len(output) > self.MAX_INPUT_CHARS:
            output = output[:self.MAX_INPUT_CHARS]

        # Select strategy
        strategy = self._select_strategy(output) if self.strategy == "auto" else self.strategy

        # Execute strategy
        if strategy == "passthrough":
            ctx = AggregatedContext(
                source_agent=agent_name,
                step_index=step_index,
                raw_summary=output,
                char_count_original=len(output),
                char_count_compressed=len(output),
            )
        elif strategy == "structured":
            ctx = self._structured_aggregate(output, data_key)
        else:
            ctx = self._heuristic_aggregate(output, data_key)

        ctx.source_agent = agent_name
        ctx.step_index = step_index
        ctx.char_count_original = len(output)

        # Enforce hard cap
        prompt_text = self.to_prompt_section(ctx)
        if len(prompt_text) > self.MAX_COMPRESSED_CHARS:
            ctx = self._trim_context(ctx)

        ctx.char_count_compressed = len(self.to_prompt_section(ctx))

        # Log metrics
        if self.db_path:
            self.log_aggregation(
                original_size=ctx.char_count_original,
                compressed_size=ctx.char_count_compressed,
                strategy=strategy,
                pipeline_name=pipeline_context.get("pipeline_name", ""),
                step_index=step_index,
                agent_name=agent_name,
            )

        return ctx

    def aggregate_for_prompt(self, output: str, step_config: Optional[dict] = None,
                             pipeline_context: Optional[dict] = None) -> str:
        """Convenience method — returns formatted string ready for prompt injection."""
        ctx = self.aggregate(output, step_config, pipeline_context)
        return self.to_prompt_section(ctx)

    # ─── STRATEGIES ────────────────────────────────────────────

    def _select_strategy(self, output: str) -> str:
        """Auto-select aggregation strategy based on output characteristics."""
        if len(output) < self.PASSTHROUGH_THRESHOLD:
            return "passthrough"
        if self._has_json_block(output):
            return "structured"
        return "heuristic"

    def _heuristic_aggregate(self, output: str, data_key: str = "") -> AggregatedContext:
        """Strategy 1: Extract facts using regex patterns."""
        ctx = AggregatedContext()
        lines = output.split("\n")

        key_lines = []
        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue

            # Check if this is a noise line (skip)
            if any(p.match(stripped) for p in NOISE_PATTERNS):
                continue

            # Check if this is a result/key line (keep)
            if any(p.match(stripped) for p in RESULT_PATTERNS):
                key_lines.append(stripped)
                continue

            # Check for decisions
            for dp in DECISION_PATTERNS:
                m = dp.search(stripped)
                if m and len(ctx.decisions) < self.MAX_DECISIONS:
                    ctx.decisions.append(m.group(0).strip())
                    break

            # Check for warnings
            for wp in WARNING_PATTERNS:
                m = wp.search(stripped)
                if m and len(ctx.warnings) < self.MAX_WARNINGS:
                    ctx.warnings.append(m.group(0).strip())
                    break

        # Extract numeric values
        for m in NUMERIC_PATTERN.finditer(output):
            fact = f"{m.group(1).strip()}: {m.group(2).strip()}"
            if fact not in key_lines and len(key_lines) < self.MAX_KEY_FACTS * 2:
                key_lines.append(fact)

        # Extract file paths as artifacts
        paths = FILE_PATH_PATTERN.findall(output)
        if paths:
            ctx.artifacts["file_paths"] = list(set(paths))[:5]

        # Extract JSON blocks as artifacts
        json_blocks = self._extract_json_blocks(output)
        if json_blocks:
            ctx.artifacts["data"] = json_blocks[0] if len(json_blocks) == 1 else json_blocks

        # Deduplicate and limit key facts
        seen = set()
        for line in key_lines:
            normalized = line.strip().lower()
            if normalized not in seen:
                seen.add(normalized)
                ctx.key_facts.append(line)
            if len(ctx.key_facts) >= self.MAX_KEY_FACTS:
                break

        # Build summary from first meaningful header or first key fact
        headers = [l for l in lines if l.strip().startswith("#")]
        if headers:
            ctx.raw_summary = headers[0].lstrip("#").strip()
        elif ctx.key_facts:
            ctx.raw_summary = ctx.key_facts[0][:150]
        else:
            ctx.raw_summary = output[:150].strip()

        return ctx

    def _structured_aggregate(self, output: str, data_key: str = "") -> AggregatedContext:
        """Strategy 2: Parse known output formats (JSON, markdown sections)."""
        ctx = AggregatedContext()

        # Extract JSON blocks
        json_blocks = self._extract_json_blocks(output)
        if json_blocks:
            ctx.artifacts["data"] = json_blocks[0] if len(json_blocks) == 1 else json_blocks

        # Extract markdown sections
        sections = self._extract_markdown_sections(output)
        for title, content in sections[:self.MAX_KEY_FACTS]:
            # Keep section title + first sentence
            first_sentence = content.split(".")[0] + "." if "." in content else content[:100]
            ctx.key_facts.append(f"**{title}**: {first_sentence.strip()}")

        # Extract warnings from sections with warning-like titles
        for title, content in sections:
            title_lower = title.lower()
            if any(w in title_lower for w in ["warning", "issue", "error", "risk", "limitation", "caveat"]):
                ctx.warnings.append(f"{title}: {content[:100]}")

        # Build summary
        if sections:
            ctx.raw_summary = f"{len(sections)} sections processed. Main topics: {', '.join(t for t, _ in sections[:3])}"
        elif json_blocks:
            ctx.raw_summary = f"Structured data extracted ({len(json_blocks)} JSON blocks)"
        else:
            ctx.raw_summary = output[:150].strip()

        return ctx

    # ─── HELPERS ───────────────────────────────────────────────

    def _has_json_block(self, text: str) -> bool:
        """Check if text contains a JSON block."""
        return bool(re.search(r'```json\s*\n', text) or
                     ('{' in text and '}' in text and
                      text.count('{') >= 2))

    def _extract_json_blocks(self, text: str) -> list:
        """Find and parse JSON blocks in output text."""
        blocks = []

        # Try fenced code blocks first
        for m in re.finditer(r'```(?:json)?\s*\n(.*?)```', text, re.DOTALL):
            try:
                parsed = json.loads(m.group(1).strip())
                blocks.append(parsed)
            except (json.JSONDecodeError, ValueError):
                pass

        # Try standalone JSON objects if no fenced blocks found
        if not blocks:
            for m in re.finditer(r'(\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\})', text):
                try:
                    parsed = json.loads(m.group(1))
                    blocks.append(parsed)
                except (json.JSONDecodeError, ValueError):
                    pass

        return blocks

    def _extract_markdown_sections(self, output: str) -> list[tuple[str, str]]:
        """Extract markdown ## sections as (title, content) tuples."""
        sections = []
        current_title = None
        current_lines = []

        for line in output.split("\n"):
            header_match = re.match(r'^#{1,3}\s+(.+)', line)
            if header_match:
                if current_title and current_lines:
                    content = " ".join(l.strip() for l in current_lines if l.strip())
                    sections.append((current_title, content[:300]))
                current_title = header_match.group(1).strip()
                current_lines = []
            elif current_title:
                current_lines.append(line)

        # Don't forget last section
        if current_title and current_lines:
            content = " ".join(l.strip() for l in current_lines if l.strip())
            sections.append((current_title, content[:300]))

        return sections

    def _extract_key_lines(self, text: str) -> list[str]:
        """Extract lines that are likely key facts. Public for coordinator use."""
        key_lines = []
        for line in text.split("\n"):
            stripped = line.strip()
            if not stripped:
                continue
            if any(p.match(stripped) for p in NOISE_PATTERNS):
                continue
            if any(p.match(stripped) for p in RESULT_PATTERNS):
                key_lines.append(stripped)
        return key_lines[:self.MAX_KEY_FACTS]

    def _trim_context(self, ctx: AggregatedContext) -> AggregatedContext:
        """Trim context to fit within MAX_COMPRESSED_CHARS."""
        # Remove warnings first (lowest priority)
        while len(self.to_prompt_section(ctx)) > self.MAX_COMPRESSED_CHARS and ctx.warnings:
            ctx.warnings.pop()

        # Then trim key facts
        while len(self.to_prompt_section(ctx)) > self.MAX_COMPRESSED_CHARS and len(ctx.key_facts) > 3:
            ctx.key_facts.pop()

        # Then trim artifacts
        if len(self.to_prompt_section(ctx)) > self.MAX_COMPRESSED_CHARS and ctx.artifacts:
            # Convert complex artifacts to simple string summaries
            for key in list(ctx.artifacts.keys()):
                val = ctx.artifacts[key]
                if isinstance(val, (dict, list)):
                    ctx.artifacts[key] = str(val)[:200]

        # Then trim summary
        if len(self.to_prompt_section(ctx)) > self.MAX_COMPRESSED_CHARS:
            ctx.raw_summary = ctx.raw_summary[:100]

        return ctx

    # ─── OUTPUT FORMATTING ─────────────────────────────────────

    def to_prompt_section(self, ctx: AggregatedContext) -> str:
        """Format an AggregatedContext as a prompt section."""
        parts = []
        parts.append(f"--- Previous Step: {ctx.source_agent} (step {ctx.step_index}) ---")

        if ctx.raw_summary:
            parts.append(f"Summary: {ctx.raw_summary}")

        if ctx.key_facts:
            parts.append("\nKey Facts:")
            for fact in ctx.key_facts:
                parts.append(f"- {fact}")

        if ctx.artifacts:
            parts.append("\nArtifacts:")
            for key, val in ctx.artifacts.items():
                if isinstance(val, (dict, list)):
                    val_str = json.dumps(val)[:300]
                else:
                    val_str = str(val)[:300]
                parts.append(f"- {key}: {val_str}")

        if ctx.decisions:
            parts.append("\nDecisions:")
            for d in ctx.decisions:
                parts.append(f"- {d}")

        if ctx.warnings:
            parts.append("\nWarnings:")
            for w in ctx.warnings:
                parts.append(f"- {w}")

        parts.append("---")
        return "\n".join(parts)

    # ─── LOGGING ───────────────────────────────────────────────

    def log_aggregation(self, original_size: int, compressed_size: int,
                        strategy: str, pipeline_name: str = "",
                        step_index: int = 0, agent_name: str = ""):
        """Log aggregation metrics to memories.db."""
        if not self.db_path:
            return
        try:
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            ratio = compressed_size / max(original_size, 1)
            conn = self._conn()
            conn.execute("""
                INSERT INTO aggregation_log
                (pipeline_name, step_index, agent_name, strategy_used,
                 original_chars, compressed_chars, compression_ratio,
                 key_facts_extracted, artifacts_extracted, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, 0, 0, ?)
            """, (pipeline_name, step_index, agent_name, strategy,
                  original_size, compressed_size, ratio, now))
            conn.commit()
            conn.close()
        except Exception:
            pass  # Non-critical logging failure

    # ─── METRICS ───────────────────────────────────────────────

    def get_stats(self, pipeline_name: str = "") -> dict:
        """Get aggregation statistics."""
        if not self.db_path:
            return {"total": 0}
        conn = self._conn()
        sql = "SELECT * FROM aggregation_log"
        params = []
        if pipeline_name:
            sql += " WHERE pipeline_name = ?"
            params.append(pipeline_name)
        sql += " ORDER BY timestamp DESC LIMIT 100"
        rows = conn.execute(sql, params).fetchall()
        conn.close()

        if not rows:
            return {"total": 0}

        ratios = [r["compression_ratio"] for r in rows]
        return {
            "total": len(rows),
            "avg_compression_ratio": round(sum(ratios) / len(ratios), 3),
            "best_compression": round(min(ratios), 3),
            "worst_compression": round(max(ratios), 3),
            "total_chars_saved": sum(r["original_chars"] - r["compressed_chars"] for r in rows),
        }


# ─── CLI ───────────────────────────────────────────────────────

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Aggregator v1.0")
    sub = parser.add_subparsers(dest="command")

    # stats
    p_stats = sub.add_parser("stats", help="Show aggregation statistics")
    p_stats.add_argument("--pipeline", default="")

    # test
    p_test = sub.add_parser("test", help="Test aggregation on sample text")
    p_test.add_argument("--input", required=True, help="Text or file path to aggregate")
    p_test.add_argument("--strategy", default="auto")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return

    if args.command == "stats":
        agg = Aggregator()
        stats = agg.get_stats(args.pipeline)
        print(f"Aggregation Stats:")
        for k, v in stats.items():
            print(f"  {k}: {v}")

    elif args.command == "test":
        text = args.input
        if Path(text).exists():
            text = Path(text).read_text()

        agg = Aggregator(strategy=args.strategy)
        ctx = agg.aggregate(text, {"agent": "test", "data_key": "test"})
        print(f"Strategy: {args.strategy}")
        print(f"Original: {ctx.char_count_original} chars")
        print(f"Compressed: {ctx.char_count_compressed} chars")
        print(f"Ratio: {ctx.compression_ratio:.1%}")
        print(f"\nKey facts ({len(ctx.key_facts)}):")
        for f in ctx.key_facts:
            print(f"  - {f}")
        if ctx.artifacts:
            print(f"\nArtifacts: {list(ctx.artifacts.keys())}")
        if ctx.decisions:
            print(f"\nDecisions ({len(ctx.decisions)}):")
            for d in ctx.decisions:
                print(f"  - {d}")
        if ctx.warnings:
            print(f"\nWarnings ({len(ctx.warnings)}):")
            for w in ctx.warnings:
                print(f"  - {w}")
        print(f"\n--- Prompt Section ---")
        print(agg.to_prompt_section(ctx))


if __name__ == "__main__":
    main()
