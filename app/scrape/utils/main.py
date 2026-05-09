import re
import json
import time
from typing import Dict, Any, List, Optional, Set
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
from .product_other import *                      
from .product_card import extract_from_product_card 
from .product_meta import extract_meta_data        
from .extract_json import extract_jsonld          
from .product_itemprop import extract_from_itemprops
from fake_useragent import UserAgent
DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
    "Connection": "keep-alive",
}

from urllib.parse import urlparse

def get_site_name(url):
    netloc = urlparse(url).netloc
    parts = netloc.split('.')
    if parts[0] == 'www':
        parts = parts[1:]
    return parts[0]


# DEFAULT_HEADERS = {
#     "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
#                   "AppleWebKit/537.36 (KHTML, like Gecko) "
#                   "Chrome/120.0.0.0 Safari/537.36",
#     "Accept-Language": "en-US,en;q=0.9",
#     "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
#     "Referer": "https://www.google.com/",
# }



def fetch_html(url: str, timeout: int = 120, render_js: bool = False) -> str:
    ua = UserAgent()
    headers = DEFAULT_HEADERS.copy()
    headers["User-Agent"] = ua.random  
    print(f"Fetching {url} with User-Agent: {headers['User-Agent']}...")
    time.sleep(2)
    if not render_js and 'daraz' not in url.lower():
        print("Fetching without JS rendering...")
        resp = requests.get(url, headers=headers, timeout=timeout)
        resp.raise_for_status()
        print(resp.status_code)
        return resp.text,get_site_name(url)
    else:
        print("Rendering with Playwright...")
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(user_agent=headers["User-Agent"])
            response = page.goto(url, wait_until="networkidle", timeout=300000)
            print("Status Code:", response.status)
            time.sleep(2)
            html = page.content()
            browser.close()
            return html,get_site_name(url)
        
        
        
def names_similar(a: Optional[str], b: Optional[str]) -> bool:
   
    if not a or not b:
        return False
    def norm(s: str) -> List[str]:
        s2 = re.sub(r'[^a-z0-9\s]', ' ', s.lower())
        tokens = [t for t in s2.split() if t]
        return tokens
    ta = norm(a)
    tb = norm(b)
    if not ta or not tb:
        return False
    set_a = set(ta)
    set_b = set(tb)
    overlap = len(set_a & set_b)
    ratio = overlap / min(len(set_a), len(set_b))
    return ratio >= 0.6 or ta == tb


def scrape_product(url: str, render_js: bool = False) -> Dict[str, Any]:
    print("Scraping product from:", url)
    html,sitename = fetch_html(url, render_js=render_js)
    
    soup = BeautifulSoup(html, "html.parser")
    base_url = url

    output: Dict[str, Any] = {
        "source": url,
        "site_name": sitename,
        "name": None,
        "price": None,
        "description": None,
        "gallery_images": []
    }

    meta_info = extract_meta_data(soup) or {}
    
    for k in ("name", "price", "description", "gallery_images"):
        if meta_info.get(k):
            output[k] = meta_info[k]

    needjsonld = extract_jsonld(soup)
    if needjsonld:
        if not output["name"] and needjsonld.get("name"):
            output["name"] = needjsonld["name"].strip()
        if not output["description"] and needjsonld.get("description"):
            output["description"] = needjsonld["description"].strip()
        if not output["gallery_images"] and needjsonld.get("image"):
            imgs_ld = needjsonld.get("image")
            if isinstance(imgs_ld, str):
                output["gallery_images"] = [urljoin(base_url, imgs_ld)]
            elif isinstance(imgs_ld, list):
                output["gallery_images"] = [urljoin(base_url, i) for i in imgs_ld if i]

        offers = needjsonld.get("offers")

        def extract_price_block(offer: dict) -> Optional[str]:
            if not isinstance(offer, dict):
                return None
            p = offer.get("price")
            c = offer.get("priceCurrency")
            if not p  and offer.get("priceSpecification"):
                price_specs = offer.get("priceSpecification")
                if isinstance(price_specs, list) and price_specs:
                    spec = price_specs[0]
                    p = spec.get("price")
                    c = spec.get("priceCurrency")
            if not p:
                return None
            return (str(c).strip() + " " + str(p).strip()) if c else str(p).strip()

        if not output["price"] :
            if isinstance(offers, dict):
                maybe_price = extract_price_block(offers)
                if maybe_price:
                    output["price"] = maybe_price
            elif isinstance(offers, list):
                for off in offers:
                    maybe_price = extract_price_block(off)
                    if maybe_price:
                        output["price"] = maybe_price
                        break



    need_itemprop = any(output[k] in (None, [], "") for k in ("name", "price", "description"))
    if need_itemprop:
        itemprop_data = extract_from_itemprops(soup, base_url)
        for k in ("name", "price", "description", "gallery_images"):
            if itemprop_data.get(k) and (output[k] in (None, [], "")):
                output[k] = itemprop_data[k]
   
   
    need_card = any(output[k] in (None, [], "") for k in ("name", "price", "description"))
    if need_card:
        try:
            card_data = extract_from_product_card(soup, base_url) 
        except TypeError:
            try:
                card_data = extract_from_product_card(soup)
                
            except Exception:
                card_data = {}
        card_data = card_data or {}

        if not output["name"] and card_data.get("name"):
            output["name"] = card_data.get("name")

        if not output["description"] and card_data.get("description"):
            output["description"] = card_data.get("description")

        if (not output["gallery_images"] or len(output["gallery_images"]) <=1) and card_data.get("gallery_images"):
            output["gallery_images"] = card_data.get("gallery_images")

        
        if not output["price"] and card_data.get("price"):
            if output["name"]:
                card_name = card_data.get("name")
                if card_name and names_similar(output["name"], card_name):
                    output["price"] = card_data.get("price")
                else:
                    pass
            else:
                output["price"] = card_data.get("price")

    imgs_list: List[str] = []
    if output.get("gallery_images"):
        seen: Set[str] = set()
        for im in output["gallery_images"]:
            if not im:
                continue
            im_abs = urljoin(base_url, im)
            if im_abs not in seen:
                seen.add(im_abs)
                imgs_list.append(im_abs)
    output["gallery_images"] = imgs_list

    
    if output["price"] == None:
        price_data=extract_price(soup)
        if price_data:
            output["price"]=price_data
            
    output["gallery_images"] = [img for img in output["gallery_images"] if ".svg" not in img and 
                                 not any(x in img.lower() for x in ['button', 'payment','icon', 'banner', 'category', 'nav', 'menu'])]

    return output


# if __name__ == "__main__":
    
#     test_urls = [
#         # "https://penworld.com.pk/product/cross-click-medalist-ballpoint-pen-at0622-122/"
#         # "https://priceoye.pk/wireless-earbuds/assorted/m10-tws-wireless-bluetooth-earbuds"
#         # "https://www.walmart.com/ip/Raycon-The-Everyday-Bluetooth-Earbuds-True-Wireless-with-Charging-Case-and-Microphone-Noise-Canceling-Blush-Violet-RBE726-23E-PUR/6113273821?classType=REGULAR&adsRedirect=true"
#         # "https://www.logoofficial.com/collections/accessories/products/vch001-blk"
#         # "https://wolf.pk/products/the-vertique-a-leather-cardholder-wallet"
#         # "https://chasevalue.pk/products/mens-leather-card-holder-black-chase-value-a191349-a-black?variant=41857658060877"
#         # "https://zellbury.com/products/wallet-mw25e007"
#         # "https://hub.com.pk/collections/view-all/products/mw0343-045"
#         # "https://jafferjees.com/products/burano-wallet"
#         ##"https://wisemarket.com.pk/collection/wireless-earbuds/other-earbuds/m10-tws-wireless-earbuds?utm_source=Ramzan-Sale-PMax&utm_medium=paid_video&utm_campaign=Pmax&gad_source=1&gad_campaignid=20437306223&gbraid=0AAAAAp_9oEB7kKRvnnEIX07f96cJZq7sc&gclid=Cj0KCQjw58PGBhCkARIsADbDilwqMBzJZ43xmmt94Be28FDKAv4r0n68giG6Upr8z7qR0JBIv5pnPsQaAiK4EALw_wcB"
#         # "https://www.daraz.pk/products/1-4-1-4-i464802846-s2196572635.html?c=&channelLpJumpArgs=&clickTrackInfo=query%253A%253Bnid%253A464802846%253Bsrc%253ALazadaMainSrp%253Brn%253A5a87a1ec9562a4bc06b4efc8213ce328%253Bregion%253Apk%253Bsku%253A464802846_PK%253Bprice%253A599%253Bclient%253Adesktop%253Bsupplier_id%253A6005010630001%253Bbiz_source%253Ah5_external%253Bslot%253A1%253Butlog_bucket_id%253A470687%253Basc_category_id%253A10002213%253Bitem_id%253A464802846%253Bsku_id%253A2196572635%253Bshop_id%253A336179%253BtemplateInfo%253A1103_L%2523-1_A3_C%2523&freeshipping=0&fs_ab=1&fuse_fs=&lang=en&location=Sindh&price=599&priceCompare=skuId%3A2196572635%3Bsource%3Alazada-search-voucher%3Bsn%3A5a87a1ec9562a4bc06b4efc8213ce328%3BoriginPrice%3A59900%3BdisplayPrice%3A59900%3BsinglePromotionId%3A-1%3BsingleToolCode%3AmockedSalePrice%3BvoucherPricePlugin%3A0%3Btimestamp%3A1758616288491&ratingscore=4.670807453416149&request_id=5a87a1ec9562a4bc06b4efc8213ce328&review=161&sale=747&search=1&source=search&spm=a2a0e.searchlistcategory.list.1&stock=1"
#         # "https://www.hushpuppies.com.pk/products/knott-runner"

# # Blockage issue in amazon site

#         # #"https://www.amazon.com/HAMITOR-Toilet-Brush-Holder-Set/dp/B0CPXV2K34/ref=sr_1_3_sspa?adgrpid=157985876525&dib=eyJ2IjoiMSJ9.RdLC8yEnjL1wd5azZ9ZAf-13sStYOFuIEKW0gVZjjnbVr67ebGIDSlR7L-xnmcY-hdhfYbjREoJu2C22oE5-Mp0IRIKZxM5vNaGBHXCuWivaKuNfYIctRqY6CiqRzbFIeNV5noMMjDFVvr7CB8iZZBfG7e6d4tVdOl8Wdan6iKwdrj9ymeTam6Rz3EID-1GRgkMpOfhXM48_7bNS2yhzry3G_QZSIRVE_F5oXt2vTmIYtITg1q-veAE2Rq3rfyhtSnKMcjZ9sFZUZmbfwx1akrSBEa2zGr0g0I14stAwAsA.cNdHaYg1G-E0iVltmLd5llBue4JnxyXsgmwfe-8k1Rc&dib_tag=se&hvadid=692772616277&hvdev=c&hvlocphy=9060971&hvnetw=g&hvqmt=b&hvrand=1616699690704855014&hvtargid=kwd-759299130614&hydadcr=29250_14785303&keywords=small%2Bhead%2Btoilet%2Bbrush&mcid=e8db6c0fc4453d108ce7b9399c33b362&qid=1758550148&sr=8-3-spons&sp_csd=d2lkZ2V0TmFtZT1zcF9hdGY&th=1"
#         # "https://www.alibaba.com/product-detail/Photochromic-Anti-Radiation-Glasses-for-Men_1601184703815.html?spm=a2700.product_home_fy25.just_for_you.3.227567af994KJn"
#         # "https://www.gulahmedshop.com/poly-cambric-printed-shirt-ips-44502"
#         # "https://saharonline.pk/collections/dobby-jacquard/products/greystone-garden?variant=50711627202873"
#         # "https://nishatlinen.com/collections/men/products/42508095"
#         # "https://mohagni.com/products/spl-19-3pc-stitched?variant=43137276903533"
#         # "https://krosskulture.com/collections/rohani/products/ezlyn?variant=46856874426622"
#         # "https://www.sokamal.com/collections/grip-pret/products/dg11?variant=45319960821916"
#         # "https://laam.pk/products/kriti-black"
#         # "https://furorjeans.com/products/hawaiian-collar-shirt-fmts5-32209"
#         # "https://lomiea.com/products/printed-blazer-mini-dress-feather-cuffs-bold-chic"
#         # "https://serenabutelondon.com/products/double-breasted-blazer-navy-blue"
#         # "https://www.next.co.uk/style/su576540/w33535"
#         # "https://cliveshoes.com/products/m195104-blk?srsltid=AfmBOorsGs07pEpXG0ro-xX8upYfcWzyyjpYCwfSBwoVvCRiaxaZBA1B&variant=50683835318553"
#         # "https://clubllondon.com/products/isla-bottle-green-crew-neck-maxi-dress-with-cape-sleeve-cl136357047"
#         # "https://hyggecorner.pk/products/foldable-bamboo-laundry-basket"
#         # "https://homsstore.com/collections/baskets/products/leather-basket-with-tissue-box-1"
#         # "https://adobasics.com/products/water-hyacinth-basket-with-stain-resistant-wooden-handles-gold-plated"
#         # "https://www.ikea.com/ca/en/p/uppdatera-box-white-20546467/"
#         # "https://appollostore.com/products/polka-basket"
#         # "https://www.idealancy.pk/multipurpose-divider-basket"
#         # "https://habitt.com/products/metal-curve-basket"
#         # "https://alfatah.pk/products/exercise-kettle-bell-dumble-10kg-ir-lm-4053?srsltid=AfmBOopSrL8eOEnMVZ_mvh9oXiROMVManbGLWvPh1N_YYJhIR-7HC5uJ"
#         # "https://www.masteroffisys.com/products/master-executive-vc-ys-1202c"
#         # "https://interwood.pk/collections/seating-chairs/products/buzz-sofa-chair"
#         # "https://interwood.pk/collections/seating-chairs/products/sofa-vigo-1-seater"
#         # "https://chair.com.pk/product/david-eb-high-back-computer-chair/"
#         # "https://chenone.com/products/porter-room-chair?variant=43552404504792"
#         # "https://livinart.pk/collections/chairs/products/victoria-mid-back-chair"
#         # "https://www.masteroffisys.com/products/master-executive-hbc-noir"
#         # "https://www.back2.co.uk/products/hag-capisco-8106-showroom-model-brown?_pos=17&_sid=ac32f3b90&_ss=r"
#         # "https://renrayhealthcare.com/product/florida-30-4-drawer-chest/"
#         # "https://www.wayfair.co.uk/furniture/pdp/17-stories-2-seater-sofa-corduroy-u110420363.html?piid=845738131"
#         # "https://www.furniturevillage.co.uk/hadley-ottoman-bed-frame/ZFRSP000000000003441.html"
#         # "https://www.officechairsuk.co.uk/shop/humanscale-freedom-chair-with-headrest-graphite-frame-black-fabric/"
#         # "https://www.officechairsuk.co.uk/shop/humanscale-freedom-chair-with-headrest-graphite-frame-black-fabric/"
#         # "https://www.next.co.uk/style/st541215/653912"
#         # "https://xrocker.co.uk/products/fury-rgb-junior-gaming-chair"
#         # "https://boulies.co.uk/products/master?variant=43805565255923"
#         # "https://stunningchairs.co.uk/collections/tub-chairs/products/faux-leather-suede-brown-aviator-tub-chair"
#         # "https://chronologystore.co.uk/collections/desks/products/rustic-scaffold-board-desk-on-steel-tube-legs-industrial-reclaimed-style?_gl=1*12ktosm*_up*MQ..&gclid=CjwKCAjwlt7GBhAvEiwAKal0cm0ckorGfgeZz56KQhQNsiicrQ8RQmOpsb263MjuppEQswtj2WxRcxoCke0QAvD_BwE&gbraid=0AAAAAogUH8LNkz8i8_tSTs4T7CKP7V1Irr"
#         # "https://www.thecontractchair.co.uk/product/martinica-armchair"
#         # "https://www.argoswatch.in/products/apollo-iii-chocolate-brown-silver-w-steel-bracelet"
#         # "https://www.johnlewis.com/levis-ribcage-ultra-high-rise-jeans-shaded-view/p113694355"
#         # "https://www.johnlewis.com/converse-chuck-taylor-all-star-canvas-hi-top-trainers-black/p114061400"
#         # "https://www.marksandspencer.com/supersoft-striped-polo-jumper-with-wool/p/clp60745628?color=GREYMIX#intid=pid_pg1pip48g4r1c3"
#         "https://jenny-store.com/product/louis-vuittonsize-36-to-41/"
#         ]
#     for u in test_urls:
#         try:
#             print("Scraping:", u)
#             result = scrape_product(u, render_js=False)
#             print(json.dumps(result, indent=2, ensure_ascii=False))
#         except Exception as e:
#             print(f"Error scraping {u}: {e}")
