"""
Data transformation functions to convert Kara data to Medusa.js compatible format
"""

from typing import Dict, Any, List, Optional, Tuple
import json

from utils.logger import get_logger

logger = get_logger(__name__)

def transform_category(category: Dict) -> Dict:
    """Transform a category from Kara format to Medusa.js compatible format"""
    return {
        'id': category.get('id'),
        'parent_id': category.get('parent_id'),
        'name': category.get('name'),
        'is_active': category.get('is_active', True),
        'position': category.get('position', 0),
        'level': category.get('level', 1),
        'product_count': category.get('product_count', 0)
    }

def transform_product(product: Dict) -> Dict:
    """Transform a product from Kara format to Medusa.js compatible format"""
    transformed = {
        'id': product.get('id'),
        'sku': product.get('sku'),
        'name': product.get('name'),
        'price': product.get('price', 0),
        'status': product.get('status', 1),
        'visibility': product.get('visibility', 4),
        'type_id': product.get('type_id', 'simple'),
        'weight': product.get('weight', 0),
        'created_at': product.get('created_at'),
        'updated_at': product.get('updated_at'),
    }
    
    return transformed

def extract_inventory_data(product: Dict) -> Dict:
    """Extract inventory data from a product"""
    stock_item = {}
    
    # Check if stock_item is in extension_attributes
    if 'extension_attributes' in product and 'stock_item' in product['extension_attributes']:
        stock_item = product['extension_attributes']['stock_item']
    
    return {
        'qty': stock_item.get('qty', 0),
        'is_in_stock': stock_item.get('is_in_stock', False),
        'manage_stock': stock_item.get('manage_stock', True)
    }

def extract_category_ids(product: Dict) -> List[int]:
    """Extract category IDs from a product"""
    category_ids = []
    
    # Check if category_links is in extension_attributes
    if 'extension_attributes' in product and 'category_links' in product['extension_attributes']:
        category_ids = [
            int(link['category_id']) 
            for link in product['extension_attributes']['category_links']
            if 'category_id' in link
        ]
    
    # Also check if category_ids is in custom_attributes
    elif 'custom_attributes' in product:
        for attr in product['custom_attributes']:
            if attr.get('attribute_code') == 'category_ids' and isinstance(attr.get('value'), list):
                category_ids = [int(cat_id) for cat_id in attr['value']]
                break
    
    return category_ids

def transform_media_entries(product: Dict) -> List[Dict]:
    """Transform media entries from a product"""
    media_entries = []
    
    if 'media_gallery_entries' in product:
        for entry in product['media_gallery_entries']:
            media_entries.append({
                'id': entry.get('id'),
                'file': entry.get('file'),
                'label': entry.get('label'),
                'position': entry.get('position', 0),
                'disabled': entry.get('disabled', False),
                'media_type': entry.get('media_type', 'image')
            })
    
    return media_entries

def extract_custom_attributes(product: Dict) -> List[Dict]:
    """Extract custom attributes from a product"""
    if 'custom_attributes' in product:
        return product['custom_attributes']
    return []

def extract_all_categories(category: Dict, categories_list: List = None) -> List[Dict]:
    """Recursively extract all categories from a nested category structure"""
    if categories_list is None:
        categories_list = []
    
    # Add the current category
    categories_list.append(transform_category(category))
    
    # Process children categories recursively
    if 'children_data' in category and category['children_data']:
        for child in category['children_data']:
            extract_all_categories(child, categories_list)
    
    return categories_list