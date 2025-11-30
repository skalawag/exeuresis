"""Output writers for different formats (text, JSON, JSONL)."""

import json
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from exeuresis.formatter import OutputStyle, TextFormatter


class OutputWriter(ABC):
    """Base class for output format writers."""

    @abstractmethod
    def format(
        self, segments: List[Dict[str, Any]], metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Format segments into output string.

        Args:
            segments: List of segment dictionaries
            metadata: Optional metadata dictionary

        Returns:
            Formatted output string
        """
        pass


class TextWriter(OutputWriter):
    """Text format writer (wraps existing TextFormatter)."""

    def __init__(
        self,
        style: OutputStyle,
        wrap_width: Optional[int] = 79,
        extractor=None,
        parser=None,
    ):
        """
        Initialize TextWriter.

        Args:
            style: Output style for formatting
            wrap_width: Width for text wrapping (None for no wrapping)
            extractor: Optional TextExtractor instance
            parser: Optional TEIParser instance
        """
        self.style = style
        self.wrap_width = wrap_width
        self.extractor = extractor
        self.parser = parser

    def format(
        self, segments: List[Dict[str, Any]], metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Format segments as text using TextFormatter.

        Args:
            segments: List of segment dictionaries
            metadata: Optional metadata (not used for text format)

        Returns:
            Formatted text string
        """
        formatter = TextFormatter(
            segments,
            extractor=self.extractor,
            parser=self.parser,
            wrap_width=self.wrap_width,
        )
        return formatter.format(self.style)


class JSONWriter(OutputWriter):
    """JSON array format writer with metadata wrapper."""

    def format(
        self, segments: List[Dict[str, Any]], metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Format segments as JSON with metadata wrapper.

        Args:
            segments: List of segment dictionaries
            metadata: Optional metadata dictionary

        Returns:
            JSON string with metadata and segments
        """
        output = {"metadata": metadata or {}, "segments": segments}

        return json.dumps(output, ensure_ascii=False, indent=2)


class JSONLWriter(OutputWriter):
    """JSONL (newline-delimited JSON) format writer."""

    def format(
        self, segments: List[Dict[str, Any]], metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Format segments as JSONL (one JSON object per line).

        Args:
            segments: List of segment dictionaries
            metadata: Optional metadata (ignored for JSONL format)

        Returns:
            JSONL string with one segment per line
        """
        if not segments:
            return ""

        lines = [json.dumps(seg, ensure_ascii=False) for seg in segments]
        return "\n".join(lines)
