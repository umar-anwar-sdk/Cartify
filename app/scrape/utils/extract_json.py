import re
import json
from typing import Dict, Any, Optional
from bs4 import BeautifulSoup

def extract_jsonld(soup: BeautifulSoup) -> Optional[Dict[str, Any]]:
    def is_product(obj: dict) -> bool:
        t = obj.get("@type")
        if isinstance(t, str):
            return t.lower() == "product"
        if isinstance(t, list):
            return any(isinstance(x, str) and x.lower() == "product" for x in t)
        return False

    scripts = soup.find_all("script", type="application/ld+json")
    for script in scripts:
        text = script.string
        if not text:
            continue
        try:
            data = json.loads(text.strip())
        except json.JSONDecodeError:
            try:
                text_fixed = re.sub(r',\s*}', '}', text)
                data = json.loads(text_fixed)
            except Exception:
                continue

        if isinstance(data, dict):
            if is_product(data):
                return data
            if "@graph" in data and isinstance(data["@graph"], list):
                for item in data["@graph"]:
                    if isinstance(item, dict) and is_product(item):
                        return item

        elif isinstance(data, list):
            for item in data:
                if isinstance(item, dict) and is_product(item):
                    return item

    return None
