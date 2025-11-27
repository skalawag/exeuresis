"""Custom exceptions for Perseus text extractor."""


class PerseusError(Exception):
    """Base exception for all Perseus-related errors."""
    pass


class WorkNotFoundError(PerseusError):
    """Raised when a work ID cannot be resolved to a file."""

    def __init__(self, work_id: str, suggestion: str = ""):
        self.work_id = work_id
        message = f"Work not found: {work_id}"
        if suggestion:
            message += f"\n{suggestion}"
        super().__init__(message)


class InvalidTEIStructureError(PerseusError):
    """Raised when a TEI XML file is missing required elements."""

    def __init__(self, xml_path: str, missing_element: str):
        self.xml_path = xml_path
        self.missing_element = missing_element
        message = f"Invalid TEI structure in {xml_path}: missing required element '{missing_element}'"
        super().__init__(message)


class EmptyExtractionError(PerseusError):
    """Raised when no text is extracted from a valid TEI file."""

    def __init__(self, xml_path: str, reason: str = ""):
        self.xml_path = xml_path
        message = f"No text extracted from {xml_path}"
        if reason:
            message += f": {reason}"
        super().__init__(message)


class InvalidStyleError(PerseusError):
    """Raised when an output style is used inappropriately."""

    def __init__(self, style: str, reason: str):
        self.style = style
        message = f"Cannot use style '{style}': {reason}"
        super().__init__(message)


class InvalidStephanusRangeError(PerseusError):
    """Raised when a requested Stephanus range doesn't exist or is invalid."""

    def __init__(self, work_id: str, range_spec: str, reason: str = ""):
        self.work_id = work_id
        self.range_spec = range_spec
        message = f"Invalid Stephanus range '{range_spec}' for work {work_id}"
        if reason:
            message += f": {reason}"
        super().__init__(message)
