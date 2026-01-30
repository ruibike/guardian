#!/usr/bin/env python3
"""Setup script for Guardian."""

from setuptools import setup, find_packages

setup(
    name="guardian",
    version="1.0.0",
    description="Agente LLM Offline para Ubuntu - Otimizado para 8GB RAM",
    author="Guardian Team",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    python_requires=">=3.9",
    install_requires=[
        "PyYAML>=6.0",
        "psutil>=5.9.0",
    ],
    extras_require={
        "gui": [
            "PyGObject>=3.44.0",
        ],
        "llm": [
            "llama-cpp-python>=0.2.50",
        ],
        "web": [
            "duckduckgo-search>=4.0",
            "requests>=2.31.0",
            "beautifulsoup4>=4.12.0",
        ],
        "full": [
            "PyGObject>=3.44.0",
            "llama-cpp-python>=0.2.50",
            "duckduckgo-search>=4.0",
            "requests>=2.31.0",
            "beautifulsoup4>=4.12.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "guardian=main:main",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Environment :: X11 Applications :: GTK",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: MIT License",
        "Operating System :: POSIX :: Linux",
        "Programming Language :: Python :: 3",
        "Topic :: Security",
        "Topic :: Utilities",
    ],
)
