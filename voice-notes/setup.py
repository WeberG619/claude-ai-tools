#!/usr/bin/env python3
"""
Setup script for voice-notes package.

Install with:
    pip install -e .

Or build distribution:
    python setup.py sdist bdist_wheel
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read the README for long description
readme_path = Path(__file__).parent / "README.md"
long_description = readme_path.read_text(encoding="utf-8") if readme_path.exists() else ""

# Read version from package
version = "1.0.0"

setup(
    name="voice-notes",
    version=version,
    author="Weber Gouin",
    author_email="weberg619@gmail.com",
    description="Convert audio recordings to structured meeting notes using OpenAI Whisper",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/webergouin/voice-notes",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Environment :: Console",
        "Intended Audience :: End Users/Desktop",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Multimedia :: Sound/Audio :: Speech",
        "Topic :: Office/Business",
        "Topic :: Text Processing",
    ],
    python_requires=">=3.8",
    install_requires=[
        "openai-whisper>=20231117",
        "torch>=2.0.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-cov>=4.0.0",
            "black>=23.0.0",
            "flake8>=6.0.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "voice-notes=voice_notes.cli:main",
        ],
    },
    include_package_data=True,
    zip_safe=False,
    keywords=[
        "whisper",
        "transcription",
        "speech-to-text",
        "meeting-notes",
        "audio",
        "voice",
        "cli",
    ],
    project_urls={
        "Bug Reports": "https://github.com/webergouin/voice-notes/issues",
        "Source": "https://github.com/webergouin/voice-notes",
    },
)
