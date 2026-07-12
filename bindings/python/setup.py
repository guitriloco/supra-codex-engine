"""
Python bindings setup.py — builds the native _wraith module via pybind11.

Run:
    pip install .
    # or for development:
    pip install -e .
"""

from setuptools import setup, Extension
from setuptools.command.build_ext import build_ext
import sys

# CFFI is a simpler option than pybind11 for the initial scaffold.
# Once the C++ API stabilizes, we'll switch to pybind11 for deeper integration.
# For now, this is a placeholder setup that installs the pure-Python reference.

setup(
    name="wraith-bindings",
    version="0.1.0",
    description="Python bindings for the WraithEngine C++ core",
    packages=["wraith"],
    package_dir={"": "."},
    python_requires=">=3.9",
    install_requires=[],
    extras_require={
        "dev": ["pytest", "pytest-asyncio"],
    },
)