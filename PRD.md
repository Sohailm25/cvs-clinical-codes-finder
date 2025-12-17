# PRD: Clinical Codes Finder

## Executive Summary

Build an agentic RAG system that accepts clinical terms and returns high-confidence codes across 6 medical coding systems (ICD-10-CM, LOINC, RxTerms/RxNorm, HCPCS, UCUM, HPO) using the NIH Clinical Tables API.

**Key Differentiator**: Unlike static lookup tools, this agent *reasons* about which systems to query, *iteratively refines* searches based on results, and *explains* its findings — preventing hallucinated codes while maximizing relevance.

---

## 1. Problem Statement

Healthcare billing and clinical documentation require matching natural language terms to standardized codes across fragmented systems. Manual lookup is:
- **Slow**: 5-10 minutes per complex query
- **Error-prone**: Codes get misapplied due to semantic ambiguity
- **Siloed**: Each coding system has its own interface; no unified search

---

## 2. Solution Overview

An AI agent that:
1. **Interprets** clinical queries to determine relevant coding systems
2. **Plans** which APIs to call and in what order
3. **Executes** searches iteratively, refining based on results
4. **Consolidates** results with deduplication and confidence scoring
5. **Explains** findings in plain English with full traceability

### Architecture Pattern: Plan-Execute-Reflect-Consolidate

```
┌─────────┐     ┌─────────┐     ┌─────────┐     ┌─────────────┐     ┌──────────┐
│ CLASSIFY│────▶│  PLAN   │────▶│ EXECUTE │────▶│  REFLECT    │────▶│CONSOLIDATE│
│         │     │         │     │         │     │             │     │          │
│ Detect  │     │ Select  │     │ Parallel│     │ Assess:     │     │ Dedupe   │
│ intent  │     │ systems │     │ API     │     │ - Coverage  │     │ Rank     │
│ domains │     │ + order │     │ calls   │     │ - Quality   │     │ Summarize│
└─────────┘     └─────────┘     └─────────┘     │ - Refine?   │     └──────────┘
                                    ▲           └──────┬──────┘
                                    └──────────────────┘
                                     (loop if needed, max 3 iterations)
```

---

## 3. Functional Requirements

### 3.1 Intent Classification (FR-1)

**Purpose**: Determine which coding systems are relevant before making API calls.

| Intent Domain | Signal Patterns | Target Systems |
|--------------|-----------------|----------------|
| Diagnosis | disease, condition, syndrome, -itis, -osis | ICD-10-CM, HPO |
| Laboratory | test, level, measurement, panel, blood, urine | LOINC, UCUM |
| Medication | mg, tablet, capsule, injection, drug names | RxTerms, RxNorm |
| Supply/Service | wheelchair, crutch, DME, procedure | HCPCS |
| Unit | per, /, mg/dL, mmol/L, unit patterns | UCUM |
| Phenotype | symptom, feature, abnormal, trait | HPO |

**Implementation**:
1. **Rule-based pre-filter** (fast, deterministic) — regex/keyword matching
2. **LLM classifier** (semantic) — handles ambiguous cases
3. **Confidence threshold** — only query systems scoring > 0.3

**Multi-intent handling**: Queries like "diabetes a1c test" should trigger both ICD-10-CM AND LOINC.

### 3.2 Tool Layer (FR-2)

**Constraint**: NO static pre-search. All retrieval is dynamic via Clinical Tables API.

Each tool wraps a specific Clinical Tables endpoint:

| Tool | Dataset | Primary Fields | Notes |
|------|---------|----------------|-------|
| `search_icd10` | icd10cm | code, name | CDC diagnosis codes |
| `search_loinc` | loinc | LOINC_NUM, LONG_COMMON_NAME | Lab/measurement codes |
| `search_rxterms` | rxterms | RXCUI, DISPLAY_NAME, STRENGTH | Drug names with strengths |
| `search_rxnorm` | rxnorm | rxcui, name | Normalized drug identifiers |
| `search_hcpcs` | hcpcs | code, description | Medical supplies/services |
| `search_ucum` | ucum | code, name | Units of measure |
| `search_hpo` | hpo | id, name | Phenotypic traits |

**Tool Output Schema** (normalized across all tools):
```python
{
    "system": str,         # e.g., "ICD-10-CM"
    "code": str,           # e.g., "E11.9"
    "display": str,        # e.g., "Type 2 diabetes mellitus without complications"
    "confidence": float,   # 0.0-1.0, computed post-retrieval
    "metadata": dict,      # system-specific extras
    "source": {
        "tool": str,       # which tool was called
        "term_used": str   # exact search term
    }
}
```

### 3.3 State Management (FR-3)

The agent maintains state throughout execution:

```python
class AgentState(TypedDict):
    # Input
    query: str

    # Classification
    intent_scores: dict[str, float]  # domain -> confidence
    selected_systems: list[str]

    # Planning
    search_terms: list[str]  # original + expanded/refined terms

    # Execution
    iteration: int  # current iteration (max 3)
    api_calls: list[dict]  # log of all calls made
    raw_results: dict[str, list]  # system -> raw results

    # Reflection
    coverage_assessment: str  # LLM assessment of result quality
    needs_refinement: bool
    refinement_strategy: str | None  # "broaden" | "narrow" | None

    # Output
    consolidated_results: list[dict]
    summary: str
    reasoning_trace: list[str]  # human-readable decision log
```

### 3.4 Execution Strategy (FR-4)

**Parallel Execution**: Independent API calls run concurrently with rate limiting.

```python
semaphore = asyncio.Semaphore(5)  # max 5 concurrent calls
results = await asyncio.gather(
    *[rate_limited(tool.search(term), semaphore) for tool, term in tasks],
    return_exceptions=True
)
```

**Stop Conditions**:
- Max iterations: 3
- Max API calls per run: 12
- Max refinements per system: 2
- High confidence early exit: if top result has confidence > 0.9 and exact token match

**Timeouts**: 3 seconds per API call, 10 seconds total per iteration.

### 3.5 Reflection Logic (FR-5)

After each execution cycle, assess results:

| Condition | Action |
|-----------|--------|
| 0 results, iteration < 3 | Broaden terms (remove modifiers, try synonyms) |
| >50 results | Narrow terms (add specificity, filter by context) |
| Results present but low confidence | Try synonym expansion via LLM |
| High-confidence results found | Stop and consolidate |

### 3.6 Confidence Scoring (FR-6)

**Multi-factor scoring** (deterministic first, LLM second):

```python
def compute_confidence(query: str, result: dict) -> float:
    scores = [
        (jaccard_similarity(query, result["display"]), 0.30),  # lexical
        (1.0 / (1 + result.get("rank", 0) * 0.1), 0.20),       # API position
        (min(len(result["code"]) / 10, 1.0), 0.20),            # specificity
        (embedding_similarity(query, result["display"]), 0.30) # semantic
    ]
    return sum(score * weight for score, weight in scores)
```

**Critical Rule**: The LLM may help *rank* results but NEVER *invent* codes. If API returns nothing, output "No matching codes found" — never hallucinate.

### 3.7 Consolidation & Deduplication (FR-7)

**Step 1**: Exact code dedup (same system, same code)
**Step 2**: Cross-system semantic dedup (e.g., RxTerms + RxNorm returning same drug)
- Cluster by embedding similarity (threshold 0.92)
- Keep best representative per cluster
- Attach `related_codes` for others in cluster

**Step 3**: Final ranking
- Sort by confidence descending
- Return top 3 per system (configurable)
- Label confidence tiers: "high" (>0.8), "medium" (0.5-0.8), "possible" (0.3-0.5)

### 3.8 Summary Generation (FR-8)

**Output Structure**:
```json
{
    "summary": "Found 5 codes for 'metformin 500 mg': 2 drug formulations from RxNorm...",
    "results": {
        "RxNorm": [
            {"code": "861004", "display": "metformin 500 MG Oral Tablet", "confidence": 0.95}
        ],
        ...
    },
    "reasoning_trace": [
        "Classified as medication query (confidence: 0.92)",
        "Queried RxTerms and RxNorm in parallel",
        "Found 8 candidates, filtered to top 3 by confidence"
    ]
}
```

---

## 4. Non-Functional Requirements

### 4.1 Performance
- **Latency**: < 10 seconds end-to-end for typical queries
- **Concurrency**: Support 5 concurrent API calls with rate limiting

### 4.2 Reliability
- **Graceful degradation**: If one API fails, return results from others with a note
- **Retry logic**: Exponential backoff on transient failures (max 2 retries)

### 4.3 Observability
- **Structured logging**: Request ID, tool calls, latencies
- **LangSmith integration** (optional): For debugging agent traces

### 4.4 Security
- **No PII storage**: Queries may contain sensitive terms; use short retention
- **Rate limiting**: Prevent API abuse

---

## 5. Technical Stack

| Component | Choice | Rationale |
|-----------|--------|-----------|
| Language | Python 3.11+ | Async support, LangChain ecosystem |
| Orchestration | LangGraph | Explicit state machine with conditional edges |
| LLM | OpenAI GPT-4o | Required for complex classification/reasoning |
| HTTP Client | httpx | Async support, timeouts, retries |
| UI | Streamlit | Fast to build, supports "thinking" visualization |
| Testing | pytest + pytest-asyncio | Async test support |

---

## 6. Project Structure

```
clinical-codes-finder/
├── src/
│   ├── __init__.py
│   ├── agent/
│   │   ├── __init__.py
│   │   ├── graph.py           # LangGraph definition
│   │   ├── state.py           # State schema
│   │   └── nodes/
│   │       ├── __init__.py
│   │       ├── classify.py    # Intent classification
│   │       ├── plan.py        # Search planning
│   │       ├── execute.py     # Parallel tool execution
│   │       ├── reflect.py     # Result assessment
│   │       ├── consolidate.py # Dedup + ranking
│   │       └── summarize.py   # Response generation
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── base.py            # Base tool class
│   │   ├── clinical_tables.py # HTTP client wrapper
│   │   ├── icd10.py
│   │   ├── loinc.py
│   │   ├── rxterms.py
│   │   ├── rxnorm.py
│   │   ├── hcpcs.py
│   │   ├── ucum.py
│   │   └── hpo.py
│   ├── scoring/
│   │   ├── __init__.py
│   │   ├── confidence.py      # Multi-factor scoring
│   │   └── dedup.py           # Deduplication logic
│   ├── ui/
│   │   └── app.py             # Streamlit app
│   └── config.py              # Configuration
├── tests/
│   ├── __init__.py
│   ├── test_tools/            # Unit tests for each tool
│   ├── test_nodes/            # Unit tests for graph nodes
│   ├── test_scoring/          # Confidence + dedup tests
│   └── test_integration.py    # End-to-end tests
├── .env.example
├── pyproject.toml
└── README.md
```

---

## 7. Test Plan

### 7.1 Required Test Prompts (from assignment)

| Query | Expected Primary System | Acceptance Criteria |
|-------|------------------------|---------------------|
| "diabetes" | ICD-10-CM | Returns E10-E14 range codes |
| "glucose test" | LOINC | Returns glucose measurement LOINCs |
| "metformin 500 mg" | RxTerms/RxNorm | Returns RXCUI for metformin 500mg |
| "wheelchair" | HCPCS | Returns K0001-K0108 range |
| "mg/dL" | UCUM | Returns mg/dL unit code |
| "ataxia" | HPO | Returns HP:0001251 or related |

### 7.2 Adversarial Tests

| Test Case | Purpose |
|-----------|---------|
| "tuberculosus" (misspelling) | Fuzzy matching / synonym expansion |
| "cold" (ambiguous) | Multi-intent handling (diagnosis vs. medication) |
| "diabetes a1c test" | Multi-system query (ICD-10 + LOINC) |
| "" (empty query) | Graceful error handling |
| "asdfghjkl" (nonsense) | Returns "no matches" without hallucination |

### 7.3 Performance Tests

- Latency < 10s for 95th percentile queries
- No memory leaks on 100 consecutive queries
- Graceful handling of API timeouts

---

## 8. UI Requirements (Demo Video Support)

### 8.1 Core Features

1. **Search input**: Single text box for clinical term
2. **"Thinking" panel**: Real-time display of agent reasoning
   - "Detected: Drug query (metformin 500 mg)"
   - "Querying RxTerms... found 8 candidates"
   - "Filtering by strength match..."
3. **Results panel**: Grouped by coding system
   - Code, display name, confidence badge
   - Expandable metadata
4. **Summary section**: Plain-English explanation

### 8.2 Demo Video Flow (60-90s)

1. **Problem** (10s): "Medical coding is fragmented — 6+ databases, each with its own lookup tool."
2. **What** (10s): "Our AI agent unifies these into one intelligent search."
3. **Why** (15s): "Unlike basic lookup, it *reasons* about which databases to query and *explains* its findings."
4. **How** (45s): Live demo with 2-3 queries showing the "thinking" panel
5. **Impact** (10s): "Faster coding, fewer errors, full audit trail."

---

## 9. Implementation Phases

### Phase 1: Foundation (Tool Layer)
- [ ] HTTP client wrapper for Clinical Tables API
- [ ] Implement all 7 tools with normalized output schema
- [ ] Unit tests for each tool

### Phase 2: Agent Core (State Machine)
- [ ] Define AgentState schema
- [ ] Implement classify → plan → execute → reflect → consolidate nodes
- [ ] Implement conditional edges (refine loop)
- [ ] Integration tests for basic flow

### Phase 3: Scoring & Dedup
- [ ] Multi-factor confidence scoring
- [ ] Cross-system deduplication
- [ ] Summary generation

### Phase 4: UI & Demo
- [ ] Streamlit app with "thinking" visualization
- [ ] Polish for demo video
- [ ] Record and upload video

---

## 10. Success Metrics

| Metric | Target |
|--------|--------|
| Test prompt accuracy | 6/6 correct primary systems |
| Hallucination rate | 0% (no invented codes) |
| Latency (p95) | < 10 seconds |
| Demo video length | 60-120 seconds |
| Code quality | All tests passing, clean structure |

---

## 11. Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Clinical Tables API rate limiting | Queries fail | Caching, exponential backoff, semaphore |
| LLM hallucinating codes | Incorrect medical codes | Deterministic scoring first; LLM can only rank, never invent |
| Scope creep | Missed deadline | Strict phase boundaries; MVP first |
| Ambiguous queries | Poor results | Multi-intent handling; ask for clarification in edge cases |

---

## 12. Open Questions

1. **RxTerms vs RxNorm**: Should we always query both, or use RxNorm as fallback? (Recommendation: Query both, dedupe by RXCUI)

2. **Embedding model**: Use OpenAI embeddings or local sentence-transformers? (Recommendation: OpenAI for consistency with GPT-4o)

3. **Caching strategy**: In-memory only, or persist? (Recommendation: In-memory LRU for demo; Redis for production)

---

## Appendix A: Clinical Tables API Reference

Base URL: `https://clinicaltables.nlm.nih.gov/api`

**Endpoint pattern**: `/search?terms={query}&maxList={n}&df={fields}`

**Response format**:
```json
[
    total_count,
    [codes...],
    {extra_fields...},
    [display_strings...]
]
```

---

## Appendix B: Decision Log

| Decision | Rationale | Source |
|----------|-----------|--------|
| LangGraph over vanilla LangChain | Explicit state machine with conditional edges matches iterative workflow | OpenAI strategy |
| Deterministic scoring before LLM | Prevents hallucination, ensures reproducibility | OpenAI strategy |
| Parallel API execution | Latency optimization; APIs are independent | Anthropic strategy |
| Streamlit UI | Fast to build, supports real-time updates for "thinking" panel | Gemini strategy |
| Multi-factor confidence | More robust than single-metric ranking | Anthropic strategy |
| Max 3 iterations | Prevents infinite loops; 3 is sufficient for most refinements | OpenAI strategy |
