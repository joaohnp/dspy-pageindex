# dspy-pageindex

A rewrite of PageIndex — a modular, DSPy-first library for extracting structured Table of Contents hierarchies from PDF documents.

## What This Is

This is a ground-up rewrite of the original PageIndex project, designed with a singular focus: clean, modular DSPy integration. The original implementation mixed concerns and relied on complex custom LLM handling. This version strips away that complexity and leans into DSPy's signature-based architecture, making every LLM operation explicit, testable, and composable.

## What It Does

Takes a PDF and returns a fully navigable tree structure of its contents — chapters, sections, subsections — with page ranges, unique IDs, and optional AI-generated summaries. Perfect for document search, content navigation, or feeding structured content into RAG systems.

## Why This Version

- **DSPy-native**: Every LLM interaction is a clean DSPy signature. No custom prompt templates, no abstraction layers.
- **Truly modular**: PDF extraction, regex processing, LLM operations, and pipeline orchestration are cleanly separated.
- **Hybrid intelligence**: Uses regex for speed, LLM for understanding. Fast pattern matching, smart content analysis.
- **Navigation-ready**: Outputs include node IDs, page ranges, and summaries — everything you need to build a document browser.

## Quick Start

```bash
# Install with uv
uv sync


```

```python
from pathlib import Path
from main import process_pdf

# Extract structure with summaries for navigation
result = process_pdf(
    pdf_path=Path("document.pdf"),
    add_summaries=True,
)

# Get JSON output
print(result.to_json())
```

## Core Features

### Automatic TOC Detection

The pipeline first hunts for an existing Table of Contents using fast regex patterns, then verifies with the LLM. No TOC? No problem — it generates one from the document content.

### Intelligent Structure Extraction

Parses TOC entries into a clean hierarchy: Parts → Chapters → Sections → Subsections. Handles nested structures, numbering schemes, and indentation patterns automatically.

### Page Range Mapping

Maps every section to its actual page span in the PDF. Parent nodes span from their start to their last child's end. Perfect for extracting specific content ranges.

### AI-Powered Summaries

Generate informative paragraph summaries for each section using the actual content. Helps users understand what each section covers before diving in.

### Hierarchical Node IDs

Every node gets a unique, hierarchical ID (`0000`, `0000_0001`, etc.) that reflects its position in the structure. Great for referencing and navigation.

## Pipeline Flow

```
PDF → Extract Pages → Detect TOC Pages → Extract TOC Content
                                              ↓
                                    Transform to Sections
                                              ↓
                                    Assign Page Indices
                                              ↓
                                    Build Tree Structure
                                              ↓
                            [Add Node IDs] → [Add Text] → [Add Summaries]
                                              ↓
                                 ProcessingResult (JSON)
```

## Main Functions

### `process_pdf(pdf_path, ...)` — **The Entry Point**

Orchestrates the entire pipeline. Extracts structure, generates summaries, and returns a complete `ProcessingResult`.

```python
result = process_pdf(
    pdf_path="document.pdf",
    max_toc_check_pages=20,      # How many pages to scan for TOC
    max_pages_per_node=10,       # For content-based TOC generation
    add_node_ids=True,           # Assign hierarchical node IDs
    add_summaries=True,          # Generate AI summaries (requires text extraction)
    add_text=True,               # Include full text content
)
```

**Returns:** `ProcessingResult` with `doc_name`, `total_pages`, `structure` (tree), `toc_pages`, `processing_time`

---

### `detect_toc(page_text)` — **Find the Table of Contents**

Uses regex heuristics to identify candidate TOC pages, then verifies with the LLM.

```python
from llm_utils import detect_toc

is_toc = detect_toc(page_text="Table of Contents\nChapter 1... Page 1")
# Returns: True
```

---

### `extract_toc(page_text)` — **Get Clean TOC Content**

Strips away headers, footers, and noise. Returns only the structured TOC entries.

```python
from llm_utils import extract_toc

toc_content = extract_toc(page_text="Page 5\nTable of Contents\nChapter 1...\nPage 10")
# Returns: "Chapter 1...\nChapter 2..."
```

---

### `transform_toc(toc_text)` — **Parse Structure into Objects**

Converts raw TOC text into structured `Section` objects with titles, hierarchy levels, and page numbers.

```python
from llm_utils import transform_toc

sections = transform_toc(toc_text="1. Introduction\n  1.1 Background\n2. Methods")
# Returns: [
#   Section(title="Introduction", level=0, page=1),
#   Section(title="Background", level=1, page=None),
#   Section(title="Methods", level=0, page=2)
# ]
```

---

### `assign_page_indices(toc_sections, page_samples)` — **Map to Physical Pages**

Matches TOC entries to their actual locations in the PDF using LLM-powered fuzzy matching.

```python
from llm_utils import assign_page_indices, PageSample

matches = assign_page_indices(
    toc_sections=sections,
    page_samples=[PageSample(page_num=5, text="Introduction...")]
)
# Returns: [SectionWithPageIndex(title="Introduction", page_index=5, level=0)]
```

---

### `generate_summary(title, text)` — **Summarize for Navigation**

Creates informative paragraph summaries from section content — perfect for TOC tooltips or preview text.

```python
from llm_utils import generate_summary

summary = generate_summary(
    title="Setting Boundaries",
    text="This section explains how to set clear project boundaries..."
)
# Returns: "This section explains the concept of setting boundaries in project..."
```

---

### `convert_to_tree_nodes(sections)` — **Build the Hierarchy**

Transforms a flat list of sections into a nested tree structure based on hierarchy levels.

---

### `add_node_ids_to_tree(nodes)` — **Assign Unique Identifiers**

Traverses the tree and assigns hierarchical node IDs for reference.

---

### `add_node_text(nodes, pages)` — **Extract Content**

Attaches the full text content to each node based on its page range.

---

### `add_node_summaries(nodes)` — **Generate AI Summaries**

Populates the `summary` field for each node using the `generate_summary` function.

## DSPy Signatures

All LLM operations are implemented as clean DSPy signatures:

| Signature | Purpose |
|-----------|---------|
| `TocDetector` | Detect if a page contains a Table of Contents |
| `TocExtractor` | Extract clean TOC content from a page |
| `TocTransformer` | Parse TOC text into structured sections |
| `PageIndexAssigner` | Match sections to physical page indices |
| `TocVerifier` | Verify a section title appears on a page |
| `TocGenerator` | Generate TOC from document content (fallback) |
| `NodeSummarizer` | Generate section summaries for navigation |

## Data Models

### `TreeNode`
The hierarchical structure representing document organization:
```python
class TreeNode(BaseModel):
    title: str                    # Section title
    level: int                    # Hierarchy depth (0, 1, 2...)
    start_page: Optional[int]     # First page number
    end_page: Optional[int]       # Last page number
    node_id: Optional[str]        # Unique ID (e.g., "0000_0001")
    summary: Optional[str]        # AI-generated summary
    text: Optional[str]          # Full text content
    children: List["TreeNode"]    # Child sections
```

### `ProcessingResult`
Complete pipeline output:
```python
class ProcessingResult(BaseModel):
    doc_name: str                 # Document filename
    total_pages: int              # Total page count
    structure: List[TreeNode]     # Hierarchical tree
    toc_pages: List[int]          # Pages where TOC was found
    processing_time: float       # Seconds to process

    def to_json(self) -> str      # Export to JSON
```

## Output Example

```json
{
  "doc_name": "shape-up",
  "total_pages": 176,
  "toc_pages": [1, 2, 6],
  "processing_time": 42.3,
  "structure": [
    {
      "title": "Introduction",
      "level": 0,
      "start_page": 11,
      "end_page": 16,
      "node_id": "0002",
      "summary": "This chapter introduces the Shape Up methodology...",
      "text": "Full text content...",
      "children": [
        {
          "title": "Growing pains",
          "level": 1,
          "start_page": 11,
          "end_page": 13,
          "node_id": "0002_0000",
          "summary": "Describes common challenges teams face...",
          "children": []
        }
      ]
    }
  ]
}
```

## Use Cases

- **Document Search**: Index books, reports, and papers for semantic search
- **Content Navigation**: Build interactive TOC widgets with preview summaries
- **RAG Pipelines**: Feed structured chunks into retrieval systems
- **Document Analysis**: Analyze document structure and organization patterns
- **PDF Processing**: Extract and organize content at scale

## Design Philosophy

1. **DSPy First**: Leverage DSPy's strengths — signatures, declarative prompts, and clean abstractions
2. **Modular Components**: Every function is independently testable and reusable
3. **Type Safety**: Pydantic models everywhere — catch errors before they propagate
4. **Hybrid Approach**: Use regex for speed, LLM for intelligence. Don't use an LLM when a pattern will do.

