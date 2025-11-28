"""Formatter for anthology output with multiple blocks."""

from typing import List

from exeuresis.anthology_extractor import AnthologyBlock
from exeuresis.formatter import OutputStyle, TextFormatter
from exeuresis.exceptions import InvalidStyleError


class AnthologyFormatter:
    """Format anthology blocks with headers and block separation."""

    def __init__(self, style: OutputStyle):
        """
        Initialize AnthologyFormatter.

        Args:
            style: Output style for formatting (A-D only)

        Raises:
            InvalidStyleError: If style is E or S
        """
        # Validate style
        if style == OutputStyle.SCRIPTIO_CONTINUA:
            raise InvalidStyleError(
                "E",
                "Style E (scriptio continua) is not supported for anthology extraction. "
                "Use styles A-D only."
            )
        if style == OutputStyle.STEPHANUS_LAYOUT:
            raise InvalidStyleError(
                "S",
                "Style S (Stephanus layout) is not supported for anthology extraction. "
                "Use styles A-D only."
            )

        self.style = style

    def format_blocks(self, blocks: List[AnthologyBlock]) -> str:
        """
        Format anthology blocks with headers and separation.

        Args:
            blocks: List of AnthologyBlock objects

        Returns:
            Formatted anthology text with headers and blank line separators
        """
        if not blocks:
            return ""

        output_parts = []

        for block in blocks:
            # Format header
            header = block.format_header(width=79)

            # Format block content using TextFormatter
            formatter = TextFormatter(block.segments)
            content = formatter.format(self.style)

            # Combine header and content
            block_output = f"{header}\n{content}"
            output_parts.append(block_output)

        # Join blocks with blank line separator
        return "\n\n".join(output_parts)
