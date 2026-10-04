"""Exception hierarchy. The CLI catches CsvToolError and turns it into a clean message."""

from __future__ import annotations


class CsvToolError(Exception):
    """Base class for all expected, user-facing errors."""


class ConfigError(CsvToolError):
    """The configuration file is missing, unreadable or invalid."""


class ReaderError(CsvToolError):
    """The input file is missing, unreadable, empty or malformed."""


class ExportError(CsvToolError):
    """An output file could not be written."""
