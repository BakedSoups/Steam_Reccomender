import unittest

from backend.recommender import (
    _build_identity_preferences,
    _build_music_preferences,
    _build_setting_preferences,
    _build_vector_preferences,
)


class TagPreferenceTests(unittest.TestCase):
    def test_explicit_overrides_replace_defaults_and_preserve_ratios(self):
        cases = [
            (_build_music_preferences, {"music_primary": "a", "music_secondary": "b"}),
            (_build_identity_preferences, {"signature_tag": "a", "identity_tags": ["b"]}),
            (_build_setting_preferences, {"setting_tags": ["a", "b"]}),
        ]
        for build, metadata in cases:
            with self.subTest(builder=build.__name__):
                self.assertTrue(build(metadata))
                self.assertEqual(build(metadata, {}), {})
                self.assertEqual(build(metadata, {"a": 0, "b": 0}), {})
                self.assertEqual(build(metadata, {"a": 0, "b": 100}), {"a": 0, "b": 1})
                self.assertEqual(build(metadata, {"a": 25, "b": 75}), {"a": .25, "b": .75})
                self.assertEqual(build(metadata, {"b": 100}), {"b": 1})

    def test_vector_empty_override_clears_only_the_selected_context(self):
        vectors = {"mechanics": {"a": 100}, "vibe": {"b": 100}}
        baseline = _build_vector_preferences(vectors)
        changed = _build_vector_preferences(vectors, {"mechanics": {}})
        self.assertEqual(changed["mechanics"], {})
        self.assertEqual(changed["vibe"], baseline["vibe"])
