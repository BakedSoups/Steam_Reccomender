import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from db_creation.chroma_pipeline import pipeline


class ChromaRebuildTests(unittest.TestCase):
    def run_rebuild(self, client, count):
        client.create_collection.return_value.count.return_value = count
        with patch.object(pipeline, "_ensure_chroma_client", return_value=client), \
             patch.object(pipeline, "_count_rows", return_value=1), \
             patch.object(pipeline, "_iter_rows", return_value=[]):
            return pipeline.run_chroma_migration(final_db_path=Path("unused"), chroma_dir_path=Path("unused"))

    def test_incomplete_rebuild_preserves_live_collection(self):
        client = MagicMock()
        with self.assertRaisesRegex(RuntimeError, "complete"):
            self.run_rebuild(client, 0)
        client.list_collections.assert_not_called()
        client.create_collection.return_value.modify.assert_not_called()

    def test_failed_swap_restores_live_name(self):
        client = MagicMock()
        old = MagicMock()
        old.name = pipeline.COLLECTION_NAME
        client.list_collections.return_value = [old]
        client.create_collection.return_value.modify.side_effect = RuntimeError("swap failed")
        with self.assertRaisesRegex(RuntimeError, "swap failed"):
            self.run_rebuild(client, 1)
        self.assertEqual(old.modify.call_args.kwargs, {"name": pipeline.COLLECTION_NAME})

    def test_successful_rebuild_preserves_backup(self):
        client = MagicMock()
        old = MagicMock()
        old.name = pipeline.COLLECTION_NAME
        client.list_collections.return_value = [old]
        self.run_rebuild(client, 1)
        self.assertIn("_backup_", old.modify.call_args.kwargs["name"])
        client.create_collection.return_value.modify.assert_called_once_with(name=pipeline.COLLECTION_NAME)
