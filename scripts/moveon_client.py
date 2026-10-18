import re
import urllib.request
import urllib.error
import json
import uuid
from typing import Dict, List, Any, Optional

def extract_product_id_from_url(url_or_id: str) -> str:
    """
    Extracts the internal MoveOn composite product ID from a MoveOn URL or raw ID.
    MoveOn product URLs follow the pattern:
    https://moveon.global/BD_en/products/{part1}-{slug}/{part2}
    MoveOn internal API expects: {part2}{part1}
    """
    url_or_id = url_or_id.strip()
    
    # Check if URL matches the MoveOn product structure
    match = re.search(r'/products/([A-Za-z0-9]+)[^/]*/([A-Za-z0-9]+)', url_or_id)
    if match:
        part1 = match.group(1)
        part2 = match.group(2)
        return f"{part2}{part1}"
    
    # If the user passed raw ID or direct query
    # Check if it's already a composite or single alphanumeric ID
    clean_id = re.sub(r'[^A-Za-z0-9]', '', url_or_id)
    return clean_id

def clean_model_name(name: str) -> str:
    """Cleans phone model string, removing Chinese brackets or spec notes like 【1 case】."""
    name = re.sub(r'【[^】]*】', '', name)
    name = re.sub(r'\[[^\]]*\]', '', name)
    name = re.sub(r'\(1\s*case\)', '', name, flags=re.IGNORECASE)
    name = re.sub(r'\brealme\b', 'Realme', name, flags=re.IGNORECASE)
    name = re.sub(r'\bneo\s*(\d+)\b', r'Neo\1', name, flags=re.IGNORECASE)
    name = re.sub(r'[\\/:*?"<>|]', '_', name)  # Windows-safe filename characters
    return name.strip()

def sanitize_filename(name: str) -> str:
    """Sanitizes a string to be safely used as a filename."""
    name = re.sub(r'[\\/:*?"<>|]', '_', name)
    name = re.sub(r'\s+', ' ', name)
    return name.strip()

class MoveOnClient:
    BASE_API = "https://product-api.proxy.service.moveon.global/api/product/customer/v1/products/find"

    def __init__(self, region: str = "BD", locale: str = "en", business_type: str = "wholesale"):
        self.region = region
        self.locale = locale
        self.business_type = business_type
        self.guest_id = str(uuid.uuid4())

    def fetch_product(self, url_or_id: str) -> Dict[str, Any]:
        """
        Fetches the product details for the single specified product.
        Strictly does NOT crawl or scan any external or related links.
        """
        product_id = extract_product_id_from_url(url_or_id)
        if not product_id:
            raise ValueError(f"Could not extract a valid MoveOn product ID from: {url_or_id}")

        api_url = f"{self.BASE_API}/{product_id}?region={self.region}&locale={self.locale}&business_type={self.business_type}"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Origin': 'https://moveon.global',
            'Referer': 'https://moveon.global/',
            'X-GUEST-ID': self.guest_id,
            'X-GUEST-SESSION': self.guest_id
        }

        req = urllib.request.Request(api_url, headers=headers)
        try:
            with urllib.request.urlopen(req) as resp:
                raw_json = json.loads(resp.read().decode('utf-8'))
        except urllib.error.HTTPError as e:
            error_body = e.read().decode('utf-8', 'ignore')
            raise RuntimeError(f"MoveOn API error (HTTP {e.code}): {error_body}") from e
        except Exception as e:
            raise RuntimeError(f"Network error communicating with MoveOn API: {e}") from e

        data = raw_json.get('data', {})
        if not data:
            raise ValueError("No product data returned by MoveOn API.")

        title = data.get('title', 'Untitled Phone Cover')
        main_image = data.get('image')
        
        # Parse Gallery Images
        gallery_raw = data.get('gallery', {})
        gallery_items = []
        if isinstance(gallery_raw, dict):
            gallery_items = gallery_raw.get('data', [])
        elif isinstance(gallery_raw, list):
            gallery_items = gallery_raw

        gallery_urls = []
        for g in gallery_items:
            if isinstance(g, dict) and g.get('url'):
                gallery_urls.append(g.get('url'))
            elif isinstance(g, str):
                gallery_urls.append(g)
        
        # If gallery is empty but main image exists, add main image
        if not gallery_urls and main_image:
            gallery_urls.append(main_image)

        # Parse properties and models
        props_data = data.get('variation', {}).get('properties', {}).get('data', [])
        models_list: List[Dict[str, str]] = []
        prop_values_map = {}  # value_id -> {'name': name, 'image': img, 'prop_id': prop_id}

        model_property_id = None
        for prop in props_data:
            prop_name = prop.get('name', '').strip()
            prop_id = str(prop.get('id', ''))
            is_model_prop = any(k in prop_name.lower() for k in ['model', 'applicable', 'device'])
            if is_model_prop:
                model_property_id = prop_id

            for val in prop.get('values', {}).get('data', []):
                val_id = str(val.get('id', ''))
                val_name = val.get('name', '').strip()
                val_img = val.get('image')
                prop_values_map[val_id] = {
                    'name': val_name,
                    'image': val_img,
                    'prop_id': prop_id,
                    'prop_name': prop_name
                }
                if is_model_prop:
                    models_list.append({
                        'id': val_id,
                        'raw_name': val_name,
                        'clean_name': clean_model_name(val_name)
                    })

        # If no explicit model property found, check title for model name
        if not models_list:
            models_list.append({
                'id': 'default',
                'raw_name': title,
                'clean_name': clean_model_name(title)
            })

        # Parse SKUs mapped by model
        skus_data = data.get('variation', {}).get('skus', {}).get('data', [])
        skus_by_model: Dict[str, List[Dict[str, Any]]] = {}

        for sku in skus_data:
            sku_id = str(sku.get('id', ''))
            sku_image = sku.get('image') or main_image
            price_info = sku.get('price', {})
            
            # Find associated properties
            associations = sku.get('property_associations', {}).get('data', [])
            associated_model_clean = None
            variant_names = []

            for assoc in associations:
                val_id = str(assoc.get('property_value_id', ''))
                val_meta = prop_values_map.get(val_id)
                if val_meta:
                    if val_meta['prop_id'] == model_property_id:
                        associated_model_clean = clean_model_name(val_meta['name'])
                    else:
                        variant_names.append(val_meta['name'])

            if not associated_model_clean:
                # Associate with default model if single model
                associated_model_clean = models_list[0]['clean_name'] if models_list else "Standard Model"

            sku_item = {
                'id': sku_id,
                'image': sku_image,
                'variant_label': " - ".join(variant_names) if variant_names else f"SKU {sku_id}",
                'price': price_info
            }

            if associated_model_clean not in skus_by_model:
                skus_by_model[associated_model_clean] = []
            skus_by_model[associated_model_clean].append(sku_item)

        return {
            'product_id': product_id,
            'title': title,
            'main_image': main_image,
            'gallery_images': gallery_urls,
            'models': models_list,
            'properties': props_data,
            'skus_by_model': skus_by_model,
            'raw_data': data
        }
