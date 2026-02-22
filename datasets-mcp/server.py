#!/usr/bin/env python3
"""
HuggingFace Datasets MCP Server - Search, Explore, Preview & Download

Provides tools to search and interact with HuggingFace Hub datasets.
Uses the HuggingFace Hub REST API and the datasets library.

Tools:
1. search_datasets - Search HuggingFace Hub for datasets
2. get_dataset_info - Get detailed info about a specific dataset
3. list_dataset_files - List files in a dataset repo
4. get_dataset_splits - Get available splits and their sizes
5. preview_dataset - Stream first N rows to preview content
6. download_dataset - Download a dataset to local storage
7. find_similar_datasets - Find datasets similar to a given one
8. search_for_training_data - Smart search for ML training data
"""

import json
import sys
import os
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

# MCP SDK
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

import requests

# Paths
SCRIPT_DIR = Path(__file__).parent
DATA_DIR = SCRIPT_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

# HuggingFace API
HF_API_BASE = "https://huggingface.co/api"
HF_TOKEN = os.environ.get("HF_TOKEN", "")

# Initialize MCP server
server = Server("datasets-mcp")

# Cache for API calls (reduce rate limiting)
_cache: dict[str, tuple[Any, float]] = {}
CACHE_DURATION = 900  # 15 minutes


def _get_headers() -> dict[str, str]:
    """Get request headers, including auth if HF_TOKEN is set."""
    headers = {"Accept": "application/json"}
    if HF_TOKEN:
        headers["Authorization"] = f"Bearer {HF_TOKEN}"
    return headers


def get_cached(key: str, fetch_func, duration: int = CACHE_DURATION):
    """Simple cache to avoid hitting rate limits."""
    now = datetime.now().timestamp()
    if key in _cache:
        data, timestamp = _cache[key]
        if now - timestamp < duration:
            return data
    data = fetch_func()
    _cache[key] = (data, now)
    return data


def _format_size(size_bytes: Optional[int]) -> str:
    """Format byte size to human-readable string."""
    if size_bytes is None:
        return "unknown"
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if abs(size_bytes) < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} PB"


def _format_number(n: Optional[int]) -> str:
    """Format large numbers with commas."""
    if n is None:
        return "N/A"
    return f"{n:,}"


# ============== API FUNCTIONS ==============

def _search_datasets_api(query: str, limit: int = 10, sort: str = "downloads",
                         task: Optional[str] = None) -> list[dict]:
    """Search HuggingFace Hub for datasets."""
    params = {
        "search": query,
        "limit": limit,
        "sort": sort,
        "direction": "-1",  # descending
    }
    if task:
        params["filter"] = f"task_categories:{task}"

    def fetch():
        resp = requests.get(f"{HF_API_BASE}/datasets", params=params,
                            headers=_get_headers(), timeout=30)
        resp.raise_for_status()
        return resp.json()

    cache_key = f"search:{query}:{limit}:{sort}:{task}"
    return get_cached(cache_key, fetch)


def _get_dataset_info_api(dataset_id: str) -> dict:
    """Get detailed info about a specific dataset."""
    def fetch():
        resp = requests.get(f"{HF_API_BASE}/datasets/{dataset_id}",
                            headers=_get_headers(), timeout=30)
        resp.raise_for_status()
        return resp.json()

    cache_key = f"info:{dataset_id}"
    return get_cached(cache_key, fetch)


def _list_dataset_files_api(dataset_id: str, path: str = "") -> list[dict]:
    """List files in a dataset repository."""
    def fetch():
        url = f"{HF_API_BASE}/datasets/{dataset_id}/tree/main"
        if path:
            url += f"/{path}"
        resp = requests.get(url, headers=_get_headers(), timeout=30)
        resp.raise_for_status()
        return resp.json()

    cache_key = f"files:{dataset_id}:{path}"
    return get_cached(cache_key, fetch)


def _get_dataset_readme(dataset_id: str) -> str:
    """Get the README content for a dataset."""
    def fetch():
        url = f"https://huggingface.co/datasets/{dataset_id}/resolve/main/README.md"
        resp = requests.get(url, headers=_get_headers(), timeout=30)
        if resp.status_code == 200:
            return resp.text
        return ""

    cache_key = f"readme:{dataset_id}"
    return get_cached(cache_key, fetch)


# ============== TOOL IMPLEMENTATIONS ==============

def _do_search_datasets(arguments: dict) -> str:
    """Search HuggingFace Hub for datasets."""
    query = arguments.get("query", "")
    limit = min(arguments.get("limit", 10), 50)
    sort = arguments.get("sort", "downloads")
    task = arguments.get("task")

    if not query:
        return json.dumps({"error": "query parameter is required"}, indent=2)

    results = _search_datasets_api(query, limit, sort, task)

    datasets_list = []
    for ds in results:
        ds_entry = {
            "id": ds.get("id", ""),
            "description": (ds.get("description") or "")[:200],
            "downloads": _format_number(ds.get("downloads")),
            "likes": ds.get("likes", 0),
            "tags": ds.get("tags", [])[:10],
            "task_categories": [t.replace("task_categories:", "")
                                for t in ds.get("tags", [])
                                if t.startswith("task_categories:")],
            "last_modified": ds.get("lastModified", ""),
            "private": ds.get("private", False),
        }
        datasets_list.append(ds_entry)

    output = {
        "query": query,
        "sort": sort,
        "task_filter": task,
        "count": len(datasets_list),
        "datasets": datasets_list,
    }
    return json.dumps(output, indent=2)


def _do_get_dataset_info(arguments: dict) -> str:
    """Get detailed info about a specific dataset."""
    dataset_id = arguments.get("dataset_id", "")
    if not dataset_id:
        return json.dumps({"error": "dataset_id parameter is required"}, indent=2)

    info = _get_dataset_info_api(dataset_id)

    # Extract card data
    card_data = info.get("cardData", {}) or {}

    # Try to get README excerpt
    readme = _get_dataset_readme(dataset_id)
    readme_excerpt = ""
    if readme:
        # Get first 500 chars after YAML frontmatter
        parts = readme.split("---")
        if len(parts) >= 3:
            readme_excerpt = parts[2].strip()[:500]
        else:
            readme_excerpt = readme[:500]

    result = {
        "id": info.get("id", ""),
        "author": info.get("author", ""),
        "description": info.get("description", ""),
        "readme_excerpt": readme_excerpt,
        "downloads": _format_number(info.get("downloads")),
        "downloads_all_time": _format_number(info.get("downloadsAllTime")),
        "likes": info.get("likes", 0),
        "tags": info.get("tags", []),
        "task_categories": [t.replace("task_categories:", "")
                            for t in info.get("tags", [])
                            if t.startswith("task_categories:")],
        "languages": [t.replace("language:", "")
                      for t in info.get("tags", [])
                      if t.startswith("language:")],
        "license": card_data.get("license", "unknown"),
        "size_categories": [t.replace("size_categories:", "")
                            for t in info.get("tags", [])
                            if t.startswith("size_categories:")],
        "created_at": info.get("createdAt", ""),
        "last_modified": info.get("lastModified", ""),
        "private": info.get("private", False),
        "gated": info.get("gated", False),
        "citation": card_data.get("citation", ""),
    }

    # Try to get split info from card data
    if "dataset_info" in card_data:
        ds_info = card_data["dataset_info"]
        if isinstance(ds_info, list) and ds_info:
            ds_info = ds_info[0]
        if isinstance(ds_info, dict):
            splits = ds_info.get("splits", [])
            if splits:
                result["splits"] = [
                    {
                        "name": s.get("name", ""),
                        "num_examples": _format_number(s.get("num_examples")),
                        "num_bytes": _format_size(s.get("num_bytes")),
                    }
                    for s in splits
                ]
            features = ds_info.get("features", [])
            if features:
                result["features"] = [
                    {
                        "name": f.get("name", ""),
                        "type": str(f.get("dtype", f.get("_type", "unknown"))),
                    }
                    for f in features[:20]
                ]

    return json.dumps(result, indent=2)


def _do_list_dataset_files(arguments: dict) -> str:
    """List files in a dataset repository."""
    dataset_id = arguments.get("dataset_id", "")
    path = arguments.get("path", "")

    if not dataset_id:
        return json.dumps({"error": "dataset_id parameter is required"}, indent=2)

    files = _list_dataset_files_api(dataset_id, path)

    file_list = []
    for f in files:
        entry = {
            "name": f.get("path", ""),
            "type": f.get("type", ""),
            "size": _format_size(f.get("size")),
        }
        if f.get("lfs"):
            entry["lfs"] = True
            entry["lfs_size"] = _format_size(f["lfs"].get("size"))
        file_list.append(entry)

    result = {
        "dataset_id": dataset_id,
        "path": path or "/",
        "file_count": len(file_list),
        "files": file_list,
    }
    return json.dumps(result, indent=2)


def _do_get_dataset_splits(arguments: dict) -> str:
    """Get available splits and their sizes."""
    dataset_id = arguments.get("dataset_id", "")
    config = arguments.get("config")

    if not dataset_id:
        return json.dumps({"error": "dataset_id parameter is required"}, indent=2)

    # First try from API info (card data)
    info = _get_dataset_info_api(dataset_id)
    card_data = info.get("cardData", {}) or {}

    splits_result = []
    configs_list = []

    if "dataset_info" in card_data:
        ds_info_list = card_data["dataset_info"]
        if not isinstance(ds_info_list, list):
            ds_info_list = [ds_info_list]

        for ds_info in ds_info_list:
            if not isinstance(ds_info, dict):
                continue
            cfg_name = ds_info.get("config_name", "default")
            configs_list.append(cfg_name)

            if config and cfg_name != config:
                continue

            splits = ds_info.get("splits", [])
            for s in splits:
                splits_result.append({
                    "config": cfg_name,
                    "split": s.get("name", ""),
                    "num_examples": _format_number(s.get("num_examples")),
                    "num_bytes": _format_size(s.get("num_bytes")),
                })

    # Fallback: try the datasets library
    if not splits_result:
        try:
            from datasets import get_dataset_config_names, get_dataset_split_names

            configs = get_dataset_config_names(dataset_id, token=HF_TOKEN or None)
            configs_list = configs

            target_configs = [config] if config else configs[:5]  # limit to 5 configs
            for cfg in target_configs:
                try:
                    split_names = get_dataset_split_names(dataset_id, cfg,
                                                          token=HF_TOKEN or None)
                    for s in split_names:
                        splits_result.append({
                            "config": cfg,
                            "split": s,
                            "num_examples": "N/A (use preview_dataset to check)",
                            "num_bytes": "N/A",
                        })
                except Exception:
                    pass
        except ImportError:
            splits_result = [{"error": "Could not determine splits. Install 'datasets' library for fallback."}]
        except Exception as e:
            splits_result = [{"note": f"Could not determine splits: {str(e)}"}]

    result = {
        "dataset_id": dataset_id,
        "available_configs": configs_list,
        "requested_config": config,
        "splits": splits_result,
    }
    return json.dumps(result, indent=2)


def _do_preview_dataset(arguments: dict) -> str:
    """Stream first N rows of a dataset to preview content."""
    dataset_id = arguments.get("dataset_id", "")
    split = arguments.get("split", "train")
    rows = min(arguments.get("rows", 5), 20)  # cap at 20
    config = arguments.get("config")

    if not dataset_id:
        return json.dumps({"error": "dataset_id parameter is required"}, indent=2)

    # Try the HF datasets viewer API first (no library needed)
    try:
        params = {
            "dataset": dataset_id,
            "split": split,
            "offset": 0,
            "length": rows,
        }
        if config:
            params["config"] = config

        resp = requests.get(
            "https://datasets-server.huggingface.co/rows",
            params=params,
            headers=_get_headers(),
            timeout=30,
        )

        if resp.status_code == 200:
            data = resp.json()
            features = data.get("features", [])
            row_data = data.get("rows", [])

            feature_names = [f.get("name", "") for f in features]
            feature_types = [str(f.get("type", {}).get("dtype",
                                f.get("type", {}).get("_type", "unknown")))
                             for f in features]

            formatted_rows = []
            for i, row_entry in enumerate(row_data):
                row = row_entry.get("row", {})
                formatted_row = {}
                for key, value in row.items():
                    # Truncate long values for preview
                    str_val = str(value)
                    if len(str_val) > 200:
                        str_val = str_val[:200] + "..."
                    formatted_row[key] = str_val
                formatted_rows.append(formatted_row)

            result = {
                "dataset_id": dataset_id,
                "split": split,
                "config": config,
                "num_rows_shown": len(formatted_rows),
                "features": [{"name": n, "type": t}
                             for n, t in zip(feature_names, feature_types)],
                "rows": formatted_rows,
            }
            return json.dumps(result, indent=2, default=str)

    except Exception:
        pass

    # Fallback: use datasets library with streaming
    try:
        from datasets import load_dataset

        kwargs = {
            "path": dataset_id,
            "split": split,
            "streaming": True,
            "token": HF_TOKEN or None,
        }
        if config:
            kwargs["name"] = config

        ds = load_dataset(**kwargs)
        rows_list = list(ds.take(rows))

        formatted_rows = []
        for row in rows_list:
            formatted_row = {}
            for key, value in row.items():
                str_val = str(value)
                if len(str_val) > 200:
                    str_val = str_val[:200] + "..."
                formatted_row[key] = str_val
            formatted_rows.append(formatted_row)

        result = {
            "dataset_id": dataset_id,
            "split": split,
            "config": config,
            "num_rows_shown": len(formatted_rows),
            "rows": formatted_rows,
        }
        return json.dumps(result, indent=2, default=str)

    except ImportError:
        return json.dumps({
            "error": "Could not preview dataset. Install 'datasets' library.",
            "hint": "pip install datasets"
        }, indent=2)
    except Exception as e:
        return json.dumps({
            "error": f"Could not preview dataset: {str(e)}",
            "dataset_id": dataset_id,
            "split": split,
        }, indent=2)


def _do_download_dataset(arguments: dict) -> str:
    """Download a dataset to local storage."""
    dataset_id = arguments.get("dataset_id", "")
    split = arguments.get("split")
    config = arguments.get("config")
    output_dir = arguments.get("output_dir", str(DATA_DIR))

    if not dataset_id:
        return json.dumps({"error": "dataset_id parameter is required"}, indent=2)

    try:
        from datasets import load_dataset

        # Create output directory
        out_path = Path(output_dir)
        out_path.mkdir(parents=True, exist_ok=True)

        # Safe directory name from dataset_id
        safe_name = dataset_id.replace("/", "__")
        dataset_dir = out_path / safe_name

        kwargs = {
            "path": dataset_id,
            "token": HF_TOKEN or None,
        }
        if config:
            kwargs["name"] = config
        if split:
            kwargs["split"] = split

        ds = load_dataset(**kwargs)

        # Save to disk
        ds.save_to_disk(str(dataset_dir))

        # Calculate size
        total_size = sum(
            f.stat().st_size for f in dataset_dir.rglob("*") if f.is_file()
        )

        result = {
            "status": "downloaded",
            "dataset_id": dataset_id,
            "config": config,
            "split": split,
            "output_path": str(dataset_dir),
            "total_size": _format_size(total_size),
        }

        # Add info about what was downloaded
        if hasattr(ds, "num_rows"):
            result["num_rows"] = _format_number(ds.num_rows)
        elif hasattr(ds, "keys"):
            # DatasetDict
            result["splits_downloaded"] = {
                k: _format_number(v.num_rows) for k, v in ds.items()
            }

        return json.dumps(result, indent=2)

    except ImportError:
        return json.dumps({
            "error": "The 'datasets' library is required for downloading. Install with: pip install datasets",
        }, indent=2)
    except Exception as e:
        return json.dumps({
            "error": f"Download failed: {str(e)}",
            "dataset_id": dataset_id,
        }, indent=2)


def _do_find_similar_datasets(arguments: dict) -> str:
    """Find datasets similar to a given one by tags/task."""
    dataset_id = arguments.get("dataset_id", "")
    limit = min(arguments.get("limit", 5), 20)

    if not dataset_id:
        return json.dumps({"error": "dataset_id parameter is required"}, indent=2)

    # Get info about the source dataset
    info = _get_dataset_info_api(dataset_id)
    tags = info.get("tags", [])

    # Extract task categories and key tags
    task_categories = [t.replace("task_categories:", "")
                       for t in tags if t.startswith("task_categories:")]
    languages = [t.replace("language:", "")
                 for t in tags if t.startswith("language:")]

    similar_datasets = []
    seen_ids = {dataset_id}

    # Search by task categories
    for task in task_categories[:2]:
        try:
            results = _search_datasets_api("", limit=limit + 5, sort="downloads",
                                           task=task)
            for ds in results:
                ds_id = ds.get("id", "")
                if ds_id not in seen_ids:
                    seen_ids.add(ds_id)
                    similar_datasets.append({
                        "id": ds_id,
                        "description": (ds.get("description") or "")[:150],
                        "downloads": _format_number(ds.get("downloads")),
                        "likes": ds.get("likes", 0),
                        "matched_on": f"task:{task}",
                        "tags": ds.get("tags", [])[:8],
                    })
        except Exception:
            pass

    # Also search by dataset name keywords
    name_parts = dataset_id.split("/")[-1].split("-")
    for keyword in name_parts[:2]:
        if len(keyword) < 3:
            continue
        try:
            results = _search_datasets_api(keyword, limit=5, sort="downloads")
            for ds in results:
                ds_id = ds.get("id", "")
                if ds_id not in seen_ids:
                    seen_ids.add(ds_id)
                    similar_datasets.append({
                        "id": ds_id,
                        "description": (ds.get("description") or "")[:150],
                        "downloads": _format_number(ds.get("downloads")),
                        "likes": ds.get("likes", 0),
                        "matched_on": f"keyword:{keyword}",
                        "tags": ds.get("tags", [])[:8],
                    })
        except Exception:
            pass

    # Sort by downloads and limit
    similar_datasets.sort(
        key=lambda x: int(x["downloads"].replace(",", "").replace("N/A", "0")),
        reverse=True
    )
    similar_datasets = similar_datasets[:limit]

    result = {
        "source_dataset": dataset_id,
        "source_tasks": task_categories,
        "source_languages": languages,
        "similar_count": len(similar_datasets),
        "similar_datasets": similar_datasets,
    }
    return json.dumps(result, indent=2)


def _do_search_for_training_data(arguments: dict) -> str:
    """Smart search specifically for ML training data."""
    task = arguments.get("task", "")
    data_type = arguments.get("data_type")
    min_downloads = arguments.get("min_downloads", 100)

    if not task:
        return json.dumps({"error": "task parameter is required"}, indent=2)

    # Map common task descriptions to HuggingFace task categories
    task_mapping = {
        "object detection": "object-detection",
        "image classification": "image-classification",
        "image segmentation": "image-segmentation",
        "text classification": "text-classification",
        "text generation": "text-generation",
        "question answering": "question-answering",
        "translation": "translation",
        "summarization": "summarization",
        "sentiment analysis": "text-classification",
        "named entity recognition": "token-classification",
        "ner": "token-classification",
        "speech recognition": "automatic-speech-recognition",
        "asr": "automatic-speech-recognition",
        "text to speech": "text-to-speech",
        "tts": "text-to-speech",
        "fill mask": "fill-mask",
        "zero shot": "zero-shot-classification",
        "image to text": "image-to-text",
        "visual question answering": "visual-question-answering",
        "document question answering": "document-question-answering",
        "depth estimation": "depth-estimation",
        "video classification": "video-classification",
        "reinforcement learning": "reinforcement-learning",
        "tabular classification": "tabular-classification",
        "tabular regression": "tabular-regression",
        "feature extraction": "feature-extraction",
        "conversational": "conversational",
        "table question answering": "table-question-answering",
    }

    # Try to find matching HF task category
    task_lower = task.lower().strip()
    hf_task = task_mapping.get(task_lower)

    # Search strategies
    all_results = []
    seen_ids = set()

    # Strategy 1: Search by HF task category if mapped
    if hf_task:
        try:
            results = _search_datasets_api("", limit=20, sort="downloads", task=hf_task)
            for ds in results:
                ds_id = ds.get("id", "")
                if ds_id not in seen_ids:
                    seen_ids.add(ds_id)
                    all_results.append(ds)
        except Exception:
            pass

    # Strategy 2: Keyword search
    try:
        results = _search_datasets_api(task, limit=20, sort="downloads")
        for ds in results:
            ds_id = ds.get("id", "")
            if ds_id not in seen_ids:
                seen_ids.add(ds_id)
                all_results.append(ds)
    except Exception:
        pass

    # Strategy 3: If data_type specified, search with it
    if data_type:
        try:
            search_query = f"{task} {data_type}"
            results = _search_datasets_api(search_query, limit=10, sort="downloads")
            for ds in results:
                ds_id = ds.get("id", "")
                if ds_id not in seen_ids:
                    seen_ids.add(ds_id)
                    all_results.append(ds)
        except Exception:
            pass

    # Filter by minimum downloads
    filtered = []
    for ds in all_results:
        downloads = ds.get("downloads", 0)
        if downloads >= min_downloads:
            ds_tags = ds.get("tags", [])
            entry = {
                "id": ds.get("id", ""),
                "description": (ds.get("description") or "")[:200],
                "downloads": _format_number(downloads),
                "likes": ds.get("likes", 0),
                "task_categories": [t.replace("task_categories:", "")
                                    for t in ds_tags
                                    if t.startswith("task_categories:")],
                "size_categories": [t.replace("size_categories:", "")
                                    for t in ds_tags
                                    if t.startswith("size_categories:")],
                "languages": [t.replace("language:", "")
                              for t in ds_tags
                              if t.startswith("language:")][:3],
                "license": next((t.replace("license:", "")
                                 for t in ds_tags
                                 if t.startswith("license:")), "unknown"),
            }
            filtered.append(entry)

    # Sort by downloads
    filtered.sort(
        key=lambda x: int(x["downloads"].replace(",", "").replace("N/A", "0")),
        reverse=True
    )
    filtered = filtered[:20]

    result = {
        "search_task": task,
        "hf_task_category": hf_task,
        "data_type_filter": data_type,
        "min_downloads": min_downloads,
        "results_count": len(filtered),
        "datasets": filtered,
        "tip": "Use get_dataset_info or preview_dataset for more details on any result.",
    }
    return json.dumps(result, indent=2)


# ============== MCP TOOL REGISTRATION ==============

@server.list_tools()
async def list_tools() -> list[Tool]:
    """List all available dataset tools."""
    return [
        Tool(
            name="search_datasets",
            description="Search HuggingFace Hub for datasets by keyword, with optional task category filter",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query (e.g., 'image segmentation', 'sentiment analysis', 'coco')"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Max results to return (default 10, max 50)",
                        "default": 10
                    },
                    "sort": {
                        "type": "string",
                        "description": "Sort by: 'downloads', 'likes', 'trending', 'created', 'modified'",
                        "default": "downloads"
                    },
                    "task": {
                        "type": "string",
                        "description": "Filter by HF task category (e.g., 'image-classification', 'object-detection', 'text-generation')"
                    },
                },
                "required": ["query"]
            }
        ),
        Tool(
            name="get_dataset_info",
            description="Get detailed information about a specific HuggingFace dataset including description, splits, features, license, citation, and size",
            inputSchema={
                "type": "object",
                "properties": {
                    "dataset_id": {
                        "type": "string",
                        "description": "Dataset identifier (e.g., 'coco', 'mozilla-foundation/common_voice_11_0', 'imdb')"
                    },
                },
                "required": ["dataset_id"]
            }
        ),
        Tool(
            name="list_dataset_files",
            description="List all files in a dataset repository on HuggingFace Hub",
            inputSchema={
                "type": "object",
                "properties": {
                    "dataset_id": {
                        "type": "string",
                        "description": "Dataset identifier (e.g., 'coco', 'squad')"
                    },
                    "path": {
                        "type": "string",
                        "description": "Subdirectory path to list (default: root)",
                        "default": ""
                    },
                },
                "required": ["dataset_id"]
            }
        ),
        Tool(
            name="get_dataset_splits",
            description="Get available splits (train, test, validation) and their sizes for a dataset",
            inputSchema={
                "type": "object",
                "properties": {
                    "dataset_id": {
                        "type": "string",
                        "description": "Dataset identifier"
                    },
                    "config": {
                        "type": "string",
                        "description": "Dataset configuration/subset name (optional)"
                    },
                },
                "required": ["dataset_id"]
            }
        ),
        Tool(
            name="preview_dataset",
            description="Preview first N rows of a dataset to inspect its content and structure without downloading",
            inputSchema={
                "type": "object",
                "properties": {
                    "dataset_id": {
                        "type": "string",
                        "description": "Dataset identifier"
                    },
                    "split": {
                        "type": "string",
                        "description": "Which split to preview (default: 'train')",
                        "default": "train"
                    },
                    "rows": {
                        "type": "integer",
                        "description": "Number of rows to preview (default 5, max 20)",
                        "default": 5
                    },
                    "config": {
                        "type": "string",
                        "description": "Dataset configuration/subset name (optional)"
                    },
                },
                "required": ["dataset_id"]
            }
        ),
        Tool(
            name="download_dataset",
            description="Download a HuggingFace dataset to local disk for offline use",
            inputSchema={
                "type": "object",
                "properties": {
                    "dataset_id": {
                        "type": "string",
                        "description": "Dataset identifier"
                    },
                    "split": {
                        "type": "string",
                        "description": "Specific split to download (optional, downloads all if omitted)"
                    },
                    "config": {
                        "type": "string",
                        "description": "Dataset configuration/subset name (optional)"
                    },
                    "output_dir": {
                        "type": "string",
                        "description": "Directory to save the dataset (default: /mnt/d/_CLAUDE-TOOLS/datasets-mcp/data)",
                        "default": "/mnt/d/_CLAUDE-TOOLS/datasets-mcp/data"
                    },
                },
                "required": ["dataset_id"]
            }
        ),
        Tool(
            name="find_similar_datasets",
            description="Find datasets similar to a given one based on shared task categories and tags",
            inputSchema={
                "type": "object",
                "properties": {
                    "dataset_id": {
                        "type": "string",
                        "description": "Source dataset identifier to find similar datasets for"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Max number of similar datasets to return (default 5)",
                        "default": 5
                    },
                },
                "required": ["dataset_id"]
            }
        ),
        Tool(
            name="search_for_training_data",
            description="Smart search for ML training datasets by task description. Maps common task names to HuggingFace categories and filters by popularity.",
            inputSchema={
                "type": "object",
                "properties": {
                    "task": {
                        "type": "string",
                        "description": "ML task description (e.g., 'object detection', 'floor plan', 'sentiment analysis', 'speech recognition')"
                    },
                    "data_type": {
                        "type": "string",
                        "description": "Type of data needed (e.g., 'image', 'text', 'audio', 'video', 'tabular')"
                    },
                    "min_downloads": {
                        "type": "integer",
                        "description": "Minimum number of downloads to filter by (default 100)",
                        "default": 100
                    },
                },
                "required": ["task"]
            }
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    """Execute dataset tools."""

    try:
        if name == "search_datasets":
            result = _do_search_datasets(arguments)

        elif name == "get_dataset_info":
            result = _do_get_dataset_info(arguments)

        elif name == "list_dataset_files":
            result = _do_list_dataset_files(arguments)

        elif name == "get_dataset_splits":
            result = _do_get_dataset_splits(arguments)

        elif name == "preview_dataset":
            result = _do_preview_dataset(arguments)

        elif name == "download_dataset":
            result = _do_download_dataset(arguments)

        elif name == "find_similar_datasets":
            result = _do_find_similar_datasets(arguments)

        elif name == "search_for_training_data":
            result = _do_search_for_training_data(arguments)

        else:
            result = json.dumps({"error": f"Unknown tool: {name}"}, indent=2)

        return [TextContent(type="text", text=result)]

    except requests.exceptions.HTTPError as e:
        error_msg = f"HuggingFace API error: {str(e)}"
        if e.response is not None:
            if e.response.status_code == 401:
                error_msg += "\nAuthentication required. Set HF_TOKEN environment variable."
            elif e.response.status_code == 404:
                error_msg += "\nDataset not found. Check the dataset_id."
            elif e.response.status_code == 429:
                error_msg += "\nRate limited. Please wait and try again."
        return [TextContent(type="text", text=json.dumps({"error": error_msg}, indent=2))]

    except requests.exceptions.ConnectionError:
        return [TextContent(type="text", text=json.dumps({
            "error": "Could not connect to HuggingFace API. Check your internet connection."
        }, indent=2))]

    except requests.exceptions.Timeout:
        return [TextContent(type="text", text=json.dumps({
            "error": "Request to HuggingFace API timed out. Try again."
        }, indent=2))]

    except Exception as e:
        return [TextContent(type="text", text=json.dumps({
            "error": f"Unexpected error: {str(e)}",
            "tool": name,
        }, indent=2))]


# ============== ENTRY POINT ==============

async def main():
    """Run the MCP server."""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
