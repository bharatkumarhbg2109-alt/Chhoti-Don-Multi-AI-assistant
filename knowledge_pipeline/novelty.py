"""
novelty.py — Module 4: Embedding-distance dedup.

Given a candidate embedding, ask ChromaDB for its nearest existing neighbour.
If that neighbour is closer than (or equal to) NOVELTY_THRESHOLD, the candidate
is a near-duplicate and should be skipped. An empty collection means everything
is novel.

This module operates purely on a passed-in collection object and embedding, so
it stays free of any ChromaDB import and is trivial to unit-test.
"""

from __future__ import annotations

import logging

import config

logger = logging.getLogger(__name__)


def nearest_distance(collection, embedding: list[float]) -> float | None:
    """
    Return the distance to the single nearest neighbour of ``embedding`` in
    ``collection``, or None if the collection is empty / has no result.
    """
    try:
        if collection.count() == 0:
            return None
    except Exception as exc:  # very defensive; count() shouldn't fail
        logger.warning("collection.count() failed (%s); treating as empty.", exc)
        return None

    result = collection.query(query_embeddings=[embedding], n_results=1)
    distances = result.get("distances") or []
    if not distances or not distances[0]:
        return None
    return distances[0][0]


def is_novel(
    collection,
    embedding: list[float],
    threshold: float | None = None,
) -> bool:
    """
    True if ``embedding`` is novel enough to store.

    A candidate is NON-novel (returns False) when its nearest-neighbour
    distance is <= ``threshold``. An empty collection => novel (True).
    """
    threshold = threshold if threshold is not None else config.NOVELTY_THRESHOLD
    dist = nearest_distance(collection, embedding)
    if dist is None:
        return True  # empty DB or no neighbour -> treat as novel
    novel = dist > threshold
    if not novel:
        logger.debug("Skipping near-duplicate (distance %.4f <= %.4f).", dist, threshold)
    return novel
