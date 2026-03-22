"""
Trie helpers for prefix autocomplete.

This is the first backend Trie structure for autocomplete. It is intentionally
in-memory and request-scoped for now; it can be swapped with a cached/Redis
adapter later without changing the public suggestion API.
"""

from __future__ import annotations


class _TrieNode:
    __slots__ = ('children', 'top_keys')

    def __init__(self):
        self.children: dict[str, _TrieNode] = {}
        self.top_keys: list[str] = []


class PrefixTrie:
    """Stores phrases and returns top prefix-matching suggestions."""

    def __init__(self, max_node_suggestions: int = 32):
        self.root = _TrieNode()
        self.max_node_suggestions = max_node_suggestions
        self._display_map: dict[str, str] = {}
        self._score_map: dict[str, float] = {}

    @staticmethod
    def _normalize(text: str) -> str:
        return ' '.join((text or '').strip().lower().split())

    def insert(self, phrase: str, weight: float = 1.0):
        key = self._normalize(phrase)
        if len(key) < 2:
            return

        # Keep the highest observed weight for stable ranking.
        self._display_map[key] = phrase.strip()
        self._score_map[key] = max(weight, self._score_map.get(key, float('-inf')))

        node = self.root
        self._update_node_top_keys(node, key)
        for char in key:
            node = node.children.setdefault(char, _TrieNode())
            self._update_node_top_keys(node, key)

    def suggest(self, prefix: str, limit: int = 8) -> list[str]:
        normalized_prefix = self._normalize(prefix)
        if not normalized_prefix:
            return []

        node = self.root
        for char in normalized_prefix:
            node = node.children.get(char)
            if node is None:
                return []

        keys = node.top_keys[: max(0, limit)]
        return [self._display_map[k] for k in keys]

    def _update_node_top_keys(self, node: _TrieNode, key: str):
        if key not in node.top_keys:
            node.top_keys.append(key)

        node.top_keys.sort(key=lambda k: (-self._score_map[k], k))
        if len(node.top_keys) > self.max_node_suggestions:
            del node.top_keys[self.max_node_suggestions :]

