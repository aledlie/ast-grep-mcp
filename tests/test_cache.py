"""Tests for query caching functionality"""

import os
import sys
import time
from unittest.mock import Mock, patch

import pytest

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Mock FastMCP before importing main
class MockFastMCP:
    def __init__(self, name):
        self.name = name
        self.tools = {}

    def tool(self, **kwargs):
        def decorator(func):
            self.tools[func.__name__] = func
            return func
        return decorator

    def run(self, **kwargs):
        pass


def mock_field(**kwargs):
    return kwargs.get("default")


# Import with mocked decorators
with patch("mcp.server.fastmcp.FastMCP", MockFastMCP):
    with patch("pydantic.Field", mock_field):
        import main
        from main import QueryCache


class TestQueryCache:
    """Test QueryCache class functionality"""

    def test_cache_initialization(self):
        """Test cache is initialized with correct parameters"""
        cache = QueryCache(max_size=50, ttl_seconds=120)
        assert cache.max_size == 50
        assert cache.ttl_seconds == 120
        assert len(cache.cache) == 0
        assert cache.hits == 0
        assert cache.misses == 0

    def test_cache_put_and_get(self):
        """Test storing and retrieving results from cache"""
        cache = QueryCache(max_size=10, ttl_seconds=300)

        results = [{"text": "match1", "file": "test.py"}]
        cache.put("run", ["--pattern", "test"], "/project", results)

        retrieved = cache.get("run", ["--pattern", "test"], "/project")
        assert retrieved == results
        assert cache.hits == 1
        assert cache.misses == 0

    def test_cache_miss(self):
        """Test cache miss returns None and updates stats"""
        cache = QueryCache(max_size=10, ttl_seconds=300)

        result = cache.get("run", ["--pattern", "test"], "/project")
        assert result is None
        assert cache.hits == 0
        assert cache.misses == 1

    def test_cache_ttl_expiration(self):
        """Test cache entries expire after TTL"""
        cache = QueryCache(max_size=10, ttl_seconds=1)  # 1 second TTL

        results = [{"text": "match1"}]
        cache.put("run", ["--pattern", "test"], "/project", results)

        # Should be in cache immediately
        retrieved = cache.get("run", ["--pattern", "test"], "/project")
        assert retrieved == results

        # Wait for TTL to expire
        time.sleep(1.1)

        # Should be expired now
        retrieved = cache.get("run", ["--pattern", "test"], "/project")
        assert retrieved is None
        assert cache.misses == 1

    def test_cache_lru_eviction(self):
        """Test LRU eviction when cache is full"""
        cache = QueryCache(max_size=2, ttl_seconds=300)

        # Fill cache to capacity
        cache.put("run", ["--pattern", "test1"], "/project", [{"text": "match1"}])
        cache.put("run", ["--pattern", "test2"], "/project", [{"text": "match2"}])

        # Add one more item, should evict oldest (test1)
        cache.put("run", ["--pattern", "test3"], "/project", [{"text": "match3"}])

        # test1 should be evicted
        assert cache.get("run", ["--pattern", "test1"], "/project") is None
        # test2 and test3 should still be there
        assert cache.get("run", ["--pattern", "test2"], "/project") is not None
        assert cache.get("run", ["--pattern", "test3"], "/project") is not None

    def test_cache_lru_access_updates_order(self):
        """Test that accessing a cache entry updates its LRU position"""
        cache = QueryCache(max_size=2, ttl_seconds=300)

        # Fill cache
        cache.put("run", ["--pattern", "test1"], "/project", [{"text": "match1"}])
        cache.put("run", ["--pattern", "test2"], "/project", [{"text": "match2"}])

        # Access test1 to make it most recently used
        cache.get("run", ["--pattern", "test1"], "/project")

        # Add test3, should evict test2 (least recently used)
        cache.put("run", ["--pattern", "test3"], "/project", [{"text": "match3"}])

        # test1 should still be there, test2 should be evicted
        assert cache.get("run", ["--pattern", "test1"], "/project") is not None
        assert cache.get("run", ["--pattern", "test2"], "/project") is None
        assert cache.get("run", ["--pattern", "test3"], "/project") is not None

    def test_cache_key_generation(self):
        """Test cache key includes command, args, and project folder"""
        cache = QueryCache()

        # Same pattern, different projects should have different cache entries
        cache.put("run", ["--pattern", "test"], "/project1", [{"text": "match1"}])
        cache.put("run", ["--pattern", "test"], "/project2", [{"text": "match2"}])

        result1 = cache.get("run", ["--pattern", "test"], "/project1")
        result2 = cache.get("run", ["--pattern", "test"], "/project2")

        assert result1 == [{"text": "match1"}]
        assert result2 == [{"text": "match2"}]

    def test_cache_args_order_normalized(self):
        """Test cache key is consistent regardless of args order"""
        cache = QueryCache()

        # The cache should normalize args order (sorting happens in _make_key)
        cache.put("run", ["--lang", "python", "--pattern", "test"], "/project", [{"text": "match1"}])

        # Same args in different order should hit the same cache entry
        result = cache.get("run", ["--pattern", "test", "--lang", "python"], "/project")
        assert result == [{"text": "match1"}]

    def test_hit_rate_calculation(self):
        """Test cache hit rate calculation"""
        cache = QueryCache()

        # Initial hit rate should be 0
        stats = cache.get_stats()
        assert stats["hit_rate"] == 0.0

        # Add an entry
        cache.put("run", ["--pattern", "test"], "/project", [{"text": "match1"}])

        # One hit, one miss (first get was a miss before put)
        cache.get("run", ["--pattern", "test"], "/project")  # hit
        cache.get("run", ["--pattern", "other"], "/project")  # miss

        # Hit rate should be 0.5 (1 hit, 1 miss)
        stats = cache.get_stats()
        assert stats["hit_rate"] == 0.5

    def test_empty_results_can_be_cached(self):
        """Test that empty result lists can be cached"""
        cache = QueryCache()

        # Cache an empty result
        cache.put("run", ["--pattern", "nonexistent"], "/project", [])

        # Should retrieve empty list, not None
        result = cache.get("run", ["--pattern", "nonexistent"], "/project")
        assert result is not None
        assert result == []


class TestCacheIntegration:
    """Test cache integration with find_code and find_code_by_rule"""

    def setup_method(self):
        """Reset global cache before each test"""
        main._query_cache = QueryCache(max_size=10, ttl_seconds=300)
        main.CACHE_ENABLED = True
        # Register tools
        main.register_mcp_tools()

    def teardown_method(self):
        """Clean up after each test"""
        main._query_cache = None
        main.CACHE_ENABLED = True

    @patch("main.stream_ast_grep_results")
    def test_find_code_cache_miss_then_hit(self, mock_stream):
        """Test find_code caches results and serves from cache on second call"""
        mock_matches = [
            {"text": "def test():", "file": "test.py", "range": {"start": {"line": 1}}}
        ]
        mock_stream.return_value = iter(mock_matches)

        find_code = main.mcp.tools.get("find_code")

        # First call - cache miss, should call stream_ast_grep_results
        result1 = find_code(project_folder="/project", pattern="def $NAME", output_format="json")
        assert mock_stream.call_count == 1
        assert result1 == mock_matches

        # Second call - cache hit, should NOT call stream_ast_grep_results again
        result2 = find_code(project_folder="/project", pattern="def $NAME", output_format="json")
        assert mock_stream.call_count == 1  # Should still be 1
        assert result2 == mock_matches

    @patch("main.stream_ast_grep_results")
    def test_find_code_by_rule_cache_miss_then_hit(self, mock_stream):
        """Test find_code_by_rule caches results and serves from cache on second call"""
        mock_matches = [
            {"text": "class Test:", "file": "test.py", "range": {"start": {"line": 1}}}
        ]
        mock_stream.return_value = iter(mock_matches)

        yaml_rule = """id: test
language: Python
rule:
  pattern: class $NAME"""

        find_code_by_rule = main.mcp.tools.get("find_code_by_rule")

        # First call - cache miss
        result1 = find_code_by_rule(
            project_folder="/project",
            yaml_rule=yaml_rule,
            output_format="json"
        )
        assert mock_stream.call_count == 1
        assert result1 == mock_matches

        # Second call - cache hit
        result2 = find_code_by_rule(
            project_folder="/project",
            yaml_rule=yaml_rule,
            output_format="json"
        )
        assert mock_stream.call_count == 1
        assert result2 == mock_matches

    @patch("main.stream_ast_grep_results")
    def test_cache_disabled(self, mock_stream):
        """Test that caching is disabled when CACHE_ENABLED is False"""
        main.CACHE_ENABLED = False
        main._query_cache = None

        mock_matches = [{"text": "match"}]
        mock_stream.return_value = iter(mock_matches)

        find_code = main.mcp.tools.get("find_code")

        # Call twice, should execute both times
        find_code(project_folder="/project", pattern="test", output_format="json")
        find_code(project_folder="/project", pattern="test", output_format="json")

        assert mock_stream.call_count == 2

    @patch("main.stream_ast_grep_results")
    def test_different_patterns_not_cached_together(self, mock_stream):
        """Test that different patterns create separate cache entries"""
        mock_stream.side_effect = [
            iter([{"text": "match1"}]),
            iter([{"text": "match2"}])
        ]

        find_code = main.mcp.tools.get("find_code")

        # Two different patterns
        result1 = find_code(project_folder="/project", pattern="pattern1", output_format="json")
        result2 = find_code(project_folder="/project", pattern="pattern2", output_format="json")

        assert mock_stream.call_count == 2
        assert result1 == [{"text": "match1"}]
        assert result2 == [{"text": "match2"}]

    @patch("main.stream_ast_grep_results")
    def test_cache_text_and_json_formats(self, mock_stream):
        """Test that both text and json formats use the same cache"""
        mock_matches = [
            {"text": "def test():", "file": "test.py", "range": {"start": {"line": 1}, "end": {"line": 1}}}
        ]
        mock_stream.return_value = iter(mock_matches)

        find_code = main.mcp.tools.get("find_code")

        # First call with json format - cache miss
        result_json = find_code(project_folder="/project", pattern="test", output_format="json")
        assert mock_stream.call_count == 1

        # Second call with text format - cache hit, different formatting
        result_text = find_code(project_folder="/project", pattern="test", output_format="text")
        assert mock_stream.call_count == 1  # Should still be 1

        # Results should be different formats but from same cached data
        assert result_json == mock_matches
        assert "Found 1 match" in result_text
        assert "test.py" in result_text
        assert "def test():" in result_text
