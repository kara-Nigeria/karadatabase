"""
Main migration script to orchestrate the data migration from Kara to Medusa.js
"""

import sys
import time
import argparse
from typing import Dict, List, Tuple, Optional
import concurrent.futures
import requests
import os

from src.api_client import KaraApiClient
from src.db_client import PostgresClient
from src.transformer import (
    extract_all_categories, transform_product, extract_inventory_data,
    extract_category_ids, transform_media_entries, extract_custom_attributes
)
from src.config import BATCH_SIZE, MEDIA_STORAGE_PATH, DOWNLOAD_IMAGES
from utils.logger import get_logger
from utils.progress import ProgressBar, MigrationStatus, print_banner, print_step

# Create the logger
logger = get_logger(__name__)

# Create the migration status tracker
migration_status = MigrationStatus()

def migrate_categories(api_client: KaraApiClient, db_client: PostgresClient, clean: bool = False) -> bool:
    """Migrate categories from Kara to PostgreSQL"""
    print_step("CATEGORIES", "Migrating categories from Kara to PostgreSQL")
    
    # Update migration progress
    db_client.update_migration_progress('categories', 'in_progress')
    
    # Fetch categories from API
    categories_response = api_client.get_categories()
    
    if not categories_response:
        logger.error("Failed to fetch categories. Aborting categories migration.")
        db_client.update_migration_progress('categories', 'failed', error_details="Failed to fetch categories from API")
        return False
    
    # Extract all categories from the nested structure
    all_categories = extract_all_categories(categories_response)
    total_categories = len(all_categories)
    
    # Update total count in progress
    db_client.update_migration_progress('categories', 'in_progress', total_count=total_categories)
    
    logger.info(f"Found {total_categories} categories to migrate")
    
    # Create progress bar
    progress_bar = ProgressBar(total=total_categories, desc="Migrating Categories")
    
    # Counters for migration statistics
    success_count = 0
    error_count = 0
    
    # Process each category
    for category in all_categories:
        try:
            # Insert category into database
            category_id = db_client.insert_category(category)
            
            if category_id:
                success_count += 1
            else:
                error_count += 1
                logger.error(f"Failed to insert category: {category.get('name')}")
            
            # Update progress
            progress_bar.update()
            
            # Update migration progress periodically
            if (success_count + error_count) % 10 == 0 or (success_count + error_count) == total_categories:
                db_client.update_migration_progress(
                    'categories', 
                    'in_progress',
                    processed_count=success_count + error_count,
                    success_count=success_count,
                    error_count=error_count,
                    last_processed_id=str(category.get('id', ''))
                )
                
                # Update migration status
                migration_status.update_entity_progress(
                    'categories', 
                    db_client.get_migration_progress('categories')
                )
        
        except Exception as e:
            error_count += 1
            logger.error(f"Error processing category {category.get('name')}: {str(e)}")
    
    # Close progress bar
    progress_bar.close()
    
    # Update final migration progress
    status = 'completed' if error_count == 0 else 'completed_with_errors'
    db_client.update_migration_progress(
        'categories', 
        status,
        processed_count=success_count + error_count,
        success_count=success_count,
        error_count=error_count
    )
    
    # Update migration status
    migration_status.update_entity_progress(
        'categories', 
        db_client.get_migration_progress('categories')
    )
    
    logger.info(f"Categories migration completed: {success_count} succeeded, {error_count} failed")
    
    return error_count == 0

def migrate_products(api_client: KaraApiClient, db_client: PostgresClient, clean: bool = False) -> bool:
    """Migrate products from Kara to PostgreSQL"""
    print_step("PRODUCTS", "Migrating products from Kara to PostgreSQL")
    
    # Update migration progress
    db_client.update_migration_progress('products', 'in_progress')
    
    # Get category ID mapping
    category_id_mapping = db_client.get_category_id_mapping()
    logger.info(f"Found {len(category_id_mapping)} category mappings")
    
    # Fetch the first page to get total count - using a small page size for reliability
    products, total_count = api_client.get_products(page=1, page_size=1)
    
    if total_count == 0:
        # Try again with an even simpler request
        try:
            logger.info("Initial product request failed. Trying with a more basic request...")
            url = f"{api_client.base_url}/products"
            response = api_client.session.get(
                url, 
                params={"searchCriteria[pageSize]": 1},
                timeout=120  # Longer timeout
            )
            response.raise_for_status()
            data = response.json()
            total_count = data.get("total_count", 0)
            products = data.get("items", [])
            logger.info(f"Basic request successful. Found {total_count} products.")
        except Exception as e:
            logger.error(f"Basic product request also failed: {str(e)}")
            logger.error("No products found. Aborting products migration.")
            db_client.update_migration_progress('products', 'failed', error_details=f"No products found: {str(e)}")
            return False
    
    if total_count == 0:
        logger.error("No products found after multiple attempts. Aborting products migration.")
        db_client.update_migration_progress('products', 'failed', error_details="No products found")
        return False
    
    # Update total count in progress
    db_client.update_migration_progress('products', 'in_progress', total_count=total_count)
    
    logger.info(f"Found {total_count} products to migrate")
    
    # Calculate number of pages - use a small page size to avoid timeouts
    page_size = min(BATCH_SIZE, 5)  # Reduce page size for reliability
    num_pages = (total_count + page_size - 1) // page_size
    
    # Create progress bar
    progress_bar = ProgressBar(total=total_count, desc="Migrating Products")
    
    # Counters for migration statistics
    success_count = 0
    error_count = 0
    
    # Process each page
    for page in range(1, num_pages + 1):
        # Update progress bar description
        progress_bar.set_description(f"Migrating Products (Page {page}/{num_pages})")
        
        # Fetch products for the current page
        products, _ = api_client.get_products(page=page, page_size=page_size)
        
        if not products:
            logger.error(f"Failed to fetch products for page {page}. Skipping.")
            error_count += page_size  # Assume all products in the page failed
            progress_bar.update(page_size)
            
            # Add a longer delay after a failed page
            logger.info(f"Waiting 10 seconds before continuing...")
            time.sleep(10)
            continue
        
        # Process each product
        for product in products:
            try:
                # Get detailed product information
                product_details = api_client.get_product_details(product['sku'])
                
                if not product_details:
                    logger.error(f"Failed to fetch details for product {product['sku']}. Skipping.")
                    error_count += 1
                    progress_bar.update()
                    continue
                
                # Transform product data
                transformed_product = transform_product(product_details)
                
                # Insert product into database
                product_id = db_client.insert_product(transformed_product)
                
                if not product_id:
                    logger.error(f"Failed to insert product {product['sku']}. Skipping.")
                    error_count += 1
                    progress_bar.update()
                    continue
                
                # Extract additional data
                inventory = extract_inventory_data(product_details)
                category_ids = extract_category_ids(product_details)
                media_entries = transform_media_entries(product_details)
                custom_attributes = extract_custom_attributes(product_details)
                
                # Map original category IDs to database IDs
                mapped_category_ids = [
                    category_id_mapping.get(cat_id)
                    for cat_id in category_ids
                    if cat_id in category_id_mapping
                ]
                
                # Insert product inventory
                db_client.insert_product_inventory(product_id, inventory)
                
                # Insert product categories
                db_client.insert_product_categories(product_id, mapped_category_ids)
                
                # Insert product media
                db_client.insert_product_media(product_id, media_entries)
                
                # Insert product attributes
                db_client.insert_product_attributes(product_id, custom_attributes)
                
                success_count += 1
                
            except Exception as e:
                error_count += 1
                logger.error(f"Error processing product {product.get('sku')}: {str(e)}")
            
            # Update progress
            progress_bar.update()
            
            # Update migration progress periodically
            if (success_count + error_count) % 5 == 0 or (success_count + error_count) == total_count:
                db_client.update_migration_progress(
                    'products', 
                    'in_progress',
                    processed_count=success_count + error_count,
                    success_count=success_count,
                    error_count=error_count,
                    last_processed_id=product.get('sku', '')
                )
                
                # Update migration status
                migration_status.update_entity_progress(
                    'products', 
                    db_client.get_migration_progress('products')
                )
        
        # Add a small delay between pages to avoid overwhelming the API
        if page < num_pages:
            logger.info(f"Waiting a few seconds before fetching next page...")
            time.sleep(3)
    
    # Close progress bar
    progress_bar.close()
    
    # Update final migration progress
    status = 'completed' if error_count == 0 else 'completed_with_errors'
    db_client.update_migration_progress(
        'products', 
        status,
        processed_count=success_count + error_count,
        success_count=success_count,
        error_count=error_count
    )
    
    # Update migration status
    migration_status.update_entity_progress(
        'products', 
        db_client.get_migration_progress('products')
    )
    
    logger.info(f"Products migration completed: {success_count} succeeded, {error_count} failed")
    
    return error_count == 0

def download_product_images(db_client: PostgresClient) -> bool:
    """Download product images from Kara to local storage"""
    if not DOWNLOAD_IMAGES:
        logger.info("Image download is disabled. Skipping.")
        return True
    
    print_step("MEDIA", "Downloading product images")
    
    # Update migration progress
    db_client.update_migration_progress('media', 'in_progress')
    
    # Create media directory if it doesn't exist
    if not os.path.exists(MEDIA_STORAGE_PATH):
        os.makedirs(MEDIA_STORAGE_PATH)
    
    # Fetch all product media
    query = "SELECT id, product_id, file_path FROM imports.product_media WHERE file_path IS NOT NULL"
    media_entries = db_client.fetch_all(query)
    
    total_media = len(media_entries)
    
    # Update total count in progress
    db_client.update_migration_progress('media', 'in_progress', total_count=total_media)
    
    logger.info(f"Found {total_media} media entries to download")
    
    if total_media == 0:
        # No media to download
        db_client.update_migration_progress('media', 'completed', total_count=0, processed_count=0)
        return True
    
    # Create progress bar
    progress_bar = ProgressBar(total=total_media, desc="Downloading Media")
    
    # Counters for migration statistics
    success_count = 0
    error_count = 0
    
    # Base URL for media
    base_url = "https://kara.com.ng/pub/media/catalog/product"
    
    # Process each media entry
    for media in media_entries:
        try:
            file_path = media['file_path']
            
            # Skip if already starts with http
            if file_path.startswith(('http://', 'https://')):
                url = file_path
            else:
                # Remove leading slash if present
                if file_path.startswith('/'):
                    file_path = file_path[1:]
                
                url = f"{base_url}/{file_path}"
            
            # Create local path
            local_path = os.path.join(MEDIA_STORAGE_PATH, file_path)
            
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            
            # Download the file
            response = requests.get(url, stream=True, timeout=30)
            response.raise_for_status()
            
            # Save to local file
            with open(local_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            success_count += 1
            
        except Exception as e:
            error_count += 1
            logger.error(f"Error downloading media {media.get('file_path')}: {str(e)}")
        
        # Update progress
        progress_bar.update()
        
        # Update migration progress periodically
        if (success_count + error_count) % 10 == 0 or (success_count + error_count) == total_media:
            db_client.update_migration_progress(
                'media', 
                'in_progress',
                processed_count=success_count + error_count,
                success_count=success_count,
                error_count=error_count,
                last_processed_id=str(media.get('id', ''))
            )
            
            # Update migration status
            migration_status.update_entity_progress(
                'media', 
                db_client.get_migration_progress('media')
            )
    
    # Close progress bar
    progress_bar.close()
    
    # Update final migration progress
    status = 'completed' if error_count == 0 else 'completed_with_errors'
    db_client.update_migration_progress(
        'media', 
        status,
        processed_count=success_count + error_count,
        success_count=success_count,
        error_count=error_count
    )
    
    # Update migration status
    migration_status.update_entity_progress(
        'media', 
        db_client.get_migration_progress('media')
    )
    
    logger.info(f"Media download completed: {success_count} succeeded, {error_count} failed")
    
    return error_count == 0

def main():
    """Main function to run the migration"""
    parser = argparse.ArgumentParser(description='Migrate data from Kara to Medusa.js')
    parser.add_argument('--clean', action='store_true', help='Clean existing data before migration')
    parser.add_argument('--skip-categories', action='store_true', help='Skip categories migration')
    parser.add_argument('--skip-products', action='store_true', help='Skip products migration')
    parser.add_argument('--skip-media', action='store_true', help='Skip media download')
    
    args = parser.parse_args()
    
    # Print banner
    print_banner()
    
    # Create API client
    api_client = KaraApiClient()
    
    # Create database client
    db_client = PostgresClient()
    
    # Connect to database
    if not db_client.connect():
        logger.error("Failed to connect to database. Aborting migration.")
        return 1
    
    try:
        # Initialize database schema
        if not db_client.initialize_schema(clean=args.clean):
            logger.error("Failed to initialize database schema. Aborting migration.")
            return 1
        
        # Authenticate with API
        if not api_client.authenticate():
            logger.error("Failed to authenticate with API. Aborting migration.")
            return 1
        
        # Migrate categories
        if not args.skip_categories:
            migrate_categories(api_client, db_client, clean=args.clean)
        else:
            logger.info("Skipping categories migration")
            db_client.update_migration_progress('categories', 'skipped')
            migration_status.update_entity_progress(
                'categories', 
                db_client.get_migration_progress('categories')
            )
        
        # Migrate products
        if not args.skip_products:
            migrate_products(api_client, db_client, clean=args.clean)
        else:
            logger.info("Skipping products migration")
            db_client.update_migration_progress('products', 'skipped')
            migration_status.update_entity_progress(
                'products', 
                db_client.get_migration_progress('products')
            )
        
        # Download product images
        if not args.skip_media and DOWNLOAD_IMAGES:
            download_product_images(db_client)
        else:
            logger.info("Skipping media download")
            db_client.update_migration_progress('media', 'skipped')
            migration_status.update_entity_progress(
                'media', 
                db_client.get_migration_progress('media')
            )
        
        # Print summary
        migration_status.print_summary()
        
        return 0
    
    except Exception as e:
        logger.error(f"Migration failed: {str(e)}")
        return 1
    
    finally:
        # Disconnect from database
        db_client.disconnect()

if __name__ == "__main__":
    sys.exit(main())