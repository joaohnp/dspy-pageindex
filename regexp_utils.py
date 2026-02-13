"""Regex utilities for pattern detection and text cleaning."""

import re
from typing import List, Optional, Tuple


def clean_toc_dots(text: str) -> str:
    """
    Transform TOC dots (......) to colons (::) for easier parsing.

    Example:
        "Introduction.......1" -> "Introduction::1"
        "Chapter 1 . . . . . . 5" -> "Chapter 1::5"
    """
    # Pattern 1: 5+ consecutive dots
    text = re.sub(r"\.{5,}", "::", text)

    # Pattern 2: Dots separated by spaces (e.g., ". . . . .")
    text = re.sub(r"(?:\.\s*){5,}\.?", "::", text)

    return text


def extract_page_number_from_toc_line(line: str) -> Optional[int]:
    """
    Extract page number from end of TOC line.

    Args:
        line: TOC line that may end with page number

    Returns:
        Page number if found, None otherwise
    """
    # Pattern: number at end of line, optionally after :: or spaces
    patterns = [
        r"::\s*(\d+)\s*$",  # After :: separator
        r"\s+(\d+)\s*$",  # Simple number at end
        r"\.{2,}\s*(\d+)\s*$",  # After dots
        r"\s*-\s*(\d+)\s*$",  # After dash
        r"\s+(\d{1,4})\s*$",  # Up to 4 digits at end
    ]

    for pattern in patterns:
        match = re.search(pattern, line)
        if match:
            try:
                num = int(match.group(1))
                # Sanity check: page numbers between 1 and 9999
                if 1 <= num <= 9999:
                    return num
            except ValueError:
                continue

    return None


def extract_toc_entries(text: str) -> List[Tuple[str, Optional[int]]]:
    """
    Extract TOC entries with their page numbers from TOC text.

    Args:
        text: Full TOC text

    Returns:
        List of tuples (title, page_number)
    """
    entries = []
    lines = text.strip().split("\n")

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Clean dots first
        cleaned = clean_toc_dots(line)

        # Try to extract page number
        page_num = extract_page_number_from_toc_line(cleaned)

        # Remove page number from title
        if page_num is not None:
            # Remove the number and any separators
            title = re.sub(r"::\s*\d+\s*$", "", cleaned)
            title = re.sub(r"\s+\d+\s*$", "", title)
            title = title.strip()
        else:
            title = cleaned.strip()

        # Skip empty or very short entries
        if len(title) > 2:
            entries.append((title, page_num))

    return entries


def detect_indentation_level(line: str) -> int:
    """
    Detect indentation level based on leading whitespace.

    Args:
        line: A single line of text

    Returns:
        Indentation level (0 = no indent, 1 = 2-4 spaces, 2 = 4-8 spaces, etc.)
    """
    leading_spaces = len(line) - len(line.lstrip())
    # Group by 4-space increments
    return leading_spaces // 4


def extract_markdown_headers(text: str) -> List[Tuple[int, str]]:
    """
    Extract headers from markdown text.

    Args:
        text: Markdown text

    Returns:
        List of tuples (level, title) where level is 1-6
    """
    headers = []
    pattern = r"^(#{1,6})\s+(.+)$"

    for line in text.split("\n"):
        match = re.match(pattern, line.strip())
        if match:
            level = len(match.group(1))
            title = match.group(2).strip()
            headers.append((level, title))

    return headers


def sanitize_json_string(text: str) -> str:
    """
    Clean and sanitize text that should be valid JSON.

    Args:
        text: Potentially malformed JSON string

    Returns:
        Cleaned text
    """
    # Remove control characters except newline and tab
    text = re.sub(r"[\x00-\x08\x0b-\x0c\x0e-\x1f]", "", text)

    # Escape unescaped quotes within the content
    # This is tricky - we try to fix common issues

    # Remove trailing commas before closing brackets
    text = re.sub(r",(\s*[}\]])", r"\1", text)

    return text.strip()


def extract_json_from_text(text: str) -> Optional[str]:
    """
    Extract JSON object/array from text that may contain other content.

    Args:
        text: Text that may contain JSON

    Returns:
        Extracted JSON string or None
    """
    # Try to find JSON object
    patterns = [
        r"\{[\s\S]*\}",  # JSON object
        r"\[[\s\S]*\]",  # JSON array
    ]

    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(0)

    return None


def is_likely_toc_page(text: str) -> bool:
    """
    Quick heuristic check if text looks like a TOC page.

    This is a fast, non-LLM check for obvious TOC patterns.

    Args:
        text: Page text

    Returns:
        True if text has TOC-like patterns
    """
    lines = text.split("\n")

    # Check for TOC-related words
    toc_keywords = ["table of contents", "contents", "index", "chapter"]
    text_lower = text.lower()

    if any(keyword in text_lower for keyword in toc_keywords):
        return True

    # Check for dotted lines pattern (common in TOCs)
    dot_pattern_count = 0
    for line in lines:
        if re.search(r"\.{3,}", line):
            dot_pattern_count += 1

    # If many lines have dots, likely TOC
    if dot_pattern_count >= 5:
        return True

    # Check for lines ending with numbers (page references)
    page_ref_count = 0
    for line in lines:
        if re.search(r"\s\d+\s*$", line):
            page_ref_count += 1

    # If many lines end with numbers, likely TOC
    if page_ref_count >= 5:
        return True

    return False


def extract_chapter_number(title: str) -> Optional[int]:
    """
    Extract chapter/section number from title.

    Args:
        title: Section title

    Returns:
        Chapter/section number if found
    """
    # Pattern: "Chapter 1", "1.", "1.1", "1.1.1", etc.
    patterns = [
        r"(?:chapter|section)\s+(\d+)",
        r"^(\d+)\.[\s\t]",
        r"^(\d+)\.\d+",
        r"^(\d+)$",
    ]

    for pattern in patterns:
        match = re.search(pattern, title, re.IGNORECASE)
        if match:
            try:
                return int(match.group(1))
            except ValueError:
                continue

    return None


def normalize_whitespace(text: str) -> str:
    """Normalize whitespace in text."""
    # Replace multiple spaces with single space
    text = re.sub(r" +", " ", text)
    # Replace multiple newlines with double newline
    text = re.sub(r"\n\s*\n", "\n\n", text)
    return text.strip()


def remove_page_numbers_from_text(text: str) -> str:
    """
    Remove standalone page numbers from text.
    Useful for cleaning extracted text.

    Args:
        text: Text that may contain page numbers

    Returns:
        Text with page numbers removed
    """
    # Remove lines that are just numbers (page numbers)
    lines = text.split("\n")
    cleaned_lines = []

    for line in lines:
        stripped = line.strip()
        # Skip if line is just a number (1-4 digits)
        if re.match(r"^\d{1,4}$", stripped):
            continue
        cleaned_lines.append(line)

    return "\n".join(cleaned_lines)
