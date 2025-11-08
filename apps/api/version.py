"""Application version helpers."""
from importlib import metadata

__all__ = ["__version__"]

try:
    __version__ = metadata.version("plotterstudio")
except metadata.PackageNotFoundError:
    __version__ = "0.1.0"
