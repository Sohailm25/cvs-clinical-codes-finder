# ABOUTME: Natural language parsing for clinical queries.
# ABOUTME: Extracts structured entities and provides ambiguity detection.

import json
from typing import Any

from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

from src.config import config


class ParsedQuery(BaseModel):
    """Structured extraction from a natural language clinical query."""

    # Extracted entities
    drug_name: str | None = Field(None, description="Drug/medication name if present")
    dose: str | None = Field(None, description="Dosage amount if present")
    unit: str | None = Field(None, description="Unit of measure if present")
    route: str | None = Field(None, description="Administration route if present")
    diagnosis: str | None = Field(None, description="Disease/condition name if present")
    lab_test: str | None = Field(None, description="Lab test name if present")
    phenotype: str | None = Field(None, description="Phenotypic trait if present")
    supply_item: str | None = Field(None, description="Medical supply/equipment if present")

    # Ambiguity detection
    ambiguity_reason: str | None = Field(
        None, description="Explanation of why query is ambiguous (if applicable)"
    )

    # Intent scores (should sum to approximately 1.0)
    intent_diagnosis: float = Field(0.0, ge=0.0, le=1.0)
    intent_laboratory: float = Field(0.0, ge=0.0, le=1.0)
    intent_medication: float = Field(0.0, ge=0.0, le=1.0)
    intent_supplies: float = Field(0.0, ge=0.0, le=1.0)
    intent_units: float = Field(0.0, ge=0.0, le=1.0)
    intent_phenotype: float = Field(0.0, ge=0.0, le=1.0)

    @property
    def primary_intent(self) -> str:
        """Return the intent with highest score."""
        intents = {
            "diagnosis": self.intent_diagnosis,
            "laboratory": self.intent_laboratory,
            "medication": self.intent_medication,
            "supplies": self.intent_supplies,
            "units": self.intent_units,
            "phenotype": self.intent_phenotype,
        }
        return max(intents, key=intents.get)

    @property
    def intent_scores_dict(self) -> dict[str, float]:
        """Return intent scores as a dictionary matching IntentScores format."""
        return {
            "diagnosis": self.intent_diagnosis,
            "laboratory": self.intent_laboratory,
            "medication": self.intent_medication,
            "supply_service": self.intent_supplies,
            "unit": self.intent_units,
            "phenotype": self.intent_phenotype,
        }


PARSING_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are a clinical coding expert. Analyze the query and extract structured information.

Extract any relevant entities you find:
- drug_name: Medication name (e.g., "metformin", "aspirin")
- dose: Numeric dosage (e.g., "500", "10-20")
- unit: Unit of measure (e.g., "mg", "mL", "mg/dL")
- route: Administration route (e.g., "oral", "IV", "topical")
- diagnosis: Disease or condition (e.g., "diabetes", "hypertension")
- lab_test: Laboratory test (e.g., "glucose test", "hemoglobin A1c")
- phenotype: Phenotypic trait or symptom (e.g., "ataxia", "tremor")
- supply_item: Medical supply or equipment (e.g., "wheelchair", "walker")

Classify the query intent with confidence scores (0.0-1.0, should roughly sum to 1.0):
- intent_diagnosis: Seeking disease/condition codes
- intent_laboratory: Seeking lab test codes
- intent_medication: Seeking drug codes
- intent_supplies: Seeking medical supply/service codes
- intent_units: Seeking unit of measure codes
- intent_phenotype: Seeking phenotype/symptom codes

If the query is ambiguous (could reasonably apply to 2+ domains), explain why in ambiguity_reason.

Respond with a JSON object only. Use null for fields with no value."""),
    ("human", "{query}"),
])


async def parse_query(query: str) -> ParsedQuery:
    """
    Parse a clinical query into structured entities and intent scores.

    Combines entity extraction and intent classification in a single LLM call
    for efficiency.

    Args:
        query: Raw clinical query string

    Returns:
        ParsedQuery with extracted entities and intent scores
    """
    llm = ChatOpenAI(
        model=config.OPENAI_MODEL,
        temperature=0,
        api_key=config.OPENAI_API_KEY,
    )

    chain = PARSING_PROMPT | llm

    try:
        response = await chain.ainvoke({"query": query})
        content = response.content.strip()

        # Handle markdown code blocks
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
            content = content.strip()

        data = json.loads(content)
        return ParsedQuery(**data)

    except Exception as e:
        # Return minimal parsed query on error
        return ParsedQuery(
            ambiguity_reason=f"Failed to parse query: {str(e)}"
        )


def needs_clarification(parsed: ParsedQuery, gap_threshold: float = 0.15) -> bool:
    """
    Check if a parsed query is ambiguous enough to warrant clarification.

    Clarification is triggered when:
    1. Top two intent scores differ by less than gap_threshold
    2. The top score is below 0.6 (not highly confident)

    Args:
        parsed: ParsedQuery from parse_query()
        gap_threshold: Maximum gap between top two scores to trigger clarification

    Returns:
        True if clarification should be requested
    """
    scores = [
        parsed.intent_diagnosis,
        parsed.intent_laboratory,
        parsed.intent_medication,
        parsed.intent_supplies,
        parsed.intent_units,
        parsed.intent_phenotype,
    ]
    sorted_scores = sorted(scores, reverse=True)

    if len(sorted_scores) < 2:
        return False

    gap = sorted_scores[0] - sorted_scores[1]
    top_score = sorted_scores[0]

    # Ambiguous if scores are close AND top isn't highly confident
    return gap < gap_threshold and top_score < 0.6


def get_clarification_options(parsed: ParsedQuery, threshold: float = 0.2) -> list[dict[str, str]]:
    """
    Get clarification options for an ambiguous query.

    Returns the top competing intents as options for the user to choose from.

    Args:
        parsed: ParsedQuery from parse_query()
        threshold: Minimum score to include as an option

    Returns:
        List of dicts with 'intent' and 'label' keys
    """
    intent_labels = {
        "diagnosis": "Search for diagnosis codes (ICD-10)",
        "laboratory": "Search for lab test codes (LOINC)",
        "medication": "Search for medication codes (RxTerms)",
        "supplies": "Search for supply/service codes (HCPCS)",
        "units": "Search for unit codes (UCUM)",
        "phenotype": "Search for phenotype codes (HPO)",
    }

    scores = {
        "diagnosis": parsed.intent_diagnosis,
        "laboratory": parsed.intent_laboratory,
        "medication": parsed.intent_medication,
        "supplies": parsed.intent_supplies,
        "units": parsed.intent_units,
        "phenotype": parsed.intent_phenotype,
    }

    # Get intents above threshold, sorted by score
    options = [
        {"intent": intent, "label": intent_labels[intent], "score": score}
        for intent, score in scores.items()
        if score >= threshold
    ]
    options.sort(key=lambda x: x["score"], reverse=True)

    # Return top 3 options max
    return [{"intent": o["intent"], "label": o["label"]} for o in options[:3]]
