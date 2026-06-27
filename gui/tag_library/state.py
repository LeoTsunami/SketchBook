"""
Tag library state dataclasses.

TagLibraryTaxonomy – immutable description of the tag tree (built at load time).
TagFilterState      – mutable filter selection (changes on each chip click).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, FrozenSet, List, Set, Tuple


@dataclass
class TagLibraryTaxonomy:
    """
    Immutable description of every category and tag in the library.

    Built once when the panel is loaded; replaced entirely on structural
    changes (add/remove/reparent tag, create shelf).

    Attributes:
        categories_order: Ordered list of category / shelf names.
        subtag_order: category → ordered list of all subtag names.
        placements: tag → placement dict from user_tags_config
                    (``{"category": "Animal"}`` or ``{"parent_tag": "Terrestrial"}``).
        subtag_to_category: tag name → category name reverse index.
        user_tags: Set of user-owned tag names (can be deleted/renamed).
        shelf_filter_modes: shelf category → filter mode ("and" or "or").
        children_map: parent_tag → list of child tag names.
    """

    categories_order: List[str] = field(default_factory=list)
    subtag_order: Dict[str, List[str]] = field(default_factory=dict)
    placements: Dict[str, dict] = field(default_factory=dict)
    subtag_to_category: Dict[str, str] = field(default_factory=dict)
    user_tags: Set[str] = field(default_factory=set)
    shelf_filter_modes: Dict[str, str] = field(default_factory=dict)
    children_map: Dict[str, List[str]] = field(default_factory=dict)

    def get_parent(self, tag: str) -> str | None:
        """
        Return the direct parent tag of *tag*, or None if it is a root tag.

        Args:
            tag: Tag name to look up.

        Returns:
            str | None: Parent tag name or None.
        """
        pl = self.placements.get(tag)
        if isinstance(pl, dict):
            return pl.get("parent_tag")
        return None

    def get_children(self, tag: str) -> List[str]:
        """
        Return direct children of *tag* in display order.

        Args:
            tag: Parent tag name.

        Returns:
            List[str]: Child tag names.
        """
        return self.children_map.get(tag, [])

    def has_children(self, tag: str) -> bool:
        """
        Return True if *tag* has at least one direct child.

        Args:
            tag: Tag name.

        Returns:
            bool: True when children exist.
        """
        return bool(self.children_map.get(tag))

    def get_all_descendants(self, tag: str, _visited: Set[str] | None = None) -> Set[str]:
        """
        Return *tag* plus every nested descendant (recursive parent_tag chain).

        Args:
            tag: Root tag.
            _visited: Internal cycle guard.

        Returns:
            Set[str]: tag ∪ all descendants.
        """
        if _visited is None:
            _visited = set()
        if tag in _visited:
            return set()
        _visited.add(tag)
        result: Set[str] = {tag}
        for child in self.get_children(tag):
            result.update(self.get_all_descendants(child, _visited))
        return result

    def get_category_all_tags(self, category: str) -> Set[str]:
        """
        Return the category name plus every tag displayed under it (any depth).

        Args:
            category: Category / shelf name.

        Returns:
            Set[str]: All tags belonging to the category.
        """
        result: Set[str] = {category}
        for tag in self.subtag_order.get(category, []):
            result.update(self.get_all_descendants(tag))
        return result


@dataclass
class TagFilterState:
    """
    Current filter selection emitted by TagLibraryPanel when the user clicks.

    MainWindow stores this and passes it to the image filter logic.

    Attributes:
        active_categories: Categories whose filter is ON (chip clicked green).
        active_subtags: category → set of active subtags within that category.
    """

    active_categories: FrozenSet[str] = field(default_factory=frozenset)
    active_subtags: Dict[str, FrozenSet[str]] = field(default_factory=dict)

    @staticmethod
    def from_mutable(
        active_categories: Set[str],
        active_subtags: Dict[str, Set[str]],
    ) -> "TagFilterState":
        """
        Build a TagFilterState from the panel's mutable internal sets.

        Args:
            active_categories: Panel's current active category set.
            active_subtags: Panel's current active subtag dict.

        Returns:
            TagFilterState: Immutable snapshot suitable for signal emission.
        """
        return TagFilterState(
            active_categories=frozenset(active_categories),
            active_subtags={k: frozenset(v) for k, v in active_subtags.items() if v},
        )

    def is_empty(self) -> bool:
        """
        Return True when no filters are active.

        Returns:
            bool: True when both categories and subtags are empty.
        """
        return not self.active_categories and not any(self.active_subtags.values())
