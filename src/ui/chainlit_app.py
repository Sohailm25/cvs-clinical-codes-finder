# ABOUTME: Chainlit chat interface for Clinical Codes Finder.
# ABOUTME: ChatGPT-style UI with streaming steps and settings panel.

import csv
import io
from datetime import datetime

import chainlit as cl
from chainlit.data import get_data_layer
from passlib.hash import bcrypt

from src.agent.graph import run_agent_streaming
from src.config import config
from src.ui.data_layer import FileDataLayer

# Validate configuration at module load
config.validate()

# User credentials: {username: bcrypt_hash}
# To generate a new hash, run: python -c "from passlib.hash import bcrypt; print(bcrypt.hash('your_password'))"
USERS = {
    "admin": "$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4.q/AEb0OZIOV1Cm",  # default: "changeme"
}


# Register the file-based data layer for thread persistence
@cl.data_layer
def get_file_data_layer():
    return FileDataLayer()


@cl.password_auth_callback
def auth_callback(username: str, password: str):
    """Authenticate users against stored bcrypt password hashes."""
    if username in USERS:
        if bcrypt.verify(password, USERS[username]):
            return cl.User(
                identifier=username,
                metadata={"role": "user", "provider": "credentials"},
            )
    return None


def _sanitize_csv_value(val: str) -> str:
    """Sanitize CSV values to prevent formula injection in spreadsheet applications."""
    if val and val[0] in "=+@-":
        return f"'{val}"
    return val


def get_confidence_badge(confidence: float) -> str:
    """Get a percentage badge based on confidence level."""
    pct = int(confidence * 100)
    return f"{pct}%"


def get_follow_up_suggestions(results: list, query: str) -> list[cl.Action]:
    """Generate contextual follow-up suggestion buttons based on search results."""
    suggestions = []

    def get_attr(r, key):
        if isinstance(r, dict):
            return r.get(key)
        return getattr(r, key, None)

    # Collect systems found
    systems_found = set()
    for r in results:
        system = get_attr(r, "system")
        if system:
            systems_found.add(system)

    # ICD-10 follow-ups
    if "ICD-10-CM" in systems_found:
        top_icd = next((r for r in results if get_attr(r, "system") == "ICD-10-CM"), None)
        if top_icd:
            code = get_attr(top_icd, "code")
            display = get_attr(top_icd, "display") or ""
            short_display = display[:25] + "..." if len(display) > 25 else display

            suggestions.append(cl.Action(
                name="followup",
                payload={"type": "meds_for_diagnosis", "code": code, "display": display},
                label=f"Medications for {short_display}",
            ))
            suggestions.append(cl.Action(
                name="followup",
                payload={"type": "check_billable", "code": code},
                label=f"Is {code} billable?",
            ))

    # RxTerms follow-ups
    if "RxTerms" in systems_found:
        top_rx = next((r for r in results if get_attr(r, "system") == "RxTerms"), None)
        if top_rx:
            code = get_attr(top_rx, "code")
            display = get_attr(top_rx, "display") or ""
            short_display = display[:20] + "..." if len(display) > 20 else display

            suggestions.append(cl.Action(
                name="followup",
                payload={"type": "other_strengths", "code": code, "display": display, "query": query},
                label=f"Other forms of {short_display}",
            ))
            suggestions.append(cl.Action(
                name="followup",
                payload={"type": "diagnosis_for_drug", "display": display, "query": query},
                label="What diagnosis supports this?",
            ))

    # LOINC follow-ups
    if "LOINC" in systems_found:
        top_loinc = next((r for r in results if get_attr(r, "system") == "LOINC"), None)
        if top_loinc:
            display = get_attr(top_loinc, "display") or ""

            suggestions.append(cl.Action(
                name="followup",
                payload={"type": "loinc_unit", "display": display, "query": query},
                label="What unit is this measured in?",
            ))

    # HCPCS follow-ups
    if "HCPCS" in systems_found:
        top_hcpcs = next((r for r in results if get_attr(r, "system") == "HCPCS"), None)
        if top_hcpcs:
            code = get_attr(top_hcpcs, "code")

            suggestions.append(cl.Action(
                name="followup",
                payload={"type": "hcpcs_diagnosis", "code": code, "query": query},
                label="What diagnosis codes pair with this?",
            ))

    return suggestions[:4]  # Max 4 suggestions


def get_bundle_actions(results: list) -> list[cl.Action]:
    """Generate 'Add to bundle' buttons for top results from each system."""
    actions = []

    def get_attr(r, key):
        if isinstance(r, dict):
            return r.get(key)
        return getattr(r, key, None)

    # Get top result from each system
    seen_systems = set()
    for r in results:
        system = get_attr(r, "system")
        if system and system not in seen_systems:
            seen_systems.add(system)
            code = get_attr(r, "code")
            display = get_attr(r, "display") or ""
            short_display = display[:20] + "..." if len(display) > 20 else display

            actions.append(cl.Action(
                name="add_to_bundle",
                payload={"system": system, "code": code, "display": display},
                label=f"Add {code} to bundle",
            ))

            if len(actions) >= 3:  # Max 3 add-to-bundle buttons
                break

    return actions


def format_empty_results(query: str, systems_searched: list) -> str:
    """Format a helpful message when no results are found."""
    systems_str = ", ".join(systems_searched) if systems_searched else "all systems"

    return f"""

### No results found

We searched {len(systems_searched) if systems_searched else "multiple"} systems for "{query}" but didn't find matches.

**Try:**
- Use more specific medical terms (e.g., "type 2 diabetes" instead of "diabetes")
- Check spelling of clinical terms
- Enable "Multi-hop reasoning" in settings to search related terms

**Systems searched**: {systems_str}
"""


def format_results(
    results: list,
    hierarchy_info: dict = None,
    show_hierarchy: bool = False,
    query: str = "",
    systems_searched: list = None,
) -> str:
    """Format results as markdown for Chainlit display."""
    if not results:
        return format_empty_results(query, systems_searched or [])

    def get_attr(r, key):
        if isinstance(r, dict):
            return r.get(key)
        return getattr(r, key, None)

    # Group by system
    by_system: dict[str, list] = {}
    for r in results:
        system = get_attr(r, "system") or "Unknown"
        if system not in by_system:
            by_system[system] = []
        by_system[system].append(r)

    output = []
    # Sort systems by result count (most results first)
    sorted_systems = sorted(by_system.items(), key=lambda x: len(x[1]), reverse=True)

    for idx, (system, items) in enumerate(sorted_systems):
        output.append(f"\n\n### {system} ({len(items)} results)")
        for r in items:
            code = get_attr(r, "code")
            display = get_attr(r, "display")
            confidence = get_attr(r, "confidence") or 0.0
            badge = get_confidence_badge(confidence)

            result_line = f"\n- `{code}` **{display}** {badge}"

            # Show system-specific metadata if available
            metadata = get_attr(r, "metadata") or {}
            if metadata:
                meta_parts = []
                # LOINC metadata
                if system == "LOINC":
                    if metadata.get("COMPONENT"):
                        meta_parts.append(f"Component: {metadata['COMPONENT']}")
                    if metadata.get("PROPERTY"):
                        meta_parts.append(f"Property: {metadata['PROPERTY']}")
                    if metadata.get("METHOD_TYP"):
                        meta_parts.append(f"Method: {metadata['METHOD_TYP']}")
                # HPO metadata
                elif system == "HPO":
                    defn = metadata.get("definition")
                    if defn:
                        # Truncate long definitions
                        defn_text = defn[0] if isinstance(defn, list) else defn
                        if len(defn_text) > 100:
                            defn_text = defn_text[:100] + "..."
                        meta_parts.append(f"Definition: {defn_text}")
                # RxTerms metadata
                elif system == "RxTerms":
                    if metadata.get("STRENGTHS_AND_FORMS"):
                        forms = metadata["STRENGTHS_AND_FORMS"]
                        if isinstance(forms, list):
                            forms = ", ".join(forms[:3])
                        meta_parts.append(f"Forms: {forms}")

                if meta_parts:
                    result_line += f"\n  - *{' | '.join(meta_parts)}*"

            # Show hierarchy if enabled and available
            if show_hierarchy and hierarchy_info and code in hierarchy_info:
                parent = hierarchy_info[code]
                parent_code = parent.get("parent_code")
                parent_display = parent.get("parent_display")
                if parent_code and parent_display:
                    result_line += f"\n  - > Parent: `{parent_code}` {parent_display}"

            output.append(result_line)

    return "".join(output)


def generate_csv(results: list, query: str) -> str:
    """Generate CSV content from results."""
    output = io.StringIO()
    writer = csv.writer(output)

    # Write header
    writer.writerow(["Code", "Display", "System", "Confidence", "Query"])

    def get_attr(r, key):
        if isinstance(r, dict):
            return r.get(key)
        return getattr(r, key, None)

    for r in results:
        writer.writerow([
            _sanitize_csv_value(get_attr(r, "code") or ""),
            _sanitize_csv_value(get_attr(r, "display") or ""),
            _sanitize_csv_value(get_attr(r, "system") or ""),
            f"{(get_attr(r, 'confidence') or 0.0):.2f}",
            _sanitize_csv_value(query),
        ])

    return output.getvalue()


@cl.action_callback("export_csv")
async def on_export_csv(action: cl.Action):
    """Handle CSV export button click."""
    results = cl.user_session.get("last_results", [])
    query = cl.user_session.get("last_query", "search")

    if not results:
        await cl.Message(content="No results to export.").send()
        return

    csv_content = generate_csv(results, query)

    # Create file element
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"clinical_codes_{timestamp}.csv"

    elements = [
        cl.File(
            name=filename,
            content=csv_content.encode("utf-8"),
            display="inline",
        )
    ]

    await cl.Message(
        content=f"Exported {len(results)} results to CSV:",
        elements=elements,
    ).send()


@cl.action_callback("followup")
async def on_followup(action: cl.Action):
    """Handle follow-up suggestion button clicks."""
    followup_type = action.payload.get("type")
    settings = cl.user_session.get("settings", {})
    multi_hop_enabled = settings.get("multi_hop_enabled", False)
    show_hierarchy = settings.get("show_hierarchy", True)

    if followup_type == "meds_for_diagnosis":
        # Search RxTerms for medications related to the diagnosis
        display = action.payload.get("display", "")

        # Extract meaningful medical term from the display
        # Remove common ICD-10 prefixes that don't help with drug search
        prefixes_to_strip = [
            "family history of", "personal history of", "encounter for",
            "screening for", "supervision of", "sequelae of", "other",
            "unspecified", "type 1", "type 2", "with", "without",
        ]
        query_term = display.lower()
        for prefix in prefixes_to_strip:
            if query_term.startswith(prefix):
                query_term = query_term[len(prefix):].strip()

        # Also try to extract the core medical term (last significant words)
        # e.g., "Family history of leukemia" → "leukemia"
        words = query_term.split()
        if len(words) > 3:
            # Take last 2-3 meaningful words
            query_term = " ".join(words[-2:])
        elif not query_term:
            # Fallback to original display
            query_term = display

        query = query_term.strip()

        await cl.Message(content=f"Searching for medications to treat: **{query}**").send()

        final_state = {}
        async with cl.Step(name="Processing", type="tool") as parent_step:
            parent_step.input = query

            async for event in run_agent_streaming(
                query,
                multi_hop_enabled=True,  # Use multi-hop for better drug discovery
                user_clarification="medication",
            ):
                for key, value in event["state"].items():
                    if key in final_state and isinstance(final_state[key], list) and isinstance(value, list):
                        final_state[key].extend(value)
                    else:
                        final_state[key] = value

            results_count = len(final_state.get("consolidated_results", []))
            parent_step.output = f"Found {results_count} medication results"

        results = final_state.get("consolidated_results", [])
        cl.user_session.set("last_results", results)
        cl.user_session.set("last_query", query)

        output = f"**Medications for: {query}**\n"
        if not results:
            output += f"\nNo medications found for '{query}'. This diagnosis may not have direct drug treatments, or try a more specific search term."
        else:
            output += format_results(results, {}, False, query, ["RxTerms"])

        actions = get_follow_up_suggestions(results, query)
        actions.extend(get_bundle_actions(results))
        if results:
            actions.append(cl.Action(name="export_csv", payload={}, label="Export to CSV"))

        await cl.Message(content=output, actions=actions[:6]).send()

    elif followup_type == "check_billable":
        # Check if ICD-10 code is billable (specific enough)
        import asyncio
        code = action.payload.get("code", "")

        # A code is billable if it's at maximum specificity
        # ICD-10-CM billability rules:
        # - Codes without decimals (3 chars) are category codes - NOT billable
        # - Codes with decimals need to be at highest specificity available
        has_decimal = "." in code
        decimal_part = code.split(".")[-1] if has_decimal else ""

        # Check code length pattern
        if not has_decimal:
            billable = False
            message = f"**{code}** is a **category code** (not billable)\n\nCategory codes are too broad for billing. You need a more specific code with a decimal."
        elif len(decimal_part) < 1:
            billable = False
            message = f"**{code}** needs **more specificity**\n\nAdd more digits after the decimal for billing."
        else:
            billable = True
            message = f"**{code}** appears to be **billable** (has decimal specificity)"

        # Try to fetch hierarchy info with timeout
        try:
            from src.agent.multi_hop import fetch_icd10_parent
            hierarchy = await asyncio.wait_for(
                fetch_icd10_parent(code),
                timeout=5.0  # 5 second timeout
            )
            if hierarchy:
                parent_code = hierarchy.get("parent_code")
                parent_display = hierarchy.get("parent_display")
                if parent_code:
                    message += f"\n\n**Parent category**: `{parent_code}` {parent_display}"
        except asyncio.TimeoutError:
            message += "\n\n*(Hierarchy lookup timed out)*"
        except Exception as e:
            pass  # Silently ignore hierarchy errors

        # Suggest searching for more specific codes
        if not billable:
            message += f"\n\n*Tip: Search for '{code}' to see more specific codes*"

        await cl.Message(content=message).send()

    elif followup_type == "other_strengths":
        # Search for other forms/strengths of the same drug
        display = action.payload.get("display", "")
        # Extract drug name (usually first word or two)
        drug_name = display.split()[0] if display else action.payload.get("query", "")

        await cl.Message(content=f"Searching for other forms of: **{drug_name}**").send()

        final_state = {}
        async with cl.Step(name="Processing", type="tool") as parent_step:
            parent_step.input = drug_name

            async for event in run_agent_streaming(
                drug_name,
                multi_hop_enabled=False,
                user_clarification="medication",
            ):
                for key, value in event["state"].items():
                    if key in final_state and isinstance(final_state[key], list) and isinstance(value, list):
                        final_state[key].extend(value)
                    else:
                        final_state[key] = value

            results_count = len(final_state.get("consolidated_results", []))
            parent_step.output = f"Found {results_count} results"

        results = final_state.get("consolidated_results", [])
        cl.user_session.set("last_results", results)
        cl.user_session.set("last_query", drug_name)

        output = f"**Forms and strengths of: {drug_name}**\n"
        output += format_results(results, {}, False, drug_name, ["RxTerms"])

        actions = get_bundle_actions(results)
        if results:
            actions.append(cl.Action(name="export_csv", payload={}, label="Export to CSV"))

        await cl.Message(content=output, actions=actions).send()

    elif followup_type == "diagnosis_for_drug":
        # Search for diagnoses that support a drug
        display = action.payload.get("display", "")
        drug_name = display.split()[0] if display else ""

        await cl.Message(content=f"Searching for diagnoses related to: **{drug_name}**").send()

        # Common drug-to-indication mappings (simplified)
        query = f"{drug_name} indication diagnosis"

        final_state = {}
        async with cl.Step(name="Processing", type="tool") as parent_step:
            parent_step.input = query

            async for event in run_agent_streaming(
                drug_name,
                multi_hop_enabled=True,  # Use multi-hop for drug→diagnosis
                user_clarification="diagnosis",
            ):
                for key, value in event["state"].items():
                    if key in final_state and isinstance(final_state[key], list) and isinstance(value, list):
                        final_state[key].extend(value)
                    else:
                        final_state[key] = value

            results_count = len(final_state.get("consolidated_results", []))
            parent_step.output = f"Found {results_count} results"

        results = final_state.get("consolidated_results", [])
        cl.user_session.set("last_results", results)
        cl.user_session.set("last_query", query)

        output = f"**Diagnoses related to: {drug_name}**\n"
        output += format_results(results, {}, False, query, ["ICD-10-CM"])

        actions = get_bundle_actions(results)
        if results:
            actions.append(cl.Action(name="export_csv", payload={}, label="Export to CSV"))

        await cl.Message(content=output, actions=actions).send()

    elif followup_type == "loinc_unit":
        # Search for UCUM units related to the LOINC test
        display = action.payload.get("display", "")
        query = action.payload.get("query", display)

        await cl.Message(content=f"Searching for units related to: **{display}**").send()

        final_state = {}
        async with cl.Step(name="Processing", type="tool") as parent_step:
            parent_step.input = f"{query} unit"

            async for event in run_agent_streaming(
                f"{query} unit",
                multi_hop_enabled=False,
                user_clarification="units",
            ):
                for key, value in event["state"].items():
                    if key in final_state and isinstance(final_state[key], list) and isinstance(value, list):
                        final_state[key].extend(value)
                    else:
                        final_state[key] = value

            results_count = len(final_state.get("consolidated_results", []))
            parent_step.output = f"Found {results_count} results"

        results = final_state.get("consolidated_results", [])

        output = f"**Units for: {display}**\n"
        output += format_results(results, {}, False, query, ["UCUM"])

        await cl.Message(content=output).send()

    elif followup_type == "hcpcs_diagnosis":
        # Search for ICD-10 codes that pair with HCPCS
        code = action.payload.get("code", "")
        query = action.payload.get("query", "")

        await cl.Message(content=f"Searching for diagnoses that pair with **{code}**...").send()

        final_state = {}
        async with cl.Step(name="Processing", type="tool") as parent_step:
            parent_step.input = query

            async for event in run_agent_streaming(
                query,
                multi_hop_enabled=True,
                user_clarification="diagnosis",
            ):
                for key, value in event["state"].items():
                    if key in final_state and isinstance(final_state[key], list) and isinstance(value, list):
                        final_state[key].extend(value)
                    else:
                        final_state[key] = value

            results_count = len(final_state.get("consolidated_results", []))
            parent_step.output = f"Found {results_count} results"

        results = final_state.get("consolidated_results", [])
        cl.user_session.set("last_results", results)
        cl.user_session.set("last_query", query)

        output = f"**Diagnoses that pair with {code}**\n"
        output += format_results(results, {}, False, query, ["ICD-10-CM"])

        actions = get_bundle_actions(results)
        if results:
            actions.append(cl.Action(name="export_csv", payload={}, label="Export to CSV"))

        await cl.Message(content=output, actions=actions).send()


@cl.action_callback("add_to_bundle")
async def on_add_to_bundle(action: cl.Action):
    """Handle adding a code to the user's bundle - compact notification."""
    system = action.payload.get("system", "")
    code = action.payload.get("code", "")
    display = action.payload.get("display", "")

    bundle = cl.user_session.get("code_bundle", [])

    # Check if already in bundle
    for item in bundle:
        if item["code"] == code and item["system"] == system:
            # Brief inline notification - no new message needed
            return

    # Add to bundle
    bundle.append({"system": system, "code": code, "display": display})
    cl.user_session.set("code_bundle", bundle)

    # Compact inline confirmation with quick actions
    codes_list = ", ".join([f"`{b['code']}`" for b in bundle])
    actions = [
        cl.Action(name="export_bundle", payload={}, label="Export"),
        cl.Action(name="clear_bundle", payload={}, label="Clear"),
    ]

    await cl.Message(
        content=f"**Bundle** ({len(bundle)}): {codes_list}",
        actions=actions,
    ).send()


@cl.action_callback("view_bundle")
async def on_view_bundle(action: cl.Action):
    """Show the current code bundle - compact format."""
    bundle = cl.user_session.get("code_bundle", [])

    if not bundle:
        await cl.Message(content="Bundle is empty").send()
        return

    # Compact single-line format
    lines = [f"**Code Bundle** ({len(bundle)} codes):"]
    for item in bundle:
        short_display = item['display'][:40] + "..." if len(item['display']) > 40 else item['display']
        lines.append(f"- `{item['code']}` ({item['system']}): {short_display}")

    actions = [
        cl.Action(name="export_bundle", payload={}, label="Export CSV"),
        cl.Action(name="clear_bundle", payload={}, label="Clear"),
    ]

    await cl.Message(content="\n".join(lines), actions=actions).send()


@cl.action_callback("export_bundle")
async def on_export_bundle(action: cl.Action):
    """Export the code bundle as CSV."""
    bundle = cl.user_session.get("code_bundle", [])

    if not bundle:
        await cl.Message(content="Bundle is empty").send()
        return

    # Generate CSV
    csv_output = io.StringIO()
    writer = csv.writer(csv_output)
    writer.writerow(["Code", "System", "Display"])
    for item in bundle:
        writer.writerow([
            _sanitize_csv_value(item["code"]),
            _sanitize_csv_value(item["system"]),
            _sanitize_csv_value(item["display"]),
        ])

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"code_bundle_{timestamp}.csv"

    elements = [
        cl.File(
            name=filename,
            content=csv_output.getvalue().encode("utf-8"),
            display="inline",
        )
    ]

    await cl.Message(
        content=f"Bundle exported ({len(bundle)} codes):",
        elements=elements,
    ).send()


@cl.action_callback("clear_bundle")
async def on_clear_bundle(action: cl.Action):
    """Clear the code bundle."""
    cl.user_session.set("code_bundle", [])
    await cl.Message(content="Bundle cleared.").send()


@cl.on_chat_start
async def on_start():
    """Initialize chat session with welcome message and settings."""
    # Set default settings with helpful descriptions
    settings = await cl.ChatSettings([
        cl.input_widget.Switch(
            id="clarification_enabled",
            label="Ask clarifying questions",
            description="Ask what type of code you're looking for when your query is ambiguous",
            initial=True,
        ),
        cl.input_widget.Switch(
            id="multi_hop_enabled",
            label="Multi-hop reasoning",
            description="Search for related clinical terms (e.g., diabetes → glucose tests)",
            initial=False,
        ),
        cl.input_widget.Switch(
            id="show_hierarchy",
            label="Show code hierarchy",
            description="Show parent codes for ICD-10 results (e.g., E11.65 → E11)",
            initial=True,
        ),
    ]).send()

    cl.user_session.set("settings", settings)

    # Welcome message
    await cl.Message(
        content="## What clinical code are you looking for?\n\n"
                "Search across **ICD-10-CM**, **LOINC**, **RxTerms**, **HCPCS**, **UCUM**, and **HPO**.\n\n"
                "Try queries like:\n"
                "- `diabetes` - diagnosis codes\n"
                "- `glucose test` - lab test codes\n"
                "- `metformin 500 mg` - medication codes\n"
                "- `wheelchair` - supply/service codes\n\n"
                "*Tip: Try an ambiguous query like `iron` to see clarification in action.*"
    ).send()


@cl.on_settings_update
async def on_settings_update(settings):
    """Handle settings toggle changes."""
    cl.user_session.set("settings", settings)


@cl.on_message
async def on_message(message: cl.Message):
    """Handle user queries with streaming agent execution."""
    settings = cl.user_session.get("settings", {})
    query = message.content

    multi_hop_enabled = settings.get("multi_hop_enabled", False)
    show_hierarchy = settings.get("show_hierarchy", True)

    final_state = {}

    # Use Steps for streaming visualization
    async with cl.Step(name="Processing", type="tool") as parent_step:
        parent_step.input = query

        async for event in run_agent_streaming(
            query,
            multi_hop_enabled=multi_hop_enabled,
        ):
            node = event["node"]
            state_update = event["state"]

            # Merge state into final state (append lists instead of replacing)
            for key, value in state_update.items():
                if key in final_state and isinstance(final_state[key], list) and isinstance(value, list):
                    final_state[key].extend(value)
                else:
                    final_state[key] = value

        # Set parent step output with reasoning trace
        results_count = len(final_state.get("consolidated_results", []))
        reasoning_trace = final_state.get("reasoning_trace", [])
        if reasoning_trace:
            trace_text = "\n".join(f"• {step}" for step in reasoning_trace)
            parent_step.output = f"Found {results_count} results\n\n**How we found these:**\n{trace_text}"
        else:
            parent_step.output = f"Found {results_count} results"

    # Check if clarification is needed
    if settings.get("clarification_enabled", True) and final_state.get("clarification_needed"):
        await handle_clarification_request(query, final_state)
        return

    # Format and display final results
    summary = final_state.get("summary", "Search completed.")
    results = final_state.get("consolidated_results", [])
    hierarchy_info = final_state.get("hierarchy_info", {})
    related_terms = final_state.get("related_terms", [])
    systems_searched = final_state.get("selected_systems", [])

    # Store results for export
    cl.user_session.set("last_results", results)
    cl.user_session.set("last_query", query)

    # Build output message
    output_parts = []

    # Add LLM summary at the top if available
    if summary and summary != "Search completed.":
        output_parts.append(summary)
        output_parts.append("\n\n---\n")  # Separator

    # Add formatted results (this has percentage badges, metadata, etc.)
    output_parts.append(format_results(results, hierarchy_info, show_hierarchy, query, systems_searched))

    # Show multi-hop expansion info if used
    if multi_hop_enabled and related_terms:
        output_parts.append(f"\n\n**Multi-hop expansion**: Searched for related terms: {', '.join(related_terms[:5])}")
        if len(related_terms) > 5:
            output_parts.append(f" (+{len(related_terms)-5} more)")

    # Add search details footer
    search_terms = final_state.get("search_terms", [query])
    if systems_searched:
        output_parts.append(f"\n\n---\n*Searched: {', '.join(search_terms[:5])} across {', '.join(systems_searched)}*")

    # Create actions: follow-up suggestions + bundle + export
    actions = []
    if results:
        # Add follow-up suggestions based on results
        actions.extend(get_follow_up_suggestions(results, query))

        # Add bundle actions (top result from each system)
        actions.extend(get_bundle_actions(results))

        # Add export action
        actions.append(
            cl.Action(
                name="export_csv",
                payload={},
                label="Export to CSV",
            )
        )

        # Show bundle status if user has codes in bundle
        bundle = cl.user_session.get("code_bundle", [])
        if bundle:
            actions.append(
                cl.Action(
                    name="view_bundle",
                    payload={},
                    label=f"View bundle ({len(bundle)})",
                )
            )

    await cl.Message(content="".join(output_parts), actions=actions[:8]).send()


async def handle_clarification_request(query: str, state: dict):
    """Handle clarification when intent is ambiguous."""
    options = state.get("clarification_options", [])

    # Store pending query for clarification callback
    cl.user_session.set("pending_query", query)

    # Create action buttons for each option
    actions = []
    for opt in options:
        actions.append(
            cl.Action(
                name="clarify",
                payload={"intent": opt["intent"], "query": query},
                label=opt["label"],
            )
        )

    # Add "Search all" option
    actions.append(
        cl.Action(
            name="clarify",
            payload={"intent": "all", "query": query},
            label="Search all systems",
        )
    )

    await cl.Message(
        content="This query could apply to multiple coding systems. What are you looking for?",
        actions=actions,
    ).send()


@cl.action_callback("clarify")
async def on_clarify(action: cl.Action):
    """Handle clarification button clicks."""
    intent = action.payload.get("intent")
    query = action.payload.get("query")
    settings = cl.user_session.get("settings", {})

    multi_hop_enabled = settings.get("multi_hop_enabled", False)
    show_hierarchy = settings.get("show_hierarchy", True)

    # Show user's choice
    intent_labels = {
        "diagnosis": "diagnosis codes",
        "laboratory": "lab test codes",
        "medication": "medication codes",
        "supplies": "supply/service codes",
        "units": "unit codes",
        "phenotype": "phenotype codes",
        "all": "all relevant systems",
    }
    await cl.Message(content=f"Searching for {intent_labels.get(intent, intent)}...").send()

    final_state = {}

    # Use Steps for streaming
    async with cl.Step(name="Processing", type="tool") as parent_step:
        parent_step.input = f"{query} (clarified: {intent})"

        async for event in run_agent_streaming(
            query,
            multi_hop_enabled=multi_hop_enabled,
            user_clarification=intent,
        ):
            node = event["node"]
            state_update = event["state"]

            # Merge state into final state (append lists instead of replacing)
            for key, value in state_update.items():
                if key in final_state and isinstance(final_state[key], list) and isinstance(value, list):
                    final_state[key].extend(value)
                else:
                    final_state[key] = value

        # Set parent step output with reasoning trace
        results_count = len(final_state.get("consolidated_results", []))
        reasoning_trace = final_state.get("reasoning_trace", [])
        if reasoning_trace:
            trace_text = "\n".join(f"• {step}" for step in reasoning_trace)
            parent_step.output = f"Found {results_count} results\n\n**How we found these:**\n{trace_text}"
        else:
            parent_step.output = f"Found {results_count} results"

    # Format and display final results
    summary = final_state.get("summary", "Search completed.")
    results = final_state.get("consolidated_results", [])
    hierarchy_info = final_state.get("hierarchy_info", {})
    related_terms = final_state.get("related_terms", [])
    systems_searched = final_state.get("selected_systems", [])

    # Store results for export
    cl.user_session.set("last_results", results)
    cl.user_session.set("last_query", query)

    # Build output message
    output_parts = []

    # Add LLM summary at the top if available
    if summary and summary != "Search completed.":
        output_parts.append(summary)
        output_parts.append("\n\n---\n")  # Separator

    # Add formatted results (this has percentage badges, metadata, etc.)
    output_parts.append(format_results(results, hierarchy_info, show_hierarchy, query, systems_searched))

    if multi_hop_enabled and related_terms:
        output_parts.append(f"\n\n**Multi-hop expansion**: Searched for related terms: {', '.join(related_terms[:5])}")

    # Add search details footer
    search_terms = final_state.get("search_terms", [query])
    if systems_searched:
        output_parts.append(f"\n\n---\n*Searched: {', '.join(search_terms[:5])} across {', '.join(systems_searched)}*")

    # Create actions: follow-up suggestions + bundle + export
    actions = []
    if results:
        # Add follow-up suggestions based on results
        actions.extend(get_follow_up_suggestions(results, query))

        # Add bundle actions (top result from each system)
        actions.extend(get_bundle_actions(results))

        # Add export action
        actions.append(
            cl.Action(
                name="export_csv",
                payload={},
                label="Export to CSV",
            )
        )

        # Show bundle status if user has codes in bundle
        bundle = cl.user_session.get("code_bundle", [])
        if bundle:
            actions.append(
                cl.Action(
                    name="view_bundle",
                    payload={},
                    label=f"View bundle ({len(bundle)})",
                )
            )

    await cl.Message(content="".join(output_parts), actions=actions[:8]).send()
