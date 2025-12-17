# ABOUTME: Intent classification node for the clinical codes agent.
# ABOUTME: Determines which coding systems are relevant for a given query.

import re
from typing import Any

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

from src.agent.state import AgentState, IntentScores, INTENT_TO_SYSTEMS
from src.config import config


# Rule-based patterns for fast classification
INTENT_PATTERNS: dict[str, list[re.Pattern]] = {
    "diagnosis": [
        re.compile(r"\b(disease|condition|syndrome|disorder)\b", re.I),
        re.compile(r"\b\w+(itis|osis|emia|pathy|plasia)\b", re.I),
        re.compile(r"\b(cancer|tumor|carcinoma|diabetes|hypertension)\b", re.I),
    ],
    "laboratory": [
        re.compile(r"\b(test|level|measurement|panel|assay)\b", re.I),
        re.compile(r"\b(blood|urine|serum|plasma|specimen)\b", re.I),
        re.compile(r"\b(glucose|hemoglobin|cholesterol|creatinine|a1c)\b", re.I),
    ],
    "medication": [
        re.compile(r"\b\d+\s*(mg|mcg|g|ml|unit)\b", re.I),
        re.compile(r"\b(tablet|capsule|injection|oral|topical)\b", re.I),
        re.compile(r"\b(metformin|aspirin|lisinopril|atorvastatin)\b", re.I),
    ],
    "supply_service": [
        re.compile(r"\b(wheelchair|crutch|walker|supply|DME|equipment)\b", re.I),
        re.compile(r"\b(prosthetic|orthotic|brace|splint)\b", re.I),
    ],
    "unit": [
        re.compile(r"\b(mg/dL|mmol/L|mL|cm|mm|kg)\b", re.I),
        re.compile(r"\b\w+/\w+\b"),  # Fraction-like units
        re.compile(r"\bper\s+(liter|minute|hour|day)\b", re.I),
    ],
    "phenotype": [
        re.compile(r"\b(symptom|trait|feature|abnormal)\b", re.I),
        re.compile(r"\b(ataxia|dystonia|seizure|tremor)\b", re.I),
        re.compile(r"\b(phenotype|clinical feature)\b", re.I),
    ],
}

CLASSIFICATION_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are a clinical coding expert. Classify the user's query into relevant medical coding domains.

For each domain, provide a confidence score from 0.0 to 1.0:
- diagnosis: Diseases, conditions, syndromes (ICD-10-CM)
- laboratory: Lab tests, measurements, panels (LOINC)
- medication: Drugs, dosages, formulations (RxTerms/RxNorm)
- supply_service: Medical supplies, DME, services (HCPCS)
- unit: Units of measure like mg/dL, mmol/L (UCUM)
- phenotype: Symptoms, traits, phenotypic features (HPO)

Respond ONLY with a JSON object like:
{{"diagnosis": 0.0, "laboratory": 0.0, "medication": 0.0, "supply_service": 0.0, "unit": 0.0, "phenotype": 0.0}}"""),
    ("human", "{query}"),
])


def apply_rule_based_classification(query: str) -> IntentScores:
    """Apply rule-based pattern matching for fast classification."""
    scores = IntentScores(
        diagnosis=0.0,
        laboratory=0.0,
        medication=0.0,
        supply_service=0.0,
        unit=0.0,
        phenotype=0.0,
    )

    for intent, patterns in INTENT_PATTERNS.items():
        matches = sum(1 for p in patterns if p.search(query))
        if matches > 0:
            # Score based on number of pattern matches
            scores[intent] = min(0.3 + (matches * 0.2), 0.9)

    return scores


async def classify_with_llm(query: str) -> IntentScores:
    """Use LLM for semantic classification."""
    llm = ChatOpenAI(
        model=config.OPENAI_MODEL,
        temperature=0,
        api_key=config.OPENAI_API_KEY,
    )

    chain = CLASSIFICATION_PROMPT | llm

    try:
        response = await chain.ainvoke({"query": query})
        content = response.content.strip()

        # Parse JSON response
        import json
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
        scores = json.loads(content)

        return IntentScores(
            diagnosis=float(scores.get("diagnosis", 0.0)),
            laboratory=float(scores.get("laboratory", 0.0)),
            medication=float(scores.get("medication", 0.0)),
            supply_service=float(scores.get("supply_service", 0.0)),
            unit=float(scores.get("unit", 0.0)),
            phenotype=float(scores.get("phenotype", 0.0)),
        )
    except Exception:
        # Fall back to empty scores on error
        return IntentScores(
            diagnosis=0.0,
            laboratory=0.0,
            medication=0.0,
            supply_service=0.0,
            unit=0.0,
            phenotype=0.0,
        )


def merge_scores(
    rule_scores: IntentScores,
    llm_scores: IntentScores,
    rule_weight: float = 0.3,
) -> IntentScores:
    """Merge rule-based and LLM scores with weighted average."""
    llm_weight = 1.0 - rule_weight

    return IntentScores(
        diagnosis=rule_scores["diagnosis"] * rule_weight + llm_scores["diagnosis"] * llm_weight,
        laboratory=rule_scores["laboratory"] * rule_weight + llm_scores["laboratory"] * llm_weight,
        medication=rule_scores["medication"] * rule_weight + llm_scores["medication"] * llm_weight,
        supply_service=rule_scores["supply_service"] * rule_weight + llm_scores["supply_service"] * llm_weight,
        unit=rule_scores["unit"] * rule_weight + llm_scores["unit"] * llm_weight,
        phenotype=rule_scores["phenotype"] * rule_weight + llm_scores["phenotype"] * llm_weight,
    )


def select_systems(scores: IntentScores, threshold: float = 0.3) -> list[str]:
    """Select coding systems based on intent scores."""
    systems: set[str] = set()

    for intent, score in scores.items():
        if score >= threshold:
            systems.update(INTENT_TO_SYSTEMS.get(intent, []))

    return sorted(systems)


async def classify_node(state: AgentState) -> dict[str, Any]:
    """
    LangGraph node: Classify query intent and select relevant coding systems.

    Returns updates to state with intent_scores, selected_systems, search_terms.
    """
    query = state["query"]

    # Rule-based classification (fast)
    rule_scores = apply_rule_based_classification(query)

    # Check if high confidence from rules alone
    max_rule_score = max(rule_scores.values())

    if max_rule_score >= 0.7:
        # High confidence from rules, skip LLM
        final_scores = rule_scores
        reasoning = f"Classified query using pattern matching (high confidence: {max_rule_score:.2f})"
    else:
        # Use LLM for semantic classification
        llm_scores = await classify_with_llm(query)
        final_scores = merge_scores(rule_scores, llm_scores)
        reasoning = f"Classified query using LLM + patterns (merged scores)"

    # Select systems above threshold
    selected = select_systems(final_scores, config.CONFIDENCE_THRESHOLD)

    # If no systems selected, use a default based on highest score
    if not selected:
        highest_intent = max(final_scores, key=lambda k: final_scores[k])
        selected = INTENT_TO_SYSTEMS.get(highest_intent, ["ICD-10-CM"])
        reasoning += f"; defaulted to {highest_intent} systems"

    return {
        "intent_scores": final_scores,
        "selected_systems": selected,
        "search_terms": [query],  # Initial search term is the raw query
        "reasoning_trace": [reasoning],
    }
