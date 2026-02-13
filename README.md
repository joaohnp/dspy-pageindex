# PageIndex - Modular Implementation

A clean, modular reimplementation of the PageIndex pipeline using Pydantic models and native DSPy signatures.

## Features

- **Pydantic Throughout**: All classes use Pydantic BaseModel for validation and serialization
- **Native DSPy Signatures**: Clean DSPy-style signatures for LLM operations
- **Hybrid Processing**: Regex-based pattern detection + LLM-based reasoning
- **Pathlib**: No `os` module usage
- **Synchronous**: Simple, straightforward execution
- **OpenRouter Support**: Works with any OpenAI-compatible API

## Architecture

```
new/
├── pdf_utils.py      # PDF ingestion and token counting
├── regexp_utils.py   # Pattern detection and text cleaning
├── llm_utils.py      # DSPy signatures for TOC processing
├── main.py           # Pipeline orchestration
├── requirements.txt  # Dependencies
├── __init__.py       # Package exports
└── README.md         # This file
```

## Installation

```bash
pip install -r requirements.txt
```

## Usage

### Setup DSPy with OpenRouter

```python
import os
import dspy
from dotenv import load_dotenv

load_dotenv()

# Configure DSPy with your OpenRouter setup
lm = dspy.LM(
    model="openrouter/openai/gpt-4o",
    api_base=os.getenv("OPEN_ROUTER_BASE_URL"),
    api_key=os.getenv("OPEN_ROUTER_API_KEY"),
    max_tokens=80000,
    cache=False,
    temperature=0.5,
)
dspy.settings.configure(lm=lm)
```

### Process a PDF

```python
from pathlib import Path
from new import process_pdf

# Process a PDF
result = process_pdf(
    pdf_path=Path("document.pdf"),
    model="openrouter/openai/gpt-4o"
)

# Get JSON output
print(result.to_json())
```

### Using Individual Signatures

```python
from new.llm_utils import detect_toc, extract_toc, Section

# Detect if a page is a TOC
result = detect_toc(page_text="Table of Contents... Chapter 1...")
print(result.is_toc_page)  # True or False

# Extract TOC content
result = extract_toc(page_text="Table of Contents\nChapter 1... Page 1")
print(result.toc_content)
```

## DSPy Signatures

All LLM operations are implemented as native DSPy signatures:

### `TocDetector`
Detects if a page contains a Table of Contents.
```python
class TocDetector(dspy.Signature):
    page_text: str = dspy.InputField()
    is_toc_page: bool = dspy.OutputField()
```

### `TocExtractor`
Extracts raw TOC content from a page.
```python
class TocExtractor(dspy.Signature):
    page_text: str = dspy.InputField()
    toc_content: str = dspy.OutputField()
```

### `TocTransformer`
Transforms TOC text to structured sections.
```python
class TocTransformer(dspy.Signature):
    toc_text: str = dspy.InputField()
    sections: List[Section] = dspy.OutputField()
```

### `PageIndexAssigner`
Matches TOC entries to physical page indices.
```python
class PageIndexAssigner(dspy.Signature):
    toc_entries: List[Section] = dspy.InputField()
    page_samples: str = dspy.InputField()
    matches: List[SectionWithPageIndex] = dspy.OutputField()
```

### `TocVerifier`
Verifies if a section title appears on a page.
```python
class TocVerifier(dspy.Signature):
    title: str = dspy.InputField()
    page_text: str = dspy.InputField()
    is_present: bool = dspy.OutputField()
```

### `TocGenerator`
Generates TOC from document content when none exists.
```python
class TocGenerator(dspy.Signature):
    page_samples: str = dspy.InputField()
    sections: List[SectionWithPageIndex] = dspy.OutputField()
```

## Pydantic Models

All data structures are Pydantic models:

- `Section`: TOC section with title, level, and optional page number
- `SectionWithPageIndex`: Section with assigned physical page index
- `TreeNode`: Hierarchical tree node with children
- `PageInfo`: PDF page with text and token count
- `ProcessingResult`: Complete pipeline result
- `PipelineConfig`: Configuration options

## CLI Usage

```bash
# Set API key
export OPEN_ROUTER_API_KEY="your-api-key"
export OPEN_ROUTER_BASE_URL="https://openrouter.ai/api/v1"

# Configure DSPy in your script, then:
python -m new.main document.pdf

# Save to file
python -m new.main document.pdf -o output.json

# Include full text
python -m new.main document.pdf --add-text
```

## Configuration

```python
from new import PipelineConfig

config = PipelineConfig(
    model="openrouter/openai/gpt-4o",
    max_toc_check_pages=20,
    max_pages_per_node=10,
    add_node_ids=True,
    add_summaries=False,
    add_text=False
)

result = process_pdf("document.pdf", **config.dict())
```

## Output Format

```json
{
  "doc_name": "document",
  "total_pages": 150,
  "toc_pages": [2, 3],
  "processing_time": 45.2,
  "structure": [
    {
      "title": "Introduction",
      "level": 0,
      "start_page": 5,
      "end_page": 10,
      "node_id": "0000",
      "children": [
        {
          "title": "Background",
          "level": 1,
          "start_page": 5,
          "end_page": 7,
          "node_id": "0000_0000"
        }
      ]
    }
  ]
}
```

## Pipeline Flow

1. **PDF Ingestion**: Extract text using PyPDF2
2. **TOC Detection**: Regex heuristics + DSPy `TocDetector`
3. **TOC Extraction**: DSPy `TocExtractor`
4. **Structure Transformation**: DSPy `TocTransformer` → `List[Section]`
5. **Page Index Assignment**: DSPy `PageIndexAssigner` → `List[SectionWithPageIndex]`
6. **Tree Construction**: Build hierarchical `TreeNode` objects
7. **Metadata Addition**: Add node IDs, text content (optional)

## Design Principles

1. **Pydantic Everywhere**: All classes inherit from BaseModel
2. **DSPy Native**: Clean signatures matching DSPy conventions
3. **Type Safety**: Full type hints
4. **Pathlib**: No `os.path` usage
5. **Minimal Boilerplate**: Leverage DSPy for LLM operations

## Dependencies

- `pypdf2>=3.0.0` - PDF text extraction
- `tiktoken>=0.5.0` - Token counting
- `dspy-ai>=2.0.0` - LLM framework
- `pydantic>=2.0.0` - Data validation
- `python-dotenv>=1.0.0` - Environment variables

## License

Same as the original PageIndex project.
