
import re
import json
import time
from typing import Dict, Any, List, Optional, Set
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
from .product_other import *

def extract_meta_data(soup: BeautifulSoup) -> Dict[str, Any]:
    meta_data: Dict[str, Any] = {
        "name": None,
        "price": None,
        "description": None,
        "gallery_images": []
    }
    images: Set[str] = set()

    for tag in soup.find_all("meta"):
        prop = (tag.get("property") or tag.get("name") or "").lower()
        content = tag.get("content", "").strip()
        if not prop or not content:
            continue

        if prop in ("og:title", "twitter:title", "title"):
            meta_data["name"] = meta_data["name"] or content

        if prop in ("og:description", "twitter:description", "description"):
            meta_data["description"] = meta_data["description"] or content

        if prop in ("og:image", "twitter:image", "twitter:image:src", "image"):
            images.add(content)

        if "price" in prop or "amount" in prop or "currency" in prop:
            m = PRICE_RE.search(content)
            if m:
                cur1 = (m.group("currency") or "").strip()
                amt = m.group("amount")
                cur2 = (m.group("currency2") or "").strip()
                price_string = f"{cur1} {amt} {cur2}".strip()
                meta_data["price"] = meta_data["price"] or price_string
            elif "currency" in prop and meta_data["price"] and not any(c.isalpha() for c in meta_data["price"]):
                meta_data["price"] = f"{content} {meta_data['price']}"

    if images:
        meta_data["gallery_images"] = list(images)

    return meta_data