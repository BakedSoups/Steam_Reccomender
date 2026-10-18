import argparse
import sys
import unittest
from unittest.mock import MagicMock, patch

from db_creation import precompute_candidates as pipeline


class PrecomputeCandidatesTests(unittest.TestCase):
    def run_pipeline(self, collection, store, *, incomplete_only=False, collection_size=None):
        collection.count.return_value = collection_size if collection_size is not None else len(store.list_game_appids.return_value)
        args = argparse.Namespace(appid=None, per_game=300, batch_size=64, incomplete_only=incomplete_only)
        chroma = MagicMock()
        chroma.PersistentClient.return_value.get_collection.return_value = collection
        with patch.dict(sys.modules, {"chromadb": chroma}), \
             patch.object(pipeline, "load_project_env"), \
             patch.object(pipeline, "postgres_dsn_from_env", return_value="test"), \
             patch.object(pipeline, "PostgresGameStore", return_value=store), \
             patch.object(pipeline, "parse_args", return_value=args):
            return pipeline.main()

    def test_missing_embedding_fails_before_candidate_replacement(self):
        store = MagicMock()
        store.list_game_appids.return_value = [1, 2]
        collection = MagicMock()
        collection.get.return_value = {"ids": ["1"], "embeddings": [[0.1]]}
        with self.assertRaisesRegex(RuntimeError, "missing embeddings"):
            self.run_pipeline(collection, store)
        store.replace_precomputed_candidates.assert_not_called()

    def test_small_catalog_caps_query_and_excludes_source(self):
        store = MagicMock()
        store.list_game_appids.return_value = [1, 2]
        collection = MagicMock()
        collection.get.return_value = {"ids": ["1", "2"], "embeddings": [[0.1], [0.2]]}
        collection.query.return_value = {"ids": [["1", "2"], ["2", "1"]]}
        self.assertEqual(self.run_pipeline(collection, store), 0)
        self.assertEqual(collection.query.call_args.kwargs["n_results"], 2)
        self.assertNotIn("where", collection.query.call_args.kwargs)
        self.assertEqual(store.replace_precomputed_candidates.call_count, 2)

    def test_empty_candidates_fail_instead_of_success(self):
        store = MagicMock()
        store.list_game_appids.return_value = [1, 2]
        collection = MagicMock()
        collection.get.return_value = {"ids": ["1", "2"], "embeddings": [[0.1], [0.2]]}
        collection.query.return_value = {"ids": [["1"], ["2"]]}
        with self.assertRaisesRegex(RuntimeError, "Incomplete candidates"):
            self.run_pipeline(collection, store)
        store.replace_precomputed_candidates.assert_not_called()

    def test_repair_only_queries_incomplete_sources(self):
        store = MagicMock()
        store.list_game_appids.return_value = [1, 2]
        store.list_incomplete_candidate_appids.return_value = [2]
        collection = MagicMock()
        collection.get.return_value = {"ids": ["2"], "embeddings": [[0.2]]}
        collection.query.return_value = {"ids": [["2", "1"]]}
        self.run_pipeline(collection, store, incomplete_only=True)
        store.replace_precomputed_candidates.assert_called_once_with(2, [1], source="chroma")

    def test_repair_is_noop_when_cache_is_complete(self):
        store = MagicMock()
        store.list_game_appids.return_value = [1, 2]
        store.list_incomplete_candidate_appids.return_value = []
        collection = MagicMock()
        self.run_pipeline(collection, store, incomplete_only=True)
        collection.query.assert_not_called()

    def test_stale_chroma_entries_are_overfetched_and_filtered(self):
        store = MagicMock()
        store.list_game_appids.return_value = [1, 2]
        collection = MagicMock()
        collection.get.return_value = {"ids": ["1", "2"], "embeddings": [[0.1], [0.2]]}
        collection.query.return_value = {"ids": [["1", "99", "2"], ["2", "99", "1"]]}
        self.run_pipeline(collection, store, collection_size=3)
        self.assertEqual(collection.query.call_args.kwargs["n_results"], 3)
        store.replace_precomputed_candidates.assert_any_call(1, [2], source="chroma")
