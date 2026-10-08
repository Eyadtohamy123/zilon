import json
import re
import logging
from selectolax.parser import HTMLParser

logger = logging.getLogger("WebScraper3.0")

def clean_text(text):
    if not text:
        return ""
    return re.sub(r'\s+', ' ', text).strip()

class EcommerceExtractor:
    """Specialized extractor for e-commerce products (Amazon, Shopify, general stores)."""

    def __init__(self, url, html_content, tree=None):
        self.url = url
        self.html_content = html_content
        self.tree = tree if tree else HTMLParser(html_content)
        self.product_data = {
            "url": self.url,
            "product_name": "",
            "price": "",
            "currency": "",
            "availability": "",
            "brand": "",
            "sku_asin": "",
            "rating": "",
            "review_count": "",
            "main_image": "",
            "description": ""
        }

    def _extract_from_json_ld(self):
        """Extract structured product data from schema.org JSON-LD scripts."""
        for script in self.tree.css("script[type='application/ld+json']"):
            try:
                data = json.loads(script.text())
                # Handle lists of objects or single objects
                items = data if isinstance(data, list) else [data]
                
                # Check for @graph arrays (common in Yoast SEO / WooCommerce)
                if isinstance(data, dict) and "@graph" in data:
                    items = data["@graph"]

                for item in items:
                    if not isinstance(item, dict):
                        continue
                    
                    item_type = item.get("@type", "")
                    if item_type == "Product" or (isinstance(item_type, list) and "Product" in item_type):
                        if not self.product_data["product_name"]:
                            self.product_data["product_name"] = item.get("name", "")
                        
                        if not self.product_data["brand"]:
                            brand = item.get("brand", "")
                            if isinstance(brand, dict):
                                self.product_data["brand"] = brand.get("name", "")
                            elif isinstance(brand, str):
                                self.product_data["brand"] = brand
                                
                        if not self.product_data["sku_asin"]:
                            self.product_data["sku_asin"] = item.get("sku", "") or item.get("mpn", "")
                            
                        if not self.product_data["description"]:
                            self.product_data["description"] = clean_text(item.get("description", ""))
                            
                        if not self.product_data["main_image"]:
                            img = item.get("image", "")
                            if isinstance(img, list) and img:
                                self.product_data["main_image"] = img[0]
                            elif isinstance(img, dict):
                                self.product_data["main_image"] = img.get("url", "")
                            elif isinstance(img, str):
                                self.product_data["main_image"] = img

                        # Offers (Price & Availability)
                        offers = item.get("offers", "")
                        if isinstance(offers, dict):
                            self._parse_offer(offers)
                        elif isinstance(offers, list) and offers:
                            self._parse_offer(offers[0])
                            
                        # Ratings
                        rating = item.get("aggregateRating", {})
                        if isinstance(rating, dict):
                            if not self.product_data["rating"]:
                                self.product_data["rating"] = str(rating.get("ratingValue", ""))
                            if not self.product_data["review_count"]:
                                self.product_data["review_count"] = str(rating.get("reviewCount", ""))
            except Exception:
                pass # JSON parse error, move on

    def _parse_offer(self, offer):
        """Helper to parse schema.org Offer object."""
        if not self.product_data["price"]:
            self.product_data["price"] = str(offer.get("price", ""))
        if not self.product_data["currency"]:
            self.product_data["currency"] = offer.get("priceCurrency", "")
        if not self.product_data["availability"]:
            avail = offer.get("availability", "")
            if "InStock" in avail:
                self.product_data["availability"] = "In Stock"
            elif "OutOfStock" in avail:
                self.product_data["availability"] = "Out of Stock"

    def _extract_amazon_heuristics(self):
        """Extract data using CSS selectors tailored specifically for Amazon."""
        if "amazon." not in self.url.lower():
            return

        # ASIN from URL
        asin_match = re.search(r'/(?:dp|gp/product|exec/obidos/ASIN)/([A-Z0-9]{10})', self.url)
        if asin_match and not self.product_data["sku_asin"]:
            self.product_data["sku_asin"] = asin_match.group(1)

        # Title
        if not self.product_data["product_name"]:
            title_node = self.tree.css_first("#productTitle")
            if title_node:
                self.product_data["product_name"] = clean_text(title_node.text())

        # Price (Amazon has many price selectors)
        if not self.product_data["price"]:
            price_node = self.tree.css_first(".a-price .a-offscreen") or \
                         self.tree.css_first("#priceblock_ourprice") or \
                         self.tree.css_first("#priceblock_dealprice") or \
                         self.tree.css_first(".a-price-whole")
            if price_node:
                price_text = clean_text(price_node.text())
                # Clean up amazon price format e.g. "19." -> "19"
                if price_text.endswith('.'): price_text = price_text[:-1]
                self.product_data["price"] = price_text

        # Rating
        if not self.product_data["rating"]:
            rating_node = self.tree.css_first("#acrPopover") or self.tree.css_first(".a-icon-alt")
            if rating_node:
                self.product_data["rating"] = clean_text(rating_node.text()).split(' out of')[0]

        # Review Count
        if not self.product_data["review_count"]:
            review_node = self.tree.css_first("#acrCustomerReviewText")
            if review_node:
                self.product_data["review_count"] = clean_text(review_node.text()).split(' ')[0].replace(',', '')

        # Availability
        if not self.product_data["availability"]:
            avail_node = self.tree.css_first("#availability")
            if avail_node:
                self.product_data["availability"] = clean_text(avail_node.text())

        # Main Image
        if not self.product_data["main_image"]:
            img_node = self.tree.css_first("#landingImage") or self.tree.css_first("#imgBlkFront")
            if img_node:
                data_a_dynamic = img_node.attributes.get("data-a-dynamic-image")
                if data_a_dynamic:
                    try:
                        urls = json.loads(data_a_dynamic.replace('&quot;', '"'))
                        if urls:
                            self.product_data["main_image"] = list(urls.keys())[0]
                    except:
                        self.product_data["main_image"] = img_node.attributes.get("src", "")

    def _extract_general_heuristics(self):
        """Extract data using generic e-commerce class names for unknown stores."""
        
        # Generic Title
        if not self.product_data["product_name"]:
            title_node = self.tree.css_first("h1.product_title, h1.product-title, h1[itemprop='name']")
            if title_node:
                self.product_data["product_name"] = clean_text(title_node.text())

        # Generic Price
        if not self.product_data["price"]:
            price_node = self.tree.css_first(".price, .product-price, [itemprop='price']")
            if price_node:
                self.product_data["price"] = clean_text(price_node.text())

        # Generic SKU
        if not self.product_data["sku_asin"]:
            sku_node = self.tree.css_first(".sku, [itemprop='sku']")
            if sku_node:
                self.product_data["sku_asin"] = clean_text(sku_node.text())
                
        # Generic Image
        if not self.product_data["main_image"]:
            img_node = self.tree.css_first(".product-image img, .gallery img, [itemprop='image']")
            if img_node:
                self.product_data["main_image"] = img_node.attributes.get("src", "") or img_node.attributes.get("data-src", "")

    def extract(self):
        """Run all extraction heuristics and return the product data."""
        self._extract_from_json_ld()
        self._extract_amazon_heuristics()
        self._extract_general_heuristics()
        
        # Only return data if we found at least a name or a price
        if self.product_data["product_name"] or self.product_data["price"]:
            return self.product_data
        return None
