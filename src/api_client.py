"""
API client for interacting with Kara's REST API
"""

import json
import time
import requests
from typing import Dict, Any, List, Optional, Tuple
from requests.exceptions import RequestException

from src.config import API_BASE_URL, API_USERNAME, API_PASSWORD, MAX_RETRIES, TIMEOUT
from utils.logger import get_logger

logger = get_logger(__name__)

class KaraApiClient:
    def __init__(self):
        self.base_url = API_BASE_URL
        self.username = API_USERNAME
        self.password = API_PASSWORD
        self.token = None
        self.session = requests.Session()
    
    def authenticate(self) -> bool:
        """Authenticate with the API and get a token"""
        url = f"{self.base_url}/integration/admin/token"
        payload = {
            "username": self.username,
            "password": self.password
        }
        
        try:
            logger.info("Authenticating with Kara API...")
            response = self.session.post(url, json=payload, timeout=TIMEOUT)
            response.raise_for_status()
            self.token = response.text.strip('"')
            self.session.headers.update({"Authorization": f"Bearer {self.token}"})
            logger.info("Authentication successful")
            return True
        except RequestException as e:
            logger.error(f"Authentication failed: {str(e)}")
            return False
    
    def _make_request(self, method: str, endpoint: str, params: Dict = None, data: Dict = None) -> Tuple[bool, Any]:
        """Make a request to the API with retries"""
        url = f"{self.base_url}/{endpoint}"
        
        for attempt in range(MAX_RETRIES):
            try:
                if not self.token:
                    self.authenticate()
                
                # Add a delay between requests to avoid overwhelming the API
                if attempt > 0:
                    delay = min(5 * attempt, 15)  # Progressive delay up to 15 seconds
                    logger.info(f"Waiting {delay} seconds before retry...")
                    time.sleep(delay)
                
                logger.debug(f"Making {method} request to {url}")
                
                # Use a longer timeout for potentially slow endpoints
                current_timeout = TIMEOUT * 2 if endpoint.startswith('products') else TIMEOUT
                
                response = self.session.request(
                    method=method,
                    url=url,
                    params=params,
                    json=data,
                    timeout=current_timeout
                )
                
                response.raise_for_status()
                return True, response.json()
            
            except RequestException as e:
                logger.warning(f"Request failed (attempt {attempt+1}/{MAX_RETRIES}): {str(e)}")
                if "401" in str(e) or "403" in str(e):
                    logger.info("Token may have expired, attempting to re-authenticate")
                    self.authenticate()
                
                if attempt == MAX_RETRIES - 1:
                    logger.error(f"Maximum retry attempts reached for {url}")
                    return False, None
                
                # Exponential backoff
                time.sleep(2 ** attempt)
        
        return False, None

    def get_categories(self) -> List[Dict]:
        """Fetch all categories from the API"""
        logger.info("Fetching categories...")
        success, response = self._make_request("GET", "categories")
        
        if success and response:
            logger.info(f"Successfully fetched categories")
            return response
        else:
            logger.error("Failed to fetch categories")
            return []
    
    def get_products(self, page: int = 1, page_size: int = 20, sort_field: str = "created_at", sort_direction: str = "DESC") -> Tuple[List[Dict], int]:
        """Fetch products with pagination"""
        # Use a smaller page size for better reliability
        effective_page_size = min(page_size, 10)
        
        params = {
            "searchCriteria[pageSize]": effective_page_size,
            "searchCriteria[currentPage]": page,
            "searchCriteria[sortOrders][0][field]": sort_field,
            "searchCriteria[sortOrders][0][direction]": sort_direction,
            # Only request essential fields to reduce response size
            "fields": "items[id,sku,name,price,status,visibility,type_id,weight,created_at,updated_at,extension_attributes[category_links,stock_item],custom_attributes,media_gallery_entries]"
        }
        
        logger.info(f"Fetching products (page {page}, size {effective_page_size})...")
        success, response = self._make_request("GET", "products", params=params)
        
        if success and response and "items" in response:
            total_count = response.get("total_count", 0)
            logger.info(f"Successfully fetched {len(response['items'])} products (total: {total_count})")
            return response["items"], total_count
        else:
            logger.error(f"Failed to fetch products for page {page}")
            return [], 0
    
    def get_product_details(self, sku: str) -> Optional[Dict]:
        """Fetch detailed information for a specific product"""
        logger.debug(f"Fetching detailed information for product {sku}...")
        
        # Add a small delay before fetching product details to avoid overwhelming the API
        time.sleep(0.5)
        
        success, response = self._make_request("GET", f"products/{sku}")
        
        if success and response:
            logger.debug(f"Successfully fetched details for product {sku}")
            return response
        else:
            logger.error(f"Failed to fetch details for product {sku}")
            return None