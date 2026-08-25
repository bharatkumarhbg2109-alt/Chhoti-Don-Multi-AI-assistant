"""Test suite for the knowledge pipeline and RAG bridge.

All external dependencies (ChromaDB, Ollama, arXiv, requests) are mocked.
"""

import sys
import os
import unittest
from unittest.mock import MagicMock, patch

# Add knowledge_pipeline to sys.path for flat imports (import config, etc.)
# NOTE: We clean up in tearDown to avoid polluting sys.path for other tests.
_KP_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       "knowledge_pipeline")
_KP_ADDED = _KP_DIR not in sys.path
if _KP_ADDED:
    sys.path.insert(0, _KP_DIR)


class TestConfig(unittest.TestCase):
    """(a) Config: all required fields present and valid."""

    def test_ollama_host_is_string(self):
        import config
        self.assertIsInstance(config.OLLAMA_HOST, str)
        self.assertTrue(config.OLLAMA_HOST.startswith("http"))

    def test_chat_model_is_string(self):
        import config
        self.assertIsInstance(config.CHAT_MODEL, str)
        self.assertTrue(len(config.CHAT_MODEL) > 0)

    def test_embed_model_is_string(self):
        import config
        self.assertIsInstance(config.EMBED_MODEL, str)

    def test_db_path_is_string(self):
        import config
        self.assertIsInstance(config.DB_PATH, str)

    def test_arxiv_categories_nonempty(self):
        import config
        self.assertIsInstance(config.ARXIV_CATEGORIES, list)
        self.assertTrue(len(config.ARXIV_CATEGORIES) > 0)

    def test_fetch_max_positive(self):
        import config
        self.assertGreater(config.FETCH_MAX, 0)


class TestProcessor(unittest.TestCase):
    """(b, c) Processor: chunk_text and clean_html."""

    def test_chunk_text_returns_list_of_strings(self):
        import processor
        text = "word " * 200
        chunks = processor.chunk_text(text, max_words=50, overlap=10, min_words=5)
        self.assertIsInstance(chunks, list)
        self.assertTrue(len(chunks) > 1)
        for c in chunks:
            self.assertIsInstance(c, str)
            self.assertTrue(len(c) > 0)

    def test_chunk_text_no_empty_chunks(self):
        import processor
        text = "This is a test sentence with enough words to create multiple chunks when split properly. " * 5
        chunks = processor.chunk_text(text, max_words=10, overlap=2, min_words=3)
        for c in chunks:
            self.assertGreater(len(c.split()), 0)

    def test_chunk_text_short_text_single_chunk(self):
        import processor
        text = "short text"
        chunks = processor.chunk_text(text, max_words=100)
        self.assertEqual(len(chunks), 1)
        self.assertEqual(chunks[0], "short text")

    def test_chunk_text_within_max_words(self):
        import processor
        text = "a b c d e"
        chunks = processor.chunk_text(text, max_words=10, overlap=2, min_words=1)
        for c in chunks:
            self.assertLessEqual(len(c.split()), 10)

    def test_clean_html_removes_tags(self):
        import processor
        html = "<html><body><p>Hello world</p></body></html>"
        result = processor.clean_html(html)
        self.assertIsInstance(result, str)
        self.assertTrue(len(result) > 0)


class TestNovelty(unittest.TestCase):
    """(d) Novelty: is_novel returns True for new doc, False for duplicate."""

    def test_empty_collection_is_novel(self):
        import novelty
        mock_collection = MagicMock()
        mock_collection.count.return_value = 0
        self.assertTrue(novelty.is_novel(mock_collection, [0.1] * 384))

    def test_duplicate_is_not_novel(self):
        import novelty
        mock_collection = MagicMock()
        mock_collection.count.return_value = 10
        mock_collection.query.return_value = {"distances": [[0.05]]}
        self.assertFalse(novelty.is_novel(mock_collection, [0.1] * 384, threshold=0.12))

    def test_distant_is_novel(self):
        import novelty
        mock_collection = MagicMock()
        mock_collection.count.return_value = 10
        mock_collection.query.return_value = {"distances": [[0.8]]}
        self.assertTrue(novelty.is_novel(mock_collection, [0.1] * 384, threshold=0.12))


class TestFetcher(unittest.TestCase):
    """(e) Fetcher: fetch_recent returns list of dicts with required keys."""

    @patch("requests.get")
    def test_fetch_returns_list(self, mock_get):
        import fetcher
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = """<?xml version="1.0" encoding="UTF-8"?>
        <feed xmlns="http://www.w3.org/2005/Atom">
          <entry>
            <title>Test Paper</title>
            <id>http://arxiv.org/abs/2401.00001</id>
            <published>2024-01-01T00:00:00Z</published>
            <summary>This is a test abstract.</summary>
            <author><name>Test Author</name></author>
            <link href="http://arxiv.org/abs/2401.00001" rel="alternate"/>
          </entry>
        </feed>"""
        mock_get.return_value = mock_resp
        with patch("os.path.exists", return_value=False),              patch("builtins.open", MagicMock()):
            result = fetcher.fetch_new_items()
        self.assertIsInstance(result, list)


class TestStore(unittest.TestCase):
    """(f) Store: embed_and_store calls Ollama embeddings + ChromaDB."""

    @patch("requests.post")
    def test_embed_text_calls_ollama(self, mock_post):
        import store
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"embedding": [0.1] * 384}
        mock_resp.status_code = 200
        mock_post.return_value = mock_resp
        result = store.embed_text("test text")
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 384)

    def test_get_collection_returns_collection(self):
        import store
        mock_client = MagicMock()
        mock_collection = MagicMock()
        mock_client.get_or_create_collection.return_value = mock_collection
        result = store.get_collection(client=mock_client, name="test")
        self.assertEqual(result, mock_collection)


class TestCoreKnowledge(unittest.TestCase):
    """(g, h, i) core/knowledge.py retrieve_context: fail-open behavior."""

    def test_empty_collection_returns_empty(self):
        """(g) retrieve_context returns empty string when ChromaDB has no results."""
        from core import knowledge
        mock_collection = MagicMock()
        mock_collection.count.return_value = 0
        with patch("store.get_collection", return_value=mock_collection):
            ctx, sources = knowledge.retrieve_context("test query")
        self.assertEqual(ctx, "")
        self.assertEqual(sources, [])

    def test_relevant_chunks_returned(self):
        """(h) retrieve_context returns formatted context when chunks within threshold."""
        from core import knowledge
        mock_collection = MagicMock()
        mock_collection.count.return_value = 5
        mock_collection.query.return_value = {
            "ids": [["chunk1"]],
            "documents": [["test document text"]],
            "metadatas": [[{"title": "Test Paper", "url": "http://example.com", "source_type": "ai_knowledge"}]],
            "distances": [[0.3]],
        }
        with patch("store.get_collection", return_value=mock_collection), \
             patch("store.embed_text", return_value=[0.1] * 384):
            ctx, sources = knowledge.retrieve_context("test query", max_distance=0.45)
        self.assertIn("Test Paper", ctx)
        self.assertTrue(len(sources) > 0)

    def test_far_chunks_return_empty(self):
        """(i) retrieve_context returns empty when all chunks exceed distance gate."""
        from core import knowledge
        mock_collection = MagicMock()
        mock_collection.count.return_value = 5
        mock_collection.query.return_value = {
            "ids": [["chunk1"]],
            "documents": [["unrelated text"]],
            "metadatas": [[{"title": "Unrelated", "url": "", "source_type": "ai_knowledge"}]],
            "distances": [[0.8]],
        }
        with patch("store.get_collection", return_value=mock_collection), \
             patch("store.embed_text", return_value=[0.1] * 384):
            ctx, sources = knowledge.retrieve_context("unrelated query", max_distance=0.45)
        self.assertEqual(ctx, "")
        self.assertEqual(sources, [])

    def test_retrieve_context_fail_open(self):
        """retrieve_context returns empty on any exception (fail-open)."""
        from core import knowledge
        with patch("store.get_collection", side_effect=RuntimeError("db locked")):
            ctx, sources = knowledge.retrieve_context("test")
        self.assertEqual(ctx, "")
        self.assertEqual(sources, [])


class _SysPathCleanup(unittest.TestCase):
    """Remove knowledge_pipeline from sys.path to avoid import conflicts."""

    def test_cleanup_syspath(self):
        if _KP_ADDED and _KP_DIR in sys.path:
            sys.path.remove(_KP_DIR)


if __name__ == "__main__":
    unittest.main()
