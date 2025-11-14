#!/usr/bin/env python3
"""Find stray gamma characters in Perseus TEI XML files.

This script identifies potential OCR artifacts where gamma (γ) appears
at the end of text segments, often after punctuation.
"""

import sys
import re
from pathlib import Path
from lxml import etree


def find_stray_gammas(xml_path):
    """
    Find all instances of stray gamma characters in a TEI XML file.

    Args:
        xml_path: Path to the TEI XML file

    Returns:
        List of tuples (line_number, context_text)
    """
    # Parse the XML
    tree = etree.parse(str(xml_path))
    root = tree.getroot()

    # Define TEI namespace
    NS = {"tei": "http://www.tei-c.org/ns/1.0"}

    # Find all <said> elements
    said_elements = root.findall(".//tei:said", NS)

    stray_gammas = []

    for said in said_elements:
        # Get all text content
        text = "".join(said.itertext())

        # Check if text ends with gamma
        if text.strip().endswith('γ'):
            # Get some context
            context = text.strip()[-60:] if len(text.strip()) > 60 else text.strip()

            # Get line number (approximate - from source line)
            line_num = said.sourceline if hasattr(said, 'sourceline') else "unknown"

            stray_gammas.append((line_num, context))

    return stray_gammas


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python find_stray_gammas.py <xml_file>")
        print("\nExample:")
        print("  python find_stray_gammas.py canonical-greekLit/data/tlg0059/tlg001/tlg0059.tlg001.perseus-grc1.xml")
        sys.exit(1)

    xml_path = Path(sys.argv[1])

    if not xml_path.exists():
        print(f"Error: File not found: {xml_path}", file=sys.stderr)
        sys.exit(1)

    print(f"Scanning {xml_path} for stray gamma characters...\n")

    stray_gammas = find_stray_gammas(xml_path)

    if not stray_gammas:
        print("No stray gammas found!")
        return

    print(f"Found {len(stray_gammas)} stray gamma(s):\n")

    for line_num, context in stray_gammas:
        print(f"Line {line_num}:")
        print(f"  ...{context}")
        print()

    # Summary
    print(f"\nTotal: {len(stray_gammas)} stray gamma character(s) found")
    print("\nThese appear to be OCR artifacts in the source XML.")
    print("The Perseus text extractor will automatically filter these out.")


if __name__ == "__main__":
    main()
