"""
Chhoti Don - Search Engine
Advanced web search with DuckDuckGo, Wikipedia,
result ranking, caching, and multi-source aggregation.
Phase 2.2 - Full Upgrade
"""

import json
import time
import datetime
import urllib.request
import urllib.parse
import urllib.error
import re
from typing import Dict, List, Optional, Type# ==================================================
# 🎯 SEARCH CONFIGURATION
# ==================================================

DUCKDUCKGO_URL = "https://api.duckduckgo.com/"
WIKIPEDIA_API = "https://en.wikipedia.org/w/api.php"
WIKIPEDIA_SEARCH = "https://en.wikipedia.org/w/rest_api/v1/search/page"

DEFAULT_TIMEOUT = 10
MAX_RESULTS = 10
CACHE_TTL = 300  # 5 minutes

# Simple in-memory cache
_search_cache: Dict = {}
_search_history: List[Dict] = []


# ==================================================
# 🎯 MAIN FUNCTION (PRESERVED + UPGRADED)
# ==================================================

def search_web(input_data: Dict) -> Dict:
    """
    Original function — preserved + massively upgraded.
    Multi-source search with ranking and caching.
    """
    if not isinstance(input_data, dict):
        input_data = {"query": str(input_data)}

    query = input_data.get("query") or input_data.get("q")

    if not query:
        return {"status": "error", "message": "No search query provided."}

    engine = SearchEngine()
    return engine.search(
        query=query,
        sources=input_data.get("sources", ["duckduckgo", "wikipedia"]),
        max_results=input_data.get("max_results", 5),
        safe_search=input_data.get("safe_search", True),
    )


# ==================================================
# 🧠 SEARCH ENGINE CLASS
# ==================================================

class SearchEngine:
    """
    Advanced Multi-Source Search Engine.
    """

    def __init__(self, timeout: int = DEFAULT_TIMEOUT):
        self.timeout = timeout

    def search(
        self,
        query: str,
        sources: List[str] = None,
        max_results: int = 5,
        safe_search: bool = True,
    ) -> Dict:
        """
        Multi-source search with aggregation.
        """
        start_time = time.time()
        sources = sources or ["duckduckgo", "wikipedia"]

        # Cache check
        cache_key = f"{query}:{':'.join(sorted(sources))}"
        cached = self._get_cache(cache_key)
        if cached:
            cached["from_cache"] = True
            return cached

        all_results = []
        source_data = {}
        errors = []

        # DuckDuckGo
        if "duckduckgo" in sources:
            ddg = self._search_duckduckgo(query, safe_search)
            if ddg.get("status") == "success":
                source_data["duckduckgo"] = ddg
                all_results.extend(ddg.get("results", []))
            else:
                errors.append(f"DuckDuckGo: {ddg.get('message', 'failed')}")

        # Wikipedia
        if "wikipedia" in sources:
            wiki = self._search_wikipedia(query)
            if wiki.get("status") == "success":
                source_data["wikipedia"] = wiki
                all_results.extend(wiki.get("results", []))
            else:
                errors.append(f"Wikipedia: {wiki.get('message', 'failed')}")

        # Rank and deduplicate
        ranked = self._rank_results(all_results, query)[:max_results]

        # Instant answer (best single answer)
        instant_answer = self._extract_instant_answer(source_data, query)

        duration = round(time.time() - start_time, 3)

        result = {
            "status": "success",
            "query": query,
            "instant_answer": instant_answer,
            "results": ranked,
            "total_results": len(ranked),
            "sources_used": list(source_data.keys()),
            "errors": errors,
            "search_time_sec": duration,
            "timestamp": datetime.datetime.utcnow().isoformat(),
            "from_cache": False,
        }

        # Cache result
        self._set_cache(cache_key, result)

        # Log search
        _search_history.append({
            "query": query,
            "results": len(ranked),
            "timestamp": time.time(),
        })

        return result

    # --------------------------------------------------
    # 🦆 DuckDuckGo Search
    # --------------------------------------------------
    def _search_duckduckgo(self, query: str, safe_search: bool) -> Dict:
        """DuckDuckGo instant answer API."""
        try:
            params = {
                "q": query,
                "format": "json",
                "no_html": "1",
                "skip_disambig": "1",
                "kp": "1" if safe_search else "-1",
            }

            url = DUCKDUCKGO_URL + "?" + urllib.parse.urlencode(params)
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "ChhotiDon/2.2 (research tool)"},
            )

            response = urllib.request.urlopen(req, timeout=self.timeout)
            raw = response.read().decode("utf-8", errors="ignore")

            if not raw.strip():
                return {"status": "error", "message": "Empty response"}

            data = json.loads(raw)
            results = []

            # Abstract (main answer)
            abstract = data.get("AbstractText", "").strip()
            abstract_url = data.get("AbstractURL", "")
            abstract_source = data.get("AbstractSource", "")

            if abstract:
                results.append({
                    "title": data.get("Heading", query),
                    "snippet": abstract,
                    "url": abstract_url,
                    "source": abstract_source,
                    "type": "abstract",
                    "relevance": 1.0,
                })

            # Related topics
            for topic in data.get("RelatedTopics", [])[:5]:
                if isinstance(topic, dict) and topic.get("Text"):
                    results.append({
                        "title": topic.get("Text", "")[:80],
                        "snippet": topic.get("Text", ""),
                        "url": topic.get("FirstURL", ""),
                        "source": "DuckDuckGo",
                        "type": "related",
                        "relevance": 0.7,
                    })

            # Answer box
            answer = data.get("Answer", "")
            if answer:
                results.insert(0, {
                    "title": "Direct Answer",
                    "snippet": answer,
                    "url": "",
                    "source": "DuckDuckGo",
                    "type": "answer_box",
                    "relevance": 1.5,
                })

            # Definition
            definition = data.get("Definition", "")
            if definition:
                results.append({
                    "title": f"Definition: {query}",
                    "snippet": definition,
                    "url": data.get("DefinitionURL", ""),
                    "source": data.get("DefinitionSource", "Dictionary"),
                    "type": "definition",
                    "relevance": 0.9,
                })

            return {
                "status": "success",
                "results": results,
                "raw_answer": abstract or answer or "No instant answer found.",
                "source": "duckduckgo",
            }

        except urllib.error.URLError as e:
            return {"status": "error", "message": f"Network error: {e.reason}"}
        except json.JSONDecodeError:
            return {"status": "error", "message": "Invalid JSON response"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    # --------------------------------------------------
    # 📖 Wikipedia Search
    # --------------------------------------------------
    def _search_wikipedia(self, query: str) -> Dict:
        """Wikipedia search API."""
        try:
            params = {
                "action": "query",
                "list": "search",
                "srsearch": query,
                "srlimit": 3,
                "format": "json",
                "srprop": "snippet|titlesnippet",
            }

            url = WIKIPEDIA_API + "?" + urllib.parse.urlencode(params)
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "ChhotiDon/2.2 (research tool)"},
            )

            response = urllib.request.urlopen(req, timeout=self.timeout)
            data = json.loads(response.read().decode("utf-8"))

            search_results = data.get("query", {}).get("search", [])
            results = []

            for item in search_results:
                title = item.get("title", "")
                snippet = re.sub(r"<[^>]+>", "", item.get("snippet", ""))
                page_url = f"https://en.wikipedia.org/wiki/{urllib.parse.quote(title)}"

                results.append({
                    "title": title,
                    "snippet": snippet,
                    "url": page_url,
                    "source": "Wikipedia",
                    "type": "wiki_article",
                    "relevance": 0.85,
                })

            return {
                "status": "success",
                "results": results,
                "source": "wikipedia",
            }

        except Exception as e:
            return {"status": "error", "message": str(e)}

    def _get_wikipedia_summary(self, title: str) -> str:
        """Wikipedia article summary lo."""
        try:
            params = {
                "action": "query",
                "prop": "extracts",
                "exintro": True,
                "explaintext": True,
                "exsectionformat": "plain",
                "titles": title,
                "format": "json",
            }
            url = WIKIPEDIA_API + "?" + urllib.parse.urlencode(params)
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "ChhotiDon/2.2"},
            )
            response = urllib.request.urlopen(req, timeout=self.timeout)
            data = json.loads(response.read().decode())

            pages = data.get("query", {}).get("pages", {})
            for page in pages.values():
                extract = page.get("extract", "")
                if extract:
                    return extract[:500]

            return ""
        except Exception:
            return ""

    # --------------------------------------------------
    # 🏆 Result Ranking
    # --------------------------------------------------
    def _rank_results(self, results: List[Dict], query: str) -> List[Dict]:
        """Results rank karo by relevance."""
        query_words = set(query.lower().split())

        for result in results:
            base_relevance = result.get("relevance", 0.5)
            snippet = (result.get("snippet", "") + " " + result.get("title", "")).lower()

            # Keyword match bonus
            keyword_matches = sum(1 for w in query_words if w in snippet)
            keyword_bonus = keyword_matches * 0.1

            # Type bonus
            type_bonus = {
                "answer_box": 0.5,
                "abstract": 0.3,
                "definition": 0.2,
                "wiki_article": 0.1,
                "related": 0.0,
            }.get(result.get("type", ""), 0.0)

            result["relevance"] = round(base_relevance + keyword_bonus + type_bonus, 3)

        # Deduplicate by URL
        seen_urls = set()
        unique = []
        for r in results:
            url = r.get("url", "")
            if url and url in seen_urls:
                continue
            seen_urls.add(url)
            unique.append(r)

        # Sort by relevance
        unique.sort(key=lambda x: x.get("relevance", 0), reverse=True)
        return unique

    # --------------------------------------------------
    # ⚡ Instant Answer
    # --------------------------------------------------
    def _extract_instant_answer(self, source_data: Dict, query: str) -> Optional[str]:
        """Best instant answer extract karo."""
        # DuckDuckGo answer box
        ddg = source_data.get("duckduckgo", {})
        raw = ddg.get("raw_answer", "")
        if raw and raw != "No instant answer found." and len(raw) > 20:
            return raw[:500]

        # Wikipedia first result snippet
        wiki = source_data.get("wikipedia", {})
        wiki_results = wiki.get("results", [])
        if wiki_results:
            return wiki_results[0].get("snippet", "")[:300]

        return None

    # --------------------------------------------------
    # 💾 Cache
    # --------------------------------------------------
    def _get_cache(self, key: str) -> Optional[Dict]:
        """Cache se result lo."""
        entry = _search_cache.get(key)
        if entry and time.time() - entry["cached_at"] < CACHE_TTL:
            return entry["data"].copy()
        return None

    def _set_cache(self, key: str, data: Dict) -> None:
        """Result cache karo."""
        _search_cache[key] = {
            "data": data,
            "cached_at": time.time(),
        }
        # Limit cache size
        if len(_search_cache) > 100:
            oldest = min(_search_cache.keys(), key=lambda k: _search_cache[k]["cached_at"])
            del _search_cache[oldest]


# ==================================================
# 🔧 STANDALONE FUNCTIONS
# ==================================================

def quick_search(query: str) -> str:
    """Quick search — returns best answer string."""
    result = search_web({"query": query})

    if result.get("instant_answer"):
        return result["instant_answer"]

    results = result.get("results", [])
    if results:
        return results[0].get("snippet", "No results found")

    return "No results found"


def search_wikipedia(query: str) -> Dict:
    """Wikipedia only search."""
    engine = SearchEngine()
    return engine._search_wikipedia(query)


def get_search_history(last_n: int = 10) -> List[Dict]:
    """Search history lo."""
    return _search_history[-last_n:]


def clear_search_cache() -> None:
    """Search cache clear karo."""
    _search_cache.clear()
