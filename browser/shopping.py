"""Phase 4: shopping-assist helpers — product extraction, bot-wall detection, and
the per-task add-to-cart cap.

READ-ONLY extraction + safety heuristics only. The actual interactions (typing a
query, clicking add-to-cart) go through the Phase-3 HITL gate in browser.guarded;
payment/checkout is hard-blocked there. Nothing here handles credentials.
"""

from __future__ import annotations

import re
import threading
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from .config import MAX_CART_ADDITIONS

# ── Per-site product-card selectors (best-effort) + generic fallback ──────────
# Real marketplaces (Flipkart/Amazon) change classes often AND bot-block headless
# automation; those are handled where possible but usually hit the bot-wall
# handoff. The generic price-anchored fallback works on most catalog pages.
SITE_SELECTORS: Dict[str, Dict[str, str]] = {
    "books.toscrape.com": {"card": "article.product_pod", "title": "h3 a",
                           "price": ".price_color", "rating": "p.star-rating",
                           "link": "h3 a"},
    "webscraper.io": {"card": "div.thumbnail", "title": "a.title",
                      "price": ".price, .caption h4.price", "rating": ".ratings",
                      "link": "a.title"},
    "flipkart.com": {"card": "div._1AtVbE, div._13oc-S, div._2kHMtA, div._4ddWXP",
                     "title": "div._4rR01T, a.s1Q9rs, a.IRpwTa, div.KzDlHZ",
                     "price": "div._30jeq3, div.Nx9bqj", "rating": "div._3LWZlK, div.XQDdHH",
                     "link": "a._1fQZEK, a.s1Q9rs, a.IRpwTa, a.CGtC98"},
    "amazon.": {"card": "div[data-component-type='s-search-result']",
                "title": "h2 a span, h2 span", "price": "span.a-price span.a-offscreen",
                "rating": "span.a-icon-alt", "link": "h2 a, a.a-link-normal.s-no-outline"},
}


def selectors_for(url: str) -> Optional[Dict[str, str]]:
    host = (urlparse(url).hostname or "").lower()
    for key, cfg in SITE_SELECTORS.items():
        if key in host:
            return cfg
    return None


# JS that extracts a structured product list. Given an optional selector config it
# uses it; otherwise it price-anchors: any card-ish element whose text contains a
# currency amount and a link becomes a product. Read-only DOM inspection.
PRODUCT_EXTRACT_JS = r"""
(cfg) => {
  const clean = s => (s || '').replace(/\s+/g, ' ').trim();
  const abs = h => { try { return new URL(h, location.href).href; } catch (e) { return h || ''; } };
  const priceRe = /(₹|Rs\.?|INR|\$|£|€)\s?\d[\d,]*(\.\d+)?/;
  let cards = [];
  if (cfg && cfg.card) cards = Array.from(document.querySelectorAll(cfg.card));
  if (!cards.length) {
    const cand = [];
    document.querySelectorAll('li, article, div').forEach(el => {
      if (!el.children || el.children.length === 0) return;
      const t = el.textContent || '';
      if (t.length > 500 || !priceRe.test(t)) return;
      if (!el.querySelector('a[href]')) return;
      cand.push(el);
    });
    // keep the smallest (leaf-most) price-bearing containers
    cards = cand.filter(el => !cand.some(o => o !== el && el.contains(o)));
  }
  const out = [];
  for (const el of cards) {
    const q = sel => { try { return sel ? el.querySelector(sel) : null; } catch (e) { return null; } };
    const titleEl = q(cfg && cfg.title)
        || el.querySelector('h1,h2,h3,h4,.title,[class*=title]')
        || el.querySelector('a[title]') || el.querySelector('img[alt]');
    let title = '';
    if (titleEl) title = clean(titleEl.getAttribute && (titleEl.getAttribute('title') || titleEl.getAttribute('alt')))
        || clean(titleEl.textContent);
    const priceEl = q(cfg && cfg.price);
    let price = clean(priceEl && priceEl.textContent);
    if (!price) { const m = (el.textContent || '').match(priceRe); price = m ? m[0] : ''; }
    let rating = '';
    const rEl = q(cfg && cfg.rating);
    if (rEl) rating = clean(rEl.getAttribute('aria-label') || rEl.getAttribute('title')
        || rEl.getAttribute('class') || rEl.textContent);
    const linkEl = q(cfg && cfg.link) || el.querySelector('a[href]');
    const url = linkEl ? abs(linkEl.getAttribute('href')) : '';
    if (title && price) out.push({ title: title.slice(0, 160), price: price.slice(0, 40),
                                   rating: rating.slice(0, 60), url });
    if (out.length >= 24) break;
  }
  return out;
}
"""


def clean_products(rows: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    """Tidy extractor output (e.g. turn 'star-rating Three' into 'Three stars')."""
    out = []
    seen = set()
    for r in rows or []:
        title = (r.get("title") or "").strip()
        url = (r.get("url") or "").strip()
        if not title or url in seen:
            continue
        seen.add(url)
        rating = (r.get("rating") or "").strip()
        m = re.search(r"star-rating\s+(\w+)", rating)
        if m:
            rating = f"{m.group(1)} stars"
        out.append({"title": title, "price": (r.get("price") or "").strip(),
                    "rating": rating, "url": url})
    return out


# ── Bot-wall / login-wall / CAPTCHA detection (detect, never bypass) ──────────
_BOTWALL_PATTERNS = (
    "captcha", "recaptcha", "hcaptcha", "are you a robot", "are you a human",
    "verify you are human", "verify you're human", "confirm you are not a robot",
    "unusual traffic", "enter the characters", "press and hold", "security check",
    "access denied", "bot detected", "to continue, please verify",
)
_LOGINWALL_PATTERNS = (
    "sign in to continue", "log in to continue", "login to continue",
    "please sign in", "please log in", "you must be logged in",
    "sign in to your account to continue",
)


def detect_bot_wall(text: str, url: str = "") -> Optional[str]:
    """Return a reason string if a CAPTCHA/bot-check/login-wall is detected, else
    None. We DETECT and hand off to the human; we never try to solve or evade."""
    low = (text or "").lower()
    if any(p in low for p in _BOTWALL_PATTERNS):
        return "captcha_or_bot_check"
    if any(p in low for p in _LOGINWALL_PATTERNS):
        return "login_required"
    return None


# ── Per-task add-to-cart cap (thread-local: one shopping run per worker) ───────
_cart = threading.local()


def reset_cart() -> None:
    _cart.count = 0


def cart_count() -> int:
    return int(getattr(_cart, "count", 0))


def can_add_to_cart() -> bool:
    return cart_count() < MAX_CART_ADDITIONS


def note_cart_addition() -> bool:
    """Record one addition; return False if the cap is already reached."""
    if not can_add_to_cart():
        return False
    _cart.count = cart_count() + 1
    return True


HANDOFF_PAYMENT = ("🛒 Cart is ready. I stop at the cart by design — please review "
                   "the items and complete payment/checkout yourself in the browser "
                   "window. I never enter card/UPI/OTP details.")


# ── Query -> search URL, and NL request parsing (for the chat trigger) ────────
SEARCH_URL_TEMPLATES = {
    "flipkart": "https://www.flipkart.com/search?q={q}",
    "amazon": "https://www.amazon.in/s?k={q}",
    "myntra": "https://www.myntra.com/{q}",
    "snapdeal": "https://www.snapdeal.com/search?keyword={q}",
}
_FILLER = {"pe", "par", "peh", "on", "for", "me", "mein", "ek", "a", "an", "the",
           "dhundo", "dhoondo", "dhundho", "search", "find", "look", "up", "buy",
           "shopping", "shop", "product", "please", "karo", "chahiye", "ka", "ki"}


def build_search_url(query: str, site: Optional[str] = None) -> str:
    from urllib.parse import quote_plus
    site = site if site in SEARCH_URL_TEMPLATES else "flipkart"
    return SEARCH_URL_TEMPLATES[site].format(q=quote_plus((query or "").strip()))


def parse_shopping_request(text: str):
    """Best-effort extract of (site, query) from a NL shopping request."""
    t = (text or "").strip()
    low = t.lower()
    site = next((s for s in SEARCH_URL_TEMPLATES if s in low), None)
    words = [w for w in re.findall(r"[a-z0-9\-']+", low)
             if w not in _FILLER and w not in SEARCH_URL_TEMPLATES]
    query = " ".join(words).strip() or t
    return site, query
