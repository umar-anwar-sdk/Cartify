# product_itemprop.py
import re
from typing import Dict, Any, List, Set
from urllib.parse import urljoin
from bs4 import BeautifulSoup

def extract_from_itemprops(soup: BeautifulSoup, base_url: str) -> Dict[str, Any]:
    
    out: Dict[str, Any] = {
        "name": None,
        "price": None,
        "description": None,
        "gallery_images": []
    }

    name_tag = soup.find(attrs={"itemprop": re.compile(r"^(name|headline)$", re.I)})
    if name_tag:
        out["name"] = name_tag.get_text(" ", strip=True)

    desc_tag = soup.find(attrs={"itemprop": re.compile(r"^(description|about)$", re.I)})
    if desc_tag:
        if desc_tag.name == "meta" and desc_tag.get("content"):
            out["description"] = desc_tag["content"].strip()
        else:
            out["description"] = desc_tag.get_text(" ", strip=True)

    price_tag = soup.find(attrs={"itemprop": re.compile(r"^(price)$", re.I)})
    if price_tag:
        if price_tag.get("content"):
            price_val = price_tag["content"].strip()
        else:
            price_val = price_tag.get_text(" ", strip=True)

        
        currency_tag = soup.find(attrs={"itemprop": re.compile(r"^(priceCurrency)$", re.I)})
        currency_val = currency_tag.get("content").strip() if (currency_tag and currency_tag.get("content")) else ""
        out["price"] = f"{currency_val}{price_val}".strip()

    
    seen: Set[str] = set()
    for img in soup.find_all(attrs={"itemprop": re.compile(r"^(image)$", re.I)}):
        src = img.get("src") or img.get("content")
        if not src:
            continue
        full = urljoin(base_url, src)
        if full not in seen:
            seen.add(full)
            out["gallery_images"].append(full)

    return out
