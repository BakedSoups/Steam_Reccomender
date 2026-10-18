import unittest

from backend.recommender import _build_vector_preferences


class VectorPreferencesTests(unittest.TestCase):
    def test_no_reviews_status_is_not_scored_as_a_vector(self):
        preferences = _build_vector_preferences({"status": "no_reviews", "mechanics": {"shooting": 100}})
        self.assertEqual(list(preferences), ["mechanics"])
        self.assertGreater(preferences["mechanics"]["shooting"], 0)

    def test_empty_vectors_with_status_do_not_crash(self):
        self.assertEqual(_build_vector_preferences({"status": "no_reviews", "vibe": {}}), {"vibe": {}})
