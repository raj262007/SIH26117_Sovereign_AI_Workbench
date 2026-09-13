"""
Tests for Langfuse tracing integration.
Verifies tracing is a silent no-op when Langfuse is not configured,
and that all helper functions handle None gracefully.
"""

import unittest
import os


class TestLangfuseTracing(unittest.TestCase):
    """Test Langfuse tracing helpers degrade gracefully when not configured."""

    def test_langfuse_not_configured_returns_none(self):
        """When LANGFUSE keys are empty, get_langfuse() returns None."""
        # Clear any keys that might be set
        original_pub = os.environ.get("LANGFUSE_PUBLIC_KEY")
        original_sec = os.environ.get("LANGFUSE_SECRET_KEY")
        os.environ["LANGFUSE_PUBLIC_KEY"] = ""
        os.environ["LANGFUSE_SECRET_KEY"] = ""

        # Reset singleton so it re-checks
        from src.utils.tracing import get_langfuse, _is_langfuse_configured
        if hasattr(get_langfuse, "_instance"):
            delattr(get_langfuse, "_instance")

        self.assertFalse(_is_langfuse_configured())
        self.assertIsNone(get_langfuse())

        # Restore
        if original_pub:
            os.environ["LANGFUSE_PUBLIC_KEY"] = original_pub
        if original_sec:
            os.environ["LANGFUSE_SECRET_KEY"] = original_sec

    def test_create_workflow_trace_returns_none_when_unconfigured(self):
        """create_workflow_trace returns None when Langfuse is not configured."""
        from src.utils.tracing import create_workflow_trace
        trace = create_workflow_trace("test query", "full_pipeline")
        self.assertIsNone(trace)

    def test_create_span_handles_none_trace(self):
        """create_span is a no-op when trace is None."""
        from src.utils.tracing import create_span
        result = create_span(None, "test-node", {"step": "test"})
        self.assertIsNone(result)

    def test_end_span_handles_none(self):
        """end_span does nothing when span is None."""
        from src.utils.tracing import end_span
        # Should not raise
        end_span(None, {"output": "test"})

    def test_create_generation_handles_none_trace(self):
        """create_generation is a no-op when trace is None."""
        from src.utils.tracing import create_generation
        # Should not raise
        create_generation(
            trace=None,
            name="test-gen",
            model="test-model",
            input_text="test input",
            output_text="test output",
        )

    def test_flush_trace_handles_none(self):
        """flush_trace does nothing when trace is None."""
        from src.utils.tracing import flush_trace
        # Should not raise
        flush_trace(None)

    def test_llm_gateway_accepts_trace_params(self):
        """LLMGateway.call_model accepts optional langfuse_trace and langfuse_span."""
        from src.agent.llm_client import llm_gateway
        # Should work with None trace (offline fallback, no tracing)
        result = llm_gateway.call_model(
            "coding-engine",
            "calculate thickness",
            langfuse_trace=None,
            langfuse_span=None,
        )
        self.assertIn("python", result.lower())


if __name__ == "__main__":
    unittest.main()
