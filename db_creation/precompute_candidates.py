#!/usr/bin/env python3

from __future__ import annotations

import argparse
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.environment import load_project_env
from backend.pg_store import PostgresGameStore, postgres_dsn_from_env
from db_creation.paths import chroma_dir_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Precompute default recommendation candidates from Chroma into Postgres.",
    )
    parser.add_argument("--appid", type=int, help="Only refresh one source appid.")
    parser.add_argument("--incomplete-only", action="store_true", help="Repair only missing or undersized candidate pools.")
    parser.add_argument("--per-game", type=int, default=300, help="Candidates to store per game.")
    parser.add_argument("--batch-size", type=int, default=64, help="Batch size for Chroma embedding fetch/query.")
    return parser.parse_args()


def chunked(items: list[int], size: int):
    for start in range(0, len(items), size):
        yield items[start : start + size]


def main() -> int:
    load_project_env()

    dsn = postgres_dsn_from_env()
    if not dsn:
        raise RuntimeError("STEAM_REC_POSTGRES_DSN must be set.")

    args = parse_args()
    if args.per_game < 1 or args.batch_size < 1:
        raise ValueError("--per-game and --batch-size must be positive")
    store = PostgresGameStore(dsn)
    store.ensure_precomputed_candidates_table()

    try:
        import chromadb
    except ImportError as exc:
        raise RuntimeError("Chroma is not installed.") from exc

    client = chromadb.PersistentClient(path=str(chroma_dir_path()))
    collection = client.get_collection("steam_final_canon")

    catalog_appids = store.list_game_appids()
    catalog_ids = set(catalog_appids)
    appids = [args.appid] if args.appid is not None else catalog_appids
    if not appids or any(appid not in catalog_ids for appid in appids):
        raise RuntimeError("Precomputation requires source games in the PostgreSQL catalog")
    expected_candidates = min(args.per_game, len(catalog_ids) - 1)
    if expected_candidates < 1:
        raise RuntimeError("Precomputation requires at least two catalog games")
    if getattr(args, "incomplete_only", False):
        if args.appid is not None:
            raise ValueError("--appid and --incomplete-only cannot be combined")
        appids = store.list_incomplete_candidate_appids(minimum=expected_candidates)

    # Validate the whole source set before replacing any cached candidates.
    missing_ids = []
    for batch in chunked(appids, args.batch_size):
        payload = collection.get(ids=[str(appid) for appid in batch], include=["embeddings"])
        embeddings = payload.get("embeddings")
        present = {
            int(raw_id)
            for raw_id, embedding in zip(payload.get("ids") or [], embeddings if embeddings is not None else [])
            if embedding is not None
        }
        missing_ids.extend(appid for appid in batch if appid not in present)
    if missing_ids:
        raise RuntimeError(
            f"Chroma is missing embeddings for {len(missing_ids)} source games; "
            f"sample={missing_ids[:20]}. Rebuild Chroma before precomputing."
        )
    # Overfetch stale entries and filter locally; a catalog-wide $in filter
    # exceeds SQLite's SQL parameter limit for large Chroma collections.
    collection_size = collection.count()
    query_limit = min(collection_size, expected_candidates + 1 + max(0, collection_size - len(catalog_ids)))
    processed = 0

    for appid_batch in chunked(appids, max(1, args.batch_size)):
        ids = [str(appid) for appid in appid_batch]
        payload = collection.get(ids=ids, include=["embeddings"])
        embeddings = payload.get("embeddings")
        if embeddings is None:
            embeddings = []
        present_ids = payload.get("ids")
        if present_ids is None:
            present_ids = []
        embedding_map = {
            int(raw_id): embedding
            for raw_id, embedding in zip(present_ids, embeddings)
            if raw_id is not None and embedding is not None
        }
        query_appids = [appid for appid in appid_batch if appid in embedding_map]
        if len(query_appids) != len(appid_batch):
            raise RuntimeError("Chroma embeddings changed during precomputation")

        query_result = collection.query(
            query_embeddings=[embedding_map[appid] for appid in query_appids],
            n_results=query_limit,
        )
        candidate_groups = query_result.get("ids", [])
        if len(candidate_groups) != len(query_appids):
            raise RuntimeError("Chroma returned incomplete candidate groups")

        for appid, raw_candidates in zip(query_appids, candidate_groups):
            candidate_appids: list[int] = []
            for raw_candidate in raw_candidates:
                try:
                    candidate_appid = int(raw_candidate)
                except (TypeError, ValueError):
                    continue
                if candidate_appid == appid or candidate_appid not in catalog_ids or candidate_appid in candidate_appids:
                    continue
                candidate_appids.append(candidate_appid)
                if len(candidate_appids) >= args.per_game:
                    break
            if len(candidate_appids) != expected_candidates:
                raise RuntimeError(f"Incomplete candidates for appid={appid}: {len(candidate_appids)}/{expected_candidates}")
            store.replace_precomputed_candidates(appid, candidate_appids, source="chroma")
            processed += 1
            if processed % 100 == 0:
                print(f"processed={processed}/{len(appids)}")

    print(f"completed processed={processed} total={len(appids)} per_game={args.per_game}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
