# ABOUTME: Tests for the cross-encoder model cache singleton.
# ABOUTME: Validates lazy loading and singleton behavior.

import pytest
from unittest.mock import patch, MagicMock

from src.scoring.model_cache import ModelCache


class TestModelCache:
    """Tests for the ModelCache singleton."""

    def setup_method(self):
        """Reset singleton before each test."""
        ModelCache.reset()

    def teardown_method(self):
        """Clean up after each test."""
        ModelCache.reset()

    async def test_get_instance_returns_same_instance(self):
        """Singleton should return same instance."""
        instance1 = await ModelCache.get_instance()
        instance2 = await ModelCache.get_instance()

        assert instance1 is instance2

    def test_get_instance_sync(self):
        """Sync version should work."""
        instance = ModelCache.get_instance_sync()

        assert instance is not None
        assert isinstance(instance, ModelCache)

    def test_is_loaded_initially_false(self):
        """Model should not be loaded initially."""
        cache = ModelCache.get_instance_sync()

        assert not cache.is_loaded()

    def test_current_model_name_initially_none(self):
        """No model name when nothing loaded."""
        cache = ModelCache.get_instance_sync()

        assert cache.current_model_name is None

    async def test_get_model_loads_on_first_call(self):
        """Model should be loaded on first get_model call."""
        with patch.object(ModelCache, "_load_model_sync") as mock_load:
            mock_model = MagicMock()
            mock_load.return_value = mock_model

            cache = await ModelCache.get_instance()
            model = await cache.get_model("test-model")

            assert model is mock_model
            mock_load.assert_called_once_with("test-model")
            assert cache.is_loaded()
            assert cache.current_model_name == "test-model"

    async def test_get_model_reuses_loaded_model(self):
        """Same model should be reused on subsequent calls."""
        with patch.object(ModelCache, "_load_model_sync") as mock_load:
            mock_model = MagicMock()
            mock_load.return_value = mock_model

            cache = await ModelCache.get_instance()
            model1 = await cache.get_model("test-model")
            model2 = await cache.get_model("test-model")

            assert model1 is model2
            # Only loaded once
            mock_load.assert_called_once()

    async def test_get_model_reloads_different_model(self):
        """Different model name should trigger reload."""
        with patch.object(ModelCache, "_load_model_sync") as mock_load:
            model_a = MagicMock(name="model-a")
            model_b = MagicMock(name="model-b")
            mock_load.side_effect = [model_a, model_b]

            cache = await ModelCache.get_instance()
            result_a = await cache.get_model("model-a")
            result_b = await cache.get_model("model-b")

            assert result_a is model_a
            assert result_b is model_b
            assert mock_load.call_count == 2

    def test_clear_unloads_model(self):
        """clear() should unload the model."""
        cache = ModelCache.get_instance_sync()
        cache._model = MagicMock()
        cache._model_name = "test"

        cache.clear()

        assert not cache.is_loaded()
        assert cache.current_model_name is None

    def test_reset_clears_singleton(self):
        """reset() should clear the singleton instance."""
        instance1 = ModelCache.get_instance_sync()
        ModelCache.reset()
        instance2 = ModelCache.get_instance_sync()

        assert instance1 is not instance2


class TestModelCacheLoadModel:
    """Tests for actual model loading."""

    def setup_method(self):
        ModelCache.reset()

    def teardown_method(self):
        ModelCache.reset()

    def test_load_model_sync_imports_correctly(self):
        """_load_model_sync should use sentence_transformers."""
        with patch("src.scoring.model_cache.CrossEncoder", create=True) as mock_ce:
            # Patch the import at module level
            import src.scoring.model_cache as module

            with patch.dict(
                "sys.modules",
                {"sentence_transformers": MagicMock(CrossEncoder=mock_ce)},
            ):
                cache = ModelCache.get_instance_sync()

                # This will use the actual import, so we need to patch differently
                with patch(
                    "sentence_transformers.CrossEncoder", mock_ce
                ):
                    cache._load_model_sync("test-model")
                    mock_ce.assert_called_once_with("test-model")
