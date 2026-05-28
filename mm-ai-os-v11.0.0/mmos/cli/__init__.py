"""Command-line interface package for MM-AI OS 7.4.0-candidate-official-split."""

from .main import main
from .parser import build_parser

__all__ = ["build_parser", "main"]
