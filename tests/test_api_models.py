from __future__ import annotations

import unittest

from pydantic import ValidationError

from backend.api_models import RecommendationRequest


class RecommendationRequestTests(unittest.TestCase):
    def test_defaults_are_applied(self) -> None:
        request = RecommendationRequest.model_validate({"appid": "123"})

        self.assertEqual(request.appid, 123)
        self.assertEqual(request.limit, 20)
        self.assertIsNone(request.weights.tags)

    def test_limit_must_be_in_supported_range(self) -> None:
        with self.assertRaises(ValidationError):
            RecommendationRequest.model_validate({"appid": 123, "limit": 0})

        with self.assertRaises(ValidationError):
            RecommendationRequest.model_validate({"appid": 123, "limit": 51})

    def test_tag_weights_are_numeric_and_clamped(self) -> None:
        request = RecommendationRequest.model_validate(
            {
                "appid": 123,
                "weights": {
                    "tags": {
                        "mechanics": {
                            "Automation": "42.5",
                            "Penalty": -10,
                        },
                    },
                },
            }
        )

        self.assertEqual(request.weights.tags["mechanics"]["Automation"], 42.5)
        self.assertEqual(request.weights.tags["mechanics"]["Penalty"], 0.0)

    def test_percentage_maps_reject_invalid_values_and_unknown_keys(self) -> None:
        for group, key in (("match", "vector"), ("context", "music"), ("appeal", "pace")):
            for value in ("oops", None, float("nan"), float("inf"), -1, 101):
                with self.subTest(group=group, value=value), self.assertRaises(ValidationError):
                    RecommendationRequest.model_validate({"appid": 123, "weights": {group: {key: value}}})
            with self.subTest(group=group), self.assertRaises(ValidationError):
                RecommendationRequest.model_validate({"appid": 123, "weights": {group: {"typo": 10}}})

    def test_tag_maps_reject_nonfinite_values_and_unknown_contexts(self) -> None:
        for value in (float("nan"), float("inf"), float("-inf"), 101):
            with self.subTest(value=value), self.assertRaises(ValidationError):
                RecommendationRequest.model_validate({"appid": 123, "weights": {"tags": {"music": {"rock": value}}}})
        with self.assertRaises(ValidationError):
            RecommendationRequest.model_validate({"appid": 123, "weights": {"tags": {"typo": {"rock": 10}}}})

    def test_percentage_boundaries_and_numeric_strings_are_supported(self) -> None:
        request = RecommendationRequest.model_validate({
            "appid": 123, "weights": {"match": {"vector": "100", "music": 0}, "appeal": {"pace": 50}}
        })
        self.assertEqual(request.weights.match, {"vector": 100, "music": 0})

    def test_invalid_tag_weight_is_rejected(self) -> None:
        with self.assertRaises(ValidationError):
            RecommendationRequest.model_validate(
                {
                    "appid": 123,
                    "weights": {
                        "tags": {
                            "mechanics": {
                                "Automation": "heavy",
                            },
                        },
                    },
                }
            )


if __name__ == "__main__":
    unittest.main()
