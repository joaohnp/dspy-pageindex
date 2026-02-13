"""LLM utilities using DSPy signatures for TOC processing."""

from typing import Optional

import dspy
from pydantic import BaseModel, Field


class Section(BaseModel):
    """A section in the document TOC."""

    title: str = Field(description="The section or chapter title")
    level: int = Field(
        description="Hierarchy level (0 = main chapter, 1 = subsection, etc.)"
    )
    page: Optional[int] = Field(None, description="Page number if available")


class SectionWithPageIndex(BaseModel):
    """A section with assigned physical page index."""

    title: str = Field(description="The section title")
    page_index: int = Field(description="Physical page index (0-based)")
    level: int = Field(default=0, description="Hierarchy level")


class PageSample(BaseModel):
    """A sample page for LLM matching."""

    page_num: int = Field(description="Page number (0-based)")
    text: str = Field(description="Page text content (truncated)")


# ============================================================================
# DSPy Signatures
# ============================================================================


class TocDetector(dspy.Signature):
    """Determine if a PDF page contains a Table of Contents.

    A Table of Contents (TOC) typically has:
    - A header like "Table of Contents", "Contents", or "Index"
    - A list of section/chapter titles
    - Page numbers (often connected by dots like ".......... 5")
    - Hierarchical structure showing chapters, sections, and subsections
    """

    page_text: str = dspy.InputField(
        desc="Full text content extracted from a PDF page"
    )
    is_toc_page: bool = dspy.OutputField(
        desc="True if page contains a Table of Contents"
    )


class TocExtractor(dspy.Signature):
    """Extract Table of Contents content from a PDF page.

    Extract only the TOC entries - section titles and page numbers.
    Preserve the structure including indentation that shows hierarchy.
    Do not include headers, footers, or other page content.
    """

    page_text: str = dspy.InputField(
        desc="Full text content of a PDF page containing TOC"
    )
    toc_content: str = dspy.OutputField(
        desc="Clean TOC content with titles and page numbers"
    )


class TocTransformer(dspy.Signature):
    """Transform Table of Contents text into structured sections.

    Parse TOC text and create structured sections with:
    - Title: The section/chapter name
    - Level: Hierarchy level (0 = chapter, 1 = section, 2 = subsection)
    - Page: Page number if present in the TOC, null otherwise

    Infer hierarchy from:
    - Indentation levels
    - Numbering patterns (1., 1.1, 1.1.1)
    - Visual structure
    """

    toc_text: str = dspy.InputField(
        desc="Clean TOC text with titles and page numbers"
    )
    sections: list[Section] = dspy.OutputField(
        desc="Structured list of TOC sections"
    )


class PageIndexAssigner(dspy.Signature):
    """Match TOC sections to their physical page indices.

    Given TOC sections and sample pages from the document,
    find the physical page index (0-based) where each section begins.

    Match sections by looking for:
    - Exact title matches at the start of pages
    - Similar/fuzzy matches
    - Section numbers or patterns

    If a section has a 'page' number from the TOC, use it as a hint
    but verify by checking the actual page content.
    """

    toc_sections: list[Section] = dspy.InputField(
        desc="TOC sections to find in the document"
    )
    page_samples: list[PageSample] = dspy.InputField(
        desc="Sample pages for matching"
    )
    matches: list[SectionWithPageIndex] = dspy.OutputField(
        desc="Sections with assigned page indices"
    )


class TocVerifier(dspy.Signature):
    """Verify if a TOC section title appears on a given page.

    Check if the section title is present on the page, considering:
    - Exact matches
    - Fuzzy/similar matches
    - Shortened or longer variations
    - Header formatting differences
    """

    title: str = dspy.InputField(desc="Section title from the TOC")
    page_text: str = dspy.InputField(desc="Text content of the page to verify")
    is_present: bool = dspy.OutputField(
        desc="True if the title appears on this page"
    )


class TocGenerator(dspy.Signature):
    """Generate a Table of Contents from document content.

    When a PDF has no existing TOC, analyze sample pages from throughout
    the document to identify:
    - Main chapters/sections
    - Subsections
    - Document structure and hierarchy
    - Estimated page indices for each section
    """

    page_samples: list[PageSample] = dspy.InputField(
        desc="Sample pages from throughout the document"
    )
    sections: list[SectionWithPageIndex] = dspy.OutputField(
        desc="Generated sections with estimated page indices"
    )


class NodeSummarizer(dspy.Signature):
    """Generate a summary of a document section for navigation.

    Create a concise but informative paragraph (3-5 sentences) that:
    - Explains the main purpose and key concepts
    - Mentions important sub-topics covered
    - Helps users understand if this section is relevant to them
    - Uses clear, accessible language
    """

    title: str = dspy.InputField(desc="Section title")
    text: str = dspy.InputField(desc="Full text content of the section")
    summary: str = dspy.OutputField(
        desc="Full paragraph summary of the section"
    )


# ============================================================================
# Predictor Functions (instantiate at call time)
# ============================================================================


def detect_toc(page_text: str) -> bool:
    """Detect if a page contains a Table of Contents.

    Args:
        page_text: Full text content of the PDF page

    Returns:
        True if the page contains a TOC
    """
    predictor = dspy.Predict(TocDetector)
    result = predictor(page_text=page_text)
    return result.is_toc_page


def extract_toc(page_text: str) -> str:
    """Extract TOC content from a page.

    Args:
        page_text: Full text content of the PDF page

    Returns:
        Clean TOC content
    """
    predictor = dspy.Predict(TocExtractor)
    result = predictor(page_text=page_text)
    return result.toc_content


def transform_toc(toc_text: str) -> list[Section]:
    """Transform TOC text to structured sections.

    Args:
        toc_text: Clean TOC text

    Returns:
        List of structured sections
    """
    predictor = dspy.Predict(TocTransformer)
    result = predictor(toc_text=toc_text)
    return result.sections


def assign_page_indices(
    toc_sections: list[Section], page_samples: list[PageSample]
) -> list[SectionWithPageIndex]:
    """Assign physical page indices to TOC sections.

    Args:
        toc_sections: List of TOC sections
        page_samples: Sample pages for matching

    Returns:
        Sections with assigned page indices
    """
    predictor = dspy.Predict(PageIndexAssigner)
    result = predictor(toc_sections=toc_sections, page_samples=page_samples)
    return result.matches


def verify_toc_entry(title: str, page_text: str) -> bool:
    """Verify if a TOC entry appears on a page.

    Args:
        title: Section title from TOC
        page_text: Page text content

    Returns:
        True if verified
    """
    predictor = dspy.Predict(TocVerifier)
    result = predictor(title=title, page_text=page_text)
    return result.is_present


def generate_toc(page_samples: list[PageSample]) -> list[SectionWithPageIndex]:
    """Generate TOC from document content.

    Args:
        page_samples: Sample pages from throughout the document

    Returns:
        Generated sections with page indices
    """
    predictor = dspy.Predict(TocGenerator)
    result = predictor(page_samples=page_samples)
    return result.sections


def generate_summary(title: str, text: str) -> str:
    """Generate a summary for a document section.

    Args:
        title: Section title
        text: Full text content of the section

    Returns:
        Full paragraph summary of the section
    """
    predictor = dspy.Predict(NodeSummarizer)
    result = predictor(title=title, text=text)
    return result.summary
