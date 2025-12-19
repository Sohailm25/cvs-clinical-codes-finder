# Clinical Codes Finder

An intelligent AI-powered system that instantly finds the right medical codes across multiple coding systems. Enter a clinical term like "diabetes" or "metformin 500mg" and get accurate, confidence-scored results from ICD-10, LOINC, RxTerms, and more.

## Demo

https://www.loom.com/share/d35af18a6f8845adbef7fb8cd1c982bc

## Quick Start

### Prerequisites

- Python 3.11+
- OpenAI API key

### Setup (5 minutes)

```bash
# Clone the repository
git clone git@github.com:Sohailm25/cvs-clinical-codes-finder.git
cd cvs-clinical-codes-finder

# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install dependencies
pip install -e ".[dev]"

# Configure environment
cp .env.example .env
```

Edit `.env` and add your keys:

```bash
OPENAI_API_KEY=sk-your-key-here
CHAINLIT_AUTH_SECRET=your-secret-here  # Generate with: chainlit create-secret
```

### Run the App

```bash
chainlit run src/ui/chainlit_app.py
```

Open http://localhost:8000 and log in:
- **Username:** `admin`
- **Password:** `changeme`

## What It Does

Clinical Codes Finder solves a common healthcare workflow problem: finding the correct medical codes across different coding systems. Instead of searching multiple databases manually, you ask a single question and get unified results.

### Supported Coding Systems

| System | What It Codes | Example Query |
|--------|---------------|---------------|
| **ICD-10-CM** | Diagnoses, conditions | "type 2 diabetes", "hypertension" |
| **LOINC** | Lab tests, measurements | "hemoglobin A1c", "glucose test" |
| **RxTerms** | Medications, drug names | "metformin 500 mg", "lisinopril" |
| **HCPCS** | Medical supplies, services | "wheelchair", "nebulizer" |
| **UCUM** | Units of measure | "mg/dL", "milliliters" |
| **HPO** | Phenotypes, symptoms | "ataxia", "muscle weakness" |

### Key Features

- **Smart Intent Detection** — Automatically determines which coding systems to search based on your query
- **Clarification Questions** — When a query is ambiguous (e.g., "iron"), asks what type of code you need
- **Multi-hop Reasoning** — Optionally expands searches to related terms (e.g., "diabetes" → also searches for related lab tests)
- **Confidence Scoring** — Results are ranked by relevance with percentage scores
- **Code Bundles** — Save codes to a bundle and export as CSV
- **Streaming Results** — See the AI's reasoning process in real-time

## How It Works

The system uses a **Plan-Execute-Reflect** pattern:

```
Query → Classify Intent → Select Systems → Search APIs → Score Results → Summarize
                              ↑                              |
                              └──── Refine if needed ────────┘
```

1. **Classify** — Hybrid rule-based + LLM classification determines query intent
2. **Plan** — Selects which coding systems to query based on intent scores
3. **Execute** — Runs parallel API calls to the NIH Clinical Tables API
4. **Score** — Ranks results using lexical similarity and specificity
5. **Reflect** — If results are poor, refines the search strategy
6. **Summarize** — Generates a plain-English explanation of findings

All codes come directly from authoritative sources via the [NIH Clinical Tables API](https://clinicaltables.nlm.nih.gov/) — the system never hallucinates codes.

## Project Structure

```
cvs-clinical-codes-finder/
├── src/
│   ├── agent/              # LangGraph agent implementation
│   │   ├── graph.py        # Agent graph definition
│   │   ├── state.py        # State schema
│   │   ├── multi_hop.py    # Related term expansion
│   │   └── nodes/          # Plan, execute, reflect, consolidate, summarize
│   ├── tools/              # API adapters for each coding system
│   ├── scoring/            # Confidence scoring and reranking
│   ├── services/           # HTTP client, caching, query expansion
│   └── ui/                 # Chainlit chat interface
├── frontend/               # React frontend (alternative UI)
├── tests/                  # Unit and integration tests
└── docs/                   # API documentation
```

## Configuration

All settings are in `.env`. Key options:

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENAI_API_KEY` | (required) | Your OpenAI API key |
| `CHAINLIT_AUTH_SECRET` | (required) | Auth secret for Chainlit |
| `OPENAI_MODEL` | `gpt-4o` | Model for classification/summarization |
| `MAX_ITERATIONS` | `3` | Max refinement attempts |
| `EXPANSION_ENABLED` | `true` | Enable LLM query expansion |
| `CACHE_ENABLED` | `true` | Cache API responses |

## Running Tests

```bash
# All tests
pytest

# Fast tests only (no external API calls)
pytest -m "not integration"

# With coverage
pytest --cov=src
```

## Data Sources

All medical codes come from the [NIH Clinical Tables API](https://clinicaltables.nlm.nih.gov/), which aggregates data from:

- **ICD-10-CM** — CDC
- **LOINC** — Regenstrief Institute
- **RxTerms** — National Library of Medicine
- **HCPCS** — Centers for Medicare & Medicaid Services
- **UCUM** — Unified Code for Units of Measure
- **HPO** — Human Phenotype Ontology (Monarch Initiative)

## License

MIT
