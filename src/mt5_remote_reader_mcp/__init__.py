from importlib.metadata import version as _pkg_version
from .server import mcp, main

__version__ = _pkg_version("mt5-remote-reader-mcp")

__all__ = ["mcp", "main", "__version__"]
