"""
PyGomo - Python Gomoku Engine Communication Framework.
"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="pygomo",
    version="0.1.0",
    author="PyGomo Contributors",
    author_email="",
    description="A clean, extensible Python library for communicating with Gomoku engines via the Gomocup protocol.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/pygomo",
    packages=find_packages(exclude=["tests", "tests.*", "examples", "docs"]),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Topic :: Games/Entertainment :: Board Games",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.8",
    extras_require={
        "dev": [
            "pytest>=7.0",
            "sphinx>=7.0",
            "furo",
            "myst-parser",
            "sphinx-copybutton",
        ],
    },
    entry_points={
        "console_scripts": [
            "pygomo-console=examples.console_game:main",
        ],
    },
)
