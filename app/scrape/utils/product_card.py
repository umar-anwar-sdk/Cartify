import re
import json
import time
from typing import Dict, Any, List, Optional, Set
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
from .product_other import *
def extract_from_product_card(soup: BeautifulSoup, base_url: str) -> Dict[str, Any]:
       
    result = {"name": None, "price": None, "description": None, "gallery_images": []}
    card_div = None

    for div in soup.find_all("div"):
        cls = " ".join(div.get("class") or []).lower()
        id_ = (div.get("id") or "").lower()
        if matches_keywords(cls, product_card_keywords) or matches_keywords(id_, product_card_keywords):
            card_div = div
            break
    if not card_div:
        return result
    
    for tag in ["h1", "h2", "h3", "span", "p", "div"]:
        for el in card_div.find_all(tag):
            text = el.get_text(" ", strip=True)
            if text and (matches_keywords(" ".join(el.get("class") or []), NAME_KEYWORDS) or tag in ["h1", "h2"]):
                result["name"] = text
                break
        if result["name"]:
            break

   
    card_text = card_div.get_text(" ", strip=True)
    m = PRICE_KEYWORD_RE.search(card_text)
    if m:
        result["price"] = m.group(1)
    else:
        m2 = PRICE_RE.search(card_text)
        if m2:
            cur1 = (m2.group("currency") or "").strip()
            amt = m2.group("amount")
            cur2 = (m2.group("currency2") or "").strip()
            result["price"] = f"{cur1} {amt} {cur2}".strip()
            


    longest = ""
    for tag in ["p", "div", "span"]:
        for el in card_div.find_all(tag):
            text = el.get_text(" ", strip=True)
            if text and len(text) > len(longest) and len(text) > 40:
                longest = text
    if longest:
        result["description"] = longest

    imgs: Set[str] = set()
    for img in card_div.find_all("img"):
        for attr in ["src", "data-src", "data-lazy-src"]:
            if img.has_attr(attr):
                imgs.add(urljoin(base_url, img[attr]))
    for pic in card_div.find_all("picture"):
        for source in pic.find_all("source"):
            if source.has_attr("srcset"):
                for srcset in source["srcset"].split(","):
                    url_part = srcset.strip().split(" ")[0]
                    if url_part:
                        imgs.add(urljoin(base_url, url_part))
    if imgs:
        result["gallery_images"] = list(imgs)

    return result
