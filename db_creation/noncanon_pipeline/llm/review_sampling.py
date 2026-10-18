from typing import Dict, List


def sample_reviews(results: Dict, per_category: int = 5, max_total: int = 14) -> List[str]:
    pool = []

    # The final cap is applied in this order, so earlier categories have priority
    # when the combined per-category selections exceed the prompt budget.
    for category in ["systems_depth", "descriptive", "artistic", "music"]:
        if category in results:
            pool.extend(results[category][:per_category])

    seen = set()
    unique = []

    # A review can appear in multiple categories; keep its first occurrence so
    # repeated evidence does not consume multiple slots in the LLM input.
    for review_data in pool:
        text = review_data["review"].strip()
        if text not in seen:
            seen.add(text)
            unique.append(text)

    return unique[:max_total]
