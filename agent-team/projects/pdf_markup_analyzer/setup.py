#!/usr/bin/env python3
"""Setup script for PDF Markup Analyzer."""

from setuptools import setup, find_packages
from pathlib import Path

# Read README if it exists
readme_path = Path(__file__).parent / "README.md"
long_description = ""
if readme_path.exists():
    long_description = readme_path.read_text(encoding="utf-8")

setup(
    name="pdf_markup_analyzer",
    version="1.0.0",
    author="Agent Team",
    description="Extract, categorize, and convert PDF markups to actionable tasks",
    long_description=long_description,
    long_description_content_type="text/markdown",
    packages=find_packages(),
    python_requires=">=3.8",
    install_requires=[
        # No required dependencies - uses standard library
    ],
    extras_require={
        "pdf": ["PyMuPDF>=1.23.0"],
        "dev": ["pytest", "black", "mypy"],
    },
    entry_points={
        "console_scripts": [
            "pdf-markup-analyzer=pdf_markup_analyzer.main:main",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Office/Business :: Office Suites",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
)
