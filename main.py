"""Main pipeline for PDF to tree structure conversion."""

import json
import time
from pathlib import Path
from typing import List, Optional, Union

import dspy
from pydantic import BaseModel, Field

from llm_utils import (
    PageSample,
    Section,
    SectionWithPageIndex,
    assign_page_indices,
    detect_toc,
    extract_toc,
    generate_toc,
    transform_toc,
)
from openrouter_utils import get_openrouter_lm
from pdf_utils import PageInfo, extract_pages
from regexp_utils import clean_toc_dots, is_likely_toc_page

# ============================================================================
# Pydantic Models (kept for return types)
# ============================================================================


class TreeNode(BaseModel):
    """Represents a node in the document tree."""

    title: str
    level: int
    start_page: Optional[int] = None
    end_page: Optional[int] = None
    node_id: Optional[str] = None
    summary: Optional[str] = None
    text: Optional[str] = None
    children: List["TreeNode"] = Field(default_factory=list)


class ProcessingResult(BaseModel):
    """Result of PDF processing."""

    doc_name: str
    total_pages: int
    structure: List[TreeNode]
    toc_pages: List[int]
    processing_time: float

    def to_json(self, indent: int = 2) -> str:
        """Convert to JSON string."""
        return json.dumps(self.model_dump(), indent=indent, ensure_ascii=False)


# ============================================================================
# Pipeline Functions
# ============================================================================


def process_pdf(
    pdf_path: Union[Path, str],
    max_toc_check_pages: int = 20,
    max_pages_per_node: int = 10,
    add_node_ids: bool = True,
    add_summaries: bool = False,
    add_text: bool = False,
) -> ProcessingResult:
    """
    Process a PDF file and return hierarchical tree structure.

    This is the main entry point for the pipeline.

    Args:
        pdf_path: Path to PDF file
        max_toc_check_pages: Maximum number of pages to check for TOC
        max_pages_per_node: Maximum pages per tree node
        add_node_ids: Add sequential node IDs to tree
        add_summaries: Generate node summaries (LLM call per node)
        add_text: Include full text in output

    Returns:
        ProcessingResult with tree structure

    Example:
        >>> result = process_pdf("document.pdf")
        >>> print(result.to_json())
    """
    # Configure LLM
    lm = get_openrouter_lm("openrouter/openrouter/aurora-alpha")
    dspy.settings.configure(lm=lm)

    pdf_path = Path(pdf_path)
    start_time = time.time()

    # Step 1: Extract pages
    print(f"Extracting pages from {pdf_path.name}...")
    pages = extract_pages(pdf_path)
    total_pages = len(pages)
    print(f"  Extracted {total_pages} pages")

    # Step 2: Detect TOC pages
    print("Detecting Table of Contents pages...")
    toc_pages = detect_toc_pages(pages, max_toc_check_pages)
    print(f"  Found TOC on pages: {toc_pages or 'None'}")

    # Step 3: Build structure
    if toc_pages:
        print("Building structure from TOC...")
        structure = build_structure_from_toc(
            pages, toc_pages, max_pages_per_node
        )
    else:
        print("No TOC found, generating structure from content...")
        structure = build_structure_from_content(pages, max_pages_per_node)

    # Step 4: Add metadata
    if add_node_ids:
        add_node_ids_to_tree(structure)

    if add_text:
        add_node_text(structure, pages)

    processing_time = time.time() - start_time

    return ProcessingResult(
        doc_name=pdf_path.stem,
        total_pages=total_pages,
        structure=structure,
        toc_pages=toc_pages,
        processing_time=processing_time,
    )


def detect_toc_pages(
    pages: List[PageInfo], max_toc_check_pages: int
) -> List[int]:
    """Detect which pages contain the Table of Contents."""
    # Create lookup dict for easy access
    pages_by_num = {p.page_num: p for p in pages}

    candidate_pages = []

    # First try fast regex-based detection
    for page in pages[:max_toc_check_pages]:
        if is_likely_toc_page(page.text):
            candidate_pages.append(page.page_num)

    toc_pages = []

    # Verify candidates with LLM
    if candidate_pages:
        for page_num in candidate_pages:
            page = pages_by_num[page_num]
            is_toc = detect_toc(page_text=page.text)
            if is_toc:
                toc_pages.append(page_num)

    # If no candidates found, check all early pages with LLM
    if not toc_pages:
        for page in pages[:max_toc_check_pages]:
            is_toc = detect_toc(page_text=page.text)
            if is_toc:
                toc_pages.append(page.page_num)

    # Expand to consecutive pages
    if toc_pages:
        toc_pages = expand_consecutive_pages(sorted(toc_pages), pages)

    return toc_pages


def expand_consecutive_pages(
    toc_pages: List[int], pages: List[PageInfo]
) -> List[int]:
    """Expand TOC pages to include consecutive pages."""
    if not toc_pages:
        return []

    # Create lookup dict
    pages_by_num = {p.page_num: p for p in pages}

    expanded = [toc_pages[0]]

    for i in range(1, len(toc_pages)):
        if toc_pages[i] == toc_pages[i - 1] + 1:
            expanded.append(toc_pages[i])

    # Check one page after the last TOC page
    last_toc = max(expanded)
    if last_toc + 1 in pages_by_num:
        next_page = pages_by_num[last_toc + 1]
        if is_likely_toc_page(next_page.text):
            is_toc = detect_toc(page_text=next_page.text)
            if is_toc:
                expanded.append(last_toc + 1)

    return sorted(expanded)


def build_structure_from_toc(
    pages: List[PageInfo], toc_pages: List[int], max_pages_per_node: int
) -> List[TreeNode]:
    """Build tree structure from detected TOC."""
    # Extract TOC content from all TOC pages
    toc_texts = []
    for page_num in toc_pages:
        content = extract_toc(page_text=pages[page_num].text)
        if content:
            toc_texts.append(content)

    combined_toc_text = "\n".join(toc_texts)

    # Clean TOC text
    cleaned_toc = clean_toc_dots(combined_toc_text)

    # Transform to structured sections
    sections = transform_toc(toc_text=cleaned_toc)

    # Assign page indices
    sections_with_pages = assign_pages_to_sections(sections, pages)

    # Convert to TreeNode objects
    return convert_to_tree_nodes(sections_with_pages)


def build_structure_from_content(
    pages: List[PageInfo], max_pages_per_node: int
) -> List[TreeNode]:
    """Build structure by generating TOC from content."""
    # Sample pages throughout document
    sample_pages = pages[:: max(1, len(pages) // 20)][:20]
    page_samples = [
        PageSample(page_num=p.page_num, text=p.text[:800])
        for p in sample_pages
    ]

    # Generate TOC
    sections_with_pages = generate_toc(page_samples=page_samples)

    # Convert to TreeNode objects
    return convert_to_tree_nodes(sections_with_pages)


def assign_pages_to_sections(
    sections: List[Section], pages: List[PageInfo]
) -> List[SectionWithPageIndex]:
    """Assign physical page indices to TOC sections."""
    # Sample pages for matching
    sample_pages = [
        PageSample(page_num=p.page_num, text=p.text[:500]) for p in pages[:50]
    ]

    # Assign indices
    matches = assign_page_indices(
        toc_sections=sections, page_samples=sample_pages
    )

    return matches


def convert_to_tree_nodes(
    sections: List[SectionWithPageIndex],
) -> List[TreeNode]:
    """Convert flat section list to hierarchical TreeNode objects."""
    if not sections:
        return []

    # Build hierarchy based on levels
    root_nodes = []
    stack = []

    for section in sections:
        node = TreeNode(
            title=section.title,
            level=section.level,
            start_page=section.page_index,
        )

        # Find parent based on level
        while stack and stack[-1].level >= node.level:
            stack.pop()

        if stack:
            stack[-1].children.append(node)
        else:
            root_nodes.append(node)

        stack.append(node)

    # Calculate end pages
    calculate_end_pages(root_nodes)

    return root_nodes


def calculate_end_pages(nodes: List[TreeNode]) -> None:
    """Calculate end_page for each node."""
    for i, node in enumerate(nodes):
        # Set end_page based on next sibling
        if i + 1 < len(nodes):
            next_start = nodes[i + 1].start_page
            if next_start is not None:
                node.end_page = next_start - 1

        # Process children
        if node.children:
            calculate_end_pages(node.children)
            # Node ends where last child ends
            if node.children[-1].end_page is not None:
                node.end_page = node.children[-1].end_page

        # If still no end_page, use start_page
        if node.end_page is None:
            node.end_page = node.start_page


def add_node_ids_to_tree(nodes: List[TreeNode], prefix: str = "") -> None:
    """Add sequential node IDs to tree."""
    for i, node in enumerate(nodes):
        node_id = f"{prefix}{i:04d}" if prefix else f"{i:04d}"
        node.node_id = node_id

        if node.children:
            add_node_ids_to_tree(node.children, prefix=f"{node_id}_")


def add_node_text(nodes: List[TreeNode], pages: List[PageInfo]) -> None:
    """Add full text content to each node."""
    for node in nodes:
        if node.start_page is not None and node.end_page is not None:
            text_parts = []
            for page in pages:
                if node.start_page <= page.page_num <= node.end_page:
                    text_parts.append(page.text)
            node.text = "\n\n".join(text_parts)

        if node.children:
            add_node_text(node.children, pages)


response: ProcessingResult = process_pdf(
    pdf_path="/Users/joaopatriota/Downloads/shape-up.pdf"
)
breakpoint()
