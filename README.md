# Clinical Codes Finder

An intelligent agentic RAG system that takes clinical terms and returns high-confidence codes across multiple medical coding systems.

## Overview

Clinical Codes Finder uses AI-powered intent classification and dynamic API orchestration to search the right coding systems for any clinical query:

| System | Purpose | Example Query |
|--------|---------|---------------|
| **ICD-10-CM** | Diagnosis codes | "diabetes" |
| **LOINC** | Lab tests, measurements | "glucose test" |
| **RxTerms** | Drug names, strengths | "metformin 500 mg" |
| **HCPCS** | Medical supplies/services | "wheelchair" |
| **UCUM** | Units of measure | "mg/dL" |
| **HPO** | Phenotypic traits/symptoms | "ataxia" |

## Architecture

The system uses a **Plan-Execute-Reflect-Consolidate** pattern implemented with LangGraph:

```
classify → plan → execute → reflect → [refine or consolidate] → summarize
                    ↑___________|
                    (iterative loop)
```

Key design principles:
- **Never hallucinate codes** — All results come directly from the Clinical Tables API
- **High precision over recall** — Confidence scoring filters noise
- **Traceable reasoning** — Full audit trail of decisions and API calls

## Quick Start

### Prerequisites

- Python 3.11+
- OpenAI API key

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/clinical-codes-finder.git
cd clinical-codes-finder

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -e ".[dev]"

# Configure environment
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY
```

### Run the UI

```bash
source .venv/bin/activate
streamlit run src/ui/app.py
```

### Run Tests

```bash
# All tests
pytest

# Unit tests only (fast, no API calls)
pytest -m "not integration"

# Integration tests (hits real APIs)
pytest tests/test_integration.py -v
```

## Usage

### Streamlit UI

The web interface provides:
- Search input for clinical terms
- Real-time "thinking" visualization
- Results grouped by coding system
- Confidence badges (High/Medium/Low)
- API call audit trail

### Programmatic Usage

```python
import asyncio
from src.agent import run_agent

async def search():
    result = await run_agent("metformin 500 mg")

    print(f"Summary: {result['summary']}")
    for r in result['consolidated_results']:
        print(f"[{r.system}] {r.code}: {r.display}")

asyncio.run(search())
```

## Project Structure

```
clinical-codes-finder/
├── src/
│   ├── agent/           # LangGraph agent
│   │   ├── graph.py     # Graph definition
│   │   ├── state.py     # State schema
│   │   └── nodes/       # classify, plan, execute, reflect, consolidate, summarize
│   ├── tools/           # API adapters
│   │   ├── base.py      # HTTP client
│   │   ├── icd10.py     # ICD-10-CM
│   │   ├── loinc.py     # LOINC
│   │   ├── rxterms.py   # RxTerms
│   │   ├── hcpcs.py     # HCPCS
│   │   ├── ucum.py      # UCUM
│   │   └── hpo.py       # HPO
│   ├── scoring/         # Confidence scoring
│   └── ui/              # Streamlit app
├── tests/
│   ├── test_tools/      # Tool unit tests
│   └── test_integration.py  # End-to-end tests
├── docs/                # API documentation
└── PRD.md               # Product requirements
```

## How It Works

### 1. Intent Classification
Hybrid approach combining:
- **Rule-based patterns** (fast, deterministic) for obvious cases
- **LLM classification** (GPT-4o) for nuanced queries

### 2. Dynamic Tool Selection
Based on intent scores, the agent selects which coding systems to query:
- Diagnosis → ICD-10-CM, HPO
- Laboratory → LOINC, UCUM
- Medication → RxTerms
- Supplies → HCPCS

### 3. Parallel API Execution
Queries run concurrently with rate limiting (max 5 concurrent) to optimize latency.

### 4. Iterative Refinement
If results are insufficient:
- **0 results** → broaden terms (synonyms, remove modifiers)
- **50+ results** → narrow terms (add specificity)
- Max 3 iterations to prevent runaway loops

### 5. Confidence Scoring
Multi-factor scoring (deterministic, not LLM):
- Lexical overlap (Jaccard similarity)
- Exact substring match bonus
- Code specificity

### 6. Summary Generation
LLM generates plain-English explanation of findings, referencing only the actual API results.

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENAI_API_KEY` | (required) | Your OpenAI API key |
| `OPENAI_MODEL` | `gpt-4o` | Model for classification/summarization |
| `MAX_ITERATIONS` | `3` | Max refinement iterations |
| `MAX_API_CALLS` | `12` | Max API calls per query |
| `CONFIDENCE_THRESHOLD` | `0.3` | Min score for system selection |

## Data Sources

All data comes from the [NIH Clinical Tables API](https://clinicaltables.nlm.nih.gov/):
- ICD-10-CM (CDC)
- LOINC (Regenstrief Institute)
- RxTerms (NLM)
- HCPCS (CMS)
- UCUM
- HPO (Monarch Initiative)

## License

MIT

## Acknowledgments

- NIH National Library of Medicine for the Clinical Tables API
- LangChain/LangGraph for the agent framework
- OpenAI for GPT-4o
