# Clinical Tables API Reference

Local reference for Clinical Tables API endpoints used by Clinical Codes Finder.

## Base URL

```
https://clinicaltables.nlm.nih.gov/api/{table}/v3/search
```

## Common Query Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `terms` | Required | Search string (partial word matching, implicit AND for multiple words) |
| `maxList` | 7 | Max results (up to 500) |
| `count` | 7 | Page size (max 500) |
| `offset` | 0 | Starting result index (0-based) |
| `df` | varies | Display fields (comma-separated) |
| `sf` | varies | Searchable fields (comma-separated) |
| `cf` | varies | Code field identifier |
| `ef` | none | Extra fields to return (supports aliases via `field:alias`) |
| `q` | none | Advanced Elasticsearch query constraint |

**Pagination limit**: `offset + count <= 7,500`

## Response Format

All endpoints return a 5-element array:

```json
[
    total_count,        // 0: Total results (capped at 10,000)
    [codes...],         // 1: Array of code values
    {extra_fields...},  // 2: Hash of extra field data (from ef)
    [[display_strings...]],  // 3: Array of display strings per result
    [code_systems...]   // 4: Code system identifiers (optional)
]
```

---

## ICD-10-CM (Diagnosis Codes)

**Endpoint**: `/api/icd10cm/v3/search`

| Field | Description |
|-------|-------------|
| `code` | ICD-10-CM code (3-7 characters) |
| `name` | Long description |

**Defaults**:
- `df`: code, name
- `sf`: code
- `cf`: code

**Example**:
```
/api/icd10cm/v3/search?sf=code,name&terms=diabetes&maxList=10
```

---

## LOINC (Lab Tests, Measurements)

**Endpoint**: `/api/loinc_items/v3/search`

For basic LOINC codes, can also use: `/api/loinc/v3/search`

| Field | Description |
|-------|-------------|
| `LOINC_NUM` | LOINC code identifier |
| `LONG_COMMON_NAME` | Full descriptive name |
| `COMPONENT` | Primary component being measured |
| `SHORTNAME` | Abbreviated name |
| `PROPERTY` | LOINC property type |
| `METHOD_TYP` | Method type |
| `RELATEDNAMES2` | Synonyms |
| `text` | Algorithmically determined name |

**Defaults**:
- `df`: text
- `sf`: text, COMPONENT, CONSUMER_NAME, RELATEDNAMES2, METHOD_TYP, SHORTNAME, LONG_COMMON_NAME, LOINC_NUM
- `cf`: LOINC_NUM

**Special Parameters**:
- `type`: Filter by "question", "form", "panel"
- `available`: Set "true" for forms with definitions

**Example**:
```
/api/loinc_items/v3/search?terms=glucose&maxList=10&df=LOINC_NUM,LONG_COMMON_NAME
```

---

## RxTerms (Drug Names with Strengths)

**Endpoint**: `/api/rxterms/v3/search`

| Field | Description |
|-------|-------------|
| `DISPLAY_NAME` | Drug name + route |
| `STRENGTHS_AND_FORMS` | Available strength/form combinations |
| `RXCUIS` | RxNorm CUIs for DISPLAY_NAME + strength-form |
| `SXDG_RXCUI` | Semantic drug group RXCUI |
| `DISPLAY_NAME_SYNONYM` | Drug name synonyms |

**Defaults**:
- `df`: DISPLAY_NAME
- `sf`: DISPLAY_NAME, DISPLAY_NAME_SYNONYM
- `cf`: DISPLAY_NAME

**Example**:
```
/api/rxterms/v3/search?terms=metformin&maxList=10&ef=STRENGTHS_AND_FORMS,RXCUIS
```

---

## Drug Ingredients (RxNorm Ingredients)

**Endpoint**: `/api/drug_ingredients/v3/search`

| Field | Description |
|-------|-------------|
| `code` | RxNorm RXCUI |
| `name` | Drug ingredient name |

**Defaults**:
- `df`: name
- `sf`: name
- `cf`: code

**Note**: Pollen/extract items removed. Salt identifiers stripped from precise ingredients.

**Example**:
```
/api/drug_ingredients/v3/search?terms=metformin&maxList=10
```

---

## HCPCS (Medical Supplies/Services)

**Endpoint**: `/api/hcpcs/v3/search`

| Field | Description |
|-------|-------------|
| `code` | HCPCS code |
| `short_desc` | Short description |
| `long_desc` | Long description |
| `display` | Derived field (short_desc or long_desc) |
| `add_dt` | Addition date |
| `term_dt` | Termination date |
| `obsolete` | Boolean (true if terminated) |
| `is_noc` | Boolean (Not Otherwise Classified codes) |

**Defaults**:
- `df`: code, display
- `sf`: code, short_desc, long_desc
- `cf`: code

**Example**:
```
/api/hcpcs/v3/search?terms=wheelchair&maxList=10
```

---

## UCUM (Units of Measure)

**Endpoint**: `/api/ucum/v3/search`

| Field | Description |
|-------|-------------|
| `cs_code` | Case-sensitive unit code (e.g., "mg/dL") |
| `name` | Unit name |
| `category` | Clinical, Nonclinical, Constant, Obsolete |
| `synonyms` | Unit synonyms |
| `loinc_property` | Associated LOINC property |
| `guidance` | Unit description |
| `is_simple` | Boolean (simple unit without operators) |

**Defaults**:
- `df`: cs_code, name
- `sf`: cs_code, name, synonyms, cs_code_tokens
- `cf`: cs_code

**Note**: UCUM allows dynamic unit construction (e.g., kg/m2).

**Example**:
```
/api/ucum/v3/search?terms=mg/dL&maxList=10
```

---

## HPO (Human Phenotype Ontology)

**Endpoint**: `/api/hpo/v3/search`

| Field | Description |
|-------|-------------|
| `id` | HPO identifier (e.g., "HP:0001251") |
| `name` | Phenotype name |
| `definition` | Phenotype definition |
| `synonym` | Array of {term, relation, type, xref} |
| `is_a` | Parent terms [{id, name}] |
| `is_obsolete` | Boolean |
| `replaced_by` | Replacement ID if obsolete |

**Defaults**:
- `df`: id, name
- `sf`: id, name, synonym.term
- `cf`: id

**Example**:
```
/api/hpo/v3/search?terms=ataxia&maxList=10&ef=definition
```

---

## Notes on RxNorm

Full RxNorm is NOT available through Clinical Tables API. Options:

1. **RxTerms** (recommended): Use `/api/rxterms/v3/search` - includes RXCUI codes
2. **Drug Ingredients**: Use `/api/drug_ingredients/v3/search` - ingredient-level RXCUIs
3. **RxNav API** (external): `https://rxnav.nlm.nih.gov/REST/` - full RxNorm access

For this project, we use RxTerms as the primary drug lookup (satisfies "RxTerms / RxNorm" requirement).

---

## Rate Limits & Best Practices

- No explicit rate limits documented, but use reasonable request frequency
- Use `maxList` parameter to control result size
- Response times typically 100-500ms
- Cache responses when appropriate (same query within session)
- Handle HTTP errors gracefully (retry on 5xx, fail on 4xx)
