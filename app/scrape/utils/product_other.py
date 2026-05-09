import re
import json
import time
from typing import Dict, Any, List, Optional, Set
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
from .extract_json import extract_jsonld


PRICE_KEYWORD_RE = re.compile(
    r'(?i)(?:price|our price|now|special|discount|sale)[^<]{0,80}'
    r'([0-9]{1,3}(?:[.,][0-9]{3})*(?:[.,][0-9]{1,2})?)\b'
)

NAME_KEYWORDS = [
    "product-title", "product_name", "productname", "title", "headline", "item-title",
    "product-heading", "name", "producthead", "h1-product", "title-main", "pdp-title"
]

PRICE_KEYWORDS = [
    "pdp-price_color_orange", "price", "prices","product-price", "cost", "our-price", "sale-price",
    "current-price", "price_current", "price-final", "amount", "amt", "you-pay",
    "discounted-price", "listing-price"
]

DESCRIPTION_KEYWORDS = [
    "description", "product-description", "about-product", "product-details",
    "item-details", "short-description", "long-description", "desc", "summary",
    "overview", "features", "specification", "specs"
]

IMAGE_KEYWORDS = [
    "product", "product-image", "product_images", "main-image",
    "product-gallery", "product-photo", "variant", "gallery-item"
]

product_card_keywords = [
    "pdp-block__main-information","ppd","center-panel-container vi-mast","main-content","product-overview", "product_overview","product-single", 
    "product_single", "product", "product-info-main","productView", 
    "product__page-container", "shopify-section", "product-view",
    "productView-product-info", "product-details", "main-product-page","product-section",
    "section-body"
]

PRICE_RE = re.compile(
    r'(?P<currency>(?:'                 
    r'[A-Z]{2,3}'                       
    r'|Rs'                               
    r'|د.إ'                               
    r'|[$€£₹¥₽₩₺₨₦₴₱₫₡₲₭₮₸₺₼₿₺₸₼₡₢₥₧₯₰₲₳₴₵₶₷₸₺₻₼₽₾₿]' 
    r')\.?)?\s*'                         
    r'(?P<amount>\d{1,10}'              
    r'(?:,\d{3})*'                      
    r'(?:\.\d{1,2})?'                   
    r')\s*'
    r'(?P<currency2>(?:'                 
    r'[A-Z]{2,3}'
    r'|Rs'
    r'|د.إ'
    r'|[$€£₹¥₽₩₺₨₦₴₱₫₡₲₭₮₸₺₼₿₺₸₼₡₢₥₧₯₰₲₳₴₵₶₷₸₺₻₼₽₾₿]'
    r')\.?)?',
    re.IGNORECASE
)

PRICE_PREFIXES = ["now", "only", "price:", "sale:", "just", "today", "from"]
INSTALLMENTS_WORD = "installments"



def matches_keywords(text: str, keywords: List[str]) -> bool:
    if not text:
        return False
    text_lower = text.lower()
    return any(kw in text_lower for kw in keywords)



def find_price_in_text(text: str) -> Optional[str]:
    if INSTALLMENTS_WORD in text.lower():
        return None
    m = PRICE_RE.search(text)
    if m:
        price_str = m.group(0).strip()
        amount = m.group('amount')
        if amount and float(amount.replace(',', '')) == 0:
            return None
        return price_str
    return None

def get_gallery_images(soup: BeautifulSoup, base_url: str) -> List[str]:
    imgs: Set[str] = set()
    data = extract_jsonld(soup)
    if data:
        images_ld = data.get("image") or data.get("images")
        if images_ld:
            if isinstance(images_ld, str):
                imgs.add(urljoin(base_url, images_ld))
            elif isinstance(images_ld, list):
                for im in images_ld:
                    if im:
                        imgs.add(urljoin(base_url, im))

    gallery_containers = []
    for tag in ["div", "ul", "section", "figure"]:
        for el in soup.find_all(tag):
            cls = " ".join(el.get("class") or []).lower()
            id_ = (el.get("id") or "").lower()
            if any(kw in cls for kw in IMAGE_KEYWORDS) or any(kw in id_ for kw in IMAGE_KEYWORDS):
                gallery_containers.append(el)

    for container in gallery_containers:
        for img in container.find_all("img"):
            for attr in ["src", "data-src", "data-lazy-src"]:
                if img.has_attr(attr):
                    imgs.add(urljoin(base_url, img[attr]))

        for pic in container.find_all("picture"):
            for source in pic.find_all("source"):
                if source.has_attr("srcset"):
                    for srcset in source["srcset"].split(","):
                        url_part = srcset.strip().split(" ")[0]
                        if url_part:
                            imgs.add(urljoin(base_url, url_part))

    return list(imgs)


def extract_price(soup: BeautifulSoup) -> Optional[str]:
    el = soup.find(attrs={"data-test-id": "PriceDisplay"})
    if el:
        pr = find_price_in_text(el.get_text(" ", strip=True))
        if pr:
            return pr

    custom_div = soup.find(
        "div",
        class_=lambda c: c and "text-text_primary" in c and "font-extrabold" in c
    )
    if custom_div:
        txt = custom_div.get_text(" ", strip=True)
        pr = find_price_in_text(txt)
        if pr:
            return pr

    for el in soup.find_all("sale-price"):
        text = el.get_text(" ", strip=True)
        if text:
            pr = find_price_in_text(text)
            if pr:
                return pr

    for tag in ["span", "div", "p", "li", "strong", "b"]:
        for el in soup.find_all(tag):
            text = el.get_text(" ", strip=True)
            if not text:
                continue
            cls = " ".join(el.get("class") or []).lower()
            id_ = (el.get("id") or "").lower()
            itemprop = (el.get("itemprop") or "").lower()
            data_fs = el.get("data-fs-element", "").lower()

            if (
                matches_keywords(cls, PRICE_KEYWORDS)
                or matches_keywords(id_, PRICE_KEYWORDS)
                or itemprop == "price"
                or data_fs == "price"
            ):
                pr = find_price_in_text(text)
                if pr:
                    return pr

    return None
