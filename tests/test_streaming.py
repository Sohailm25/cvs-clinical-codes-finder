# ABOUTME: Tests for streaming agent execution.
# ABOUTME: Verifies that run_agent_streaming yields events in correct order.

import pytest
from src.agent import run_agent_streaming


class TestStreaming:
    """Tests for streaming agent execution."""

    @pytest.mark.asyncio
    async def test_streaming_yields_events(self):
        """Streaming should yield events as nodes complete."""
        events = []
        async for event in run_agent_streaming("diabetes"):
            events.append(event)

        # Should have received multiple events
        assert len(events) > 0

    @pytest.mark.asyncio
    async def test_streaming_event_structure(self):
        """Each event should have node, state, and timestamp keys."""
        async for event in run_agent_streaming("glucose"):
            assert "node" in event
            assert "state" in event
            assert "timestamp" in event
            assert isinstance(event["node"], str)
            assert isinstance(event["state"], dict)
            assert isinstance(event["timestamp"], float)
            break  # Just test first event

    @pytest.mark.asyncio
    async def test_streaming_covers_all_nodes(self):
        """Streaming should emit events for all core nodes."""
        nodes_seen = set()
        async for event in run_agent_streaming("metformin"):
            nodes_seen.add(event["node"])

        # Core nodes that should always run
        expected_nodes = {"classify", "plan", "execute", "reflect", "consolidate", "summarize"}
        assert expected_nodes.issubset(nodes_seen), f"Missing nodes: {expected_nodes - nodes_seen}"

    @pytest.mark.asyncio
    async def test_streaming_preserves_order(self):
        """Events should come in logical order."""
        nodes = []
        async for event in run_agent_streaming("aspirin"):
            nodes.append(event["node"])

        # Classify should come before plan, plan before execute
        if "classify" in nodes and "plan" in nodes:
            assert nodes.index("classify") < nodes.index("plan")
        if "plan" in nodes and "execute" in nodes:
            # Note: plan might appear multiple times due to refinement loops
            first_plan = nodes.index("plan")
            first_execute = next(i for i, n in enumerate(nodes) if n == "execute")
            # Execute should come after at least one plan
            assert first_execute > first_plan

    @pytest.mark.asyncio
    async def test_streaming_final_state_has_results(self):
        """Final aggregated state should contain results."""
        final_state = {}
        async for event in run_agent_streaming("wheelchair"):
            final_state.update(event["state"])

        # Should have consolidated results
        assert "consolidated_results" in final_state or "summary" in final_state
