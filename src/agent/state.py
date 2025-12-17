# ABOUTME: State schema for the Clinical Codes Finder agent.
# ABOUTME: Defines the TypedDict structure passed between LangGraph nodes.

from typing import TypedDict, Annotated
from operator import add

from src.tools.base import CodeResult


class IntentScores(TypedDict):
    """Confidence scores for each intent domain."""

    diagnosis: float
    laboratory: float
    medication: float
    supply_service: float
    unit: float
    phenotype: float


class AgentState(TypedDict):
    """State maintained throughout agent execution."""

    # Input
    query: str

    # Classification
    intent_scores: IntentScores
    selected_systems: list[str]

    # Planning
    search_terms: list[str]

    # Execution tracking
    iteration: int
    api_calls: Annotated[list[dict], add]
    raw_results: dict[str, list[dict]]

    # Reflection
    coverage_assessment: str
    needs_refinement: bool
    refinement_strategy: str | None

    # Output
    consolidated_results: list[CodeResult]
    summary: str
    reasoning_trace: Annotated[list[str], add]


def create_initial_state(query: str) -> AgentState:
    """Create initial state for a new query."""
    return AgentState(
        query=query,
        intent_scores=IntentScores(
            diagnosis=0.0,
            laboratory=0.0,
            medication=0.0,
            supply_service=0.0,
            unit=0.0,
            phenotype=0.0,
        ),
        selected_systems=[],
        search_terms=[],
        iteration=0,
        api_calls=[],
        raw_results={},
        coverage_assessment="",
        needs_refinement=False,
        refinement_strategy=None,
        consolidated_results=[],
        summary="",
        reasoning_trace=[],
    )


# Mapping from intent domains to coding systems
INTENT_TO_SYSTEMS: dict[str, list[str]] = {
    "diagnosis": ["ICD-10-CM", "HPO"],
    "laboratory": ["LOINC", "UCUM"],
    "medication": ["RxTerms"],
    "supply_service": ["HCPCS"],
    "unit": ["UCUM"],
    "phenotype": ["HPO"],
}

# Mapping from system names to tool classes
SYSTEM_TO_TOOL: dict[str, str] = {
    "ICD-10-CM": "ICD10Tool",
    "LOINC": "LOINCTool",
    "RxTerms": "RxTermsTool",
    "HCPCS": "HCPCSTool",
    "UCUM": "UCUMTool",
    "HPO": "HPOTool",
}
