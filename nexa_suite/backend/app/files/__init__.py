"""Files package for the Nexa AI backend."""

from .safe_directories import (
    get_user_home,
    get_safe_directory_map,
    normalize_scope,
    is_path_within_safe_directories,
    contains_blocked_path_keyword,
    get_directories_for_scope,
    list_safe_directories,
)
from .search import (
    normalize_file_query,
    normalize_extensions,
    is_blocked_file_search_text,
    search_files_read_only,
)

__all__ = [
    "get_user_home",
    "get_safe_directory_map",
    "normalize_scope",
    "is_path_within_safe_directories",
    "contains_blocked_path_keyword",
    "get_directories_for_scope",
    "list_safe_directories",
    "normalize_file_query",
    "normalize_extensions",
    "is_blocked_file_search_text",
    "search_files_read_only",
]
