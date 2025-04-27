#!/usr/bin/env python3
"""
Setup-Skript für TeddyCloudStarter
"""

import os
from setuptools import setup, find_packages
with open(os.path.join('TeddyCloudStarter', '__init__.py'), 'r') as f:
    for line in f:
        if line.startswith('__version__'):
            version = line.split('=')[1].strip().strip("'\"")
            break

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="TeddyCloudStarter",
    version=version,
    author="Quentendo64",
    author_email="quentin@wohlfeil.at",
    description="Ein OS-unabhängiger Setup-Wizard für TeddyCloud mit Docker",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/quentendo64/TeddyCloudStarter",
    packages=find_packages(),
    include_package_data=True,
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
        "Operating System :: OS Independent",
        "Environment :: Console",
        "Topic :: System :: Installation/Setup",
        "Topic :: System :: Systems Administration",
    ],
    python_requires=">=3.6",
    install_requires=[
        "rich>=14.0.0",
        "questionary>=2.1.0",
        "jinja2>=3.1.6",
        "dnspython>=2.7.0",
    ],
    entry_points={
        "console_scripts": [
            "TeddyCloudStarter=TeddyCloudStarter.main:main",
        ],
    },
)