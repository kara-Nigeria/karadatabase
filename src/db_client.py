"""
Database client for interacting with PostgreSQL
"""

import psycopg2
import psycopg2.extras
from typing import Dict, Any, List, Optional, Tuple
from psycopg2.extensions import connection, cursor

from src.config import DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD
from src.schema import CREATE_SCHEMA_SQL, CLEANUP_SQL, CREATE_INDEXES_SQL, INIT_MIGRATION_PROGRESS_SQL
from utils.logger import get_logger

logger = get_logger(__name__)

class PostgresClient:
    def __init__(self):
        self.conn_params = {
            "host": DB_HOST,
            "port": DB_PORT,
            "dbname": DB_NAME,
            "user": DB_USER,
            "password": DB_PASSWORD
        }
        self.conn = None
        self.cursor = None
    
    def connect(self) -> bool:
        """Connect to the PostgreSQL database"""
        try:
            logger.info(f"Connecting to PostgreSQL database at {DB_HOST}:{DB_PORT}...")
            self.conn = psycopg2.connect(**self.conn_params)
            self.cursor = self.conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
            logger.info("Database connection successful")
            return True
        except Exception as e:
            logger.error(f"Database connection failed: {str(e)}")
            return False
    
    def disconnect(self):
        """Close the database connection"""
        if self.cursor:
            self.cursor.close()
        
        if self.conn:
            self.conn.close()
            logger.info("Database connection closed")
    
    def execute(self, query: str, params: tuple = None) -> bool:
        """Execute a SQL query"""
        try:
            self.cursor.execute(query, params)
            self.conn.commit()
            return True
        except Exception as e:
            self.conn.rollback()
            logger.error(f"Query execution failed: {str(e)}")
            logger.debug(f"Query: {query}")
            if params:
                logger.debug(f"Params: {params}")
            return False
    
    def fetch_one(self, query: str, params: tuple = None) -> Optional[Dict]:
        """Execute a query and fetch one result"""
        try:
            self.cursor.execute(query, params)
            return self.cursor.fetchone()
        except Exception as e:
            logger.error(f"Failed to fetch one: {str(e)}")
            return None
    
    def fetch_all(self, query: str, params: tuple = None) -> List[Dict]:
        """Execute a query and fetch all results"""
        try:
            self.cursor.execute(query, params)
            return self.cursor.fetchall()
        except Exception as e:
            logger.error(f"Failed to fetch all: {str(e)}")
            return []
    
    def initialize_schema(self, clean: bool = False) -> bool:
        """Initialize the database schema"""
        try:
            if clean:
                logger.warning("Cleaning up existing schema...")
                self.execute(CLEANUP_SQL)
            
            logger.info("Creating database schema...")
            self.execute(CREATE_SCHEMA_SQL)
            
            logger.info("Creating indexes...")
            self.execute(CREATE_INDEXES_SQL)
            
            logger.info("Initializing migration progress...")
            self.execute(INIT_MIGRATION_PROGRESS_SQL)
            
            logger.info("Schema initialization complete")
            return True
        except Exception as e:
            logger.error(f"Schema initialization failed: {str(e)}")
            return False
    
    def insert_category(self, category: Dict) -> Optional[int]:
        """Insert a category into the database"""
        query = """
        INSERT INTO imports.categories
        (original_id, parent_id, name, is_active, position, level, product_count)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (original_id) 
        DO UPDATE SET 
            parent_id = EXCLUDED.parent_id,
            name = EXCLUDED.name,
            is_active = EXCLUDED.is_active,
            position = EXCLUDED.position,
            level = EXCLUDED.level,
            product_count = EXCLUDED.product_count,
            updated_at = CURRENT_TIMESTAMP
        RETURNING id;
        """
        
        try:
            parent_id = category.get('parent_id')
            # If parent_id is 0 or None, set to NULL in database
            if parent_id == 0 or parent_id is None:
                parent_id = None
                
            params = (
                category['id'],
                parent_id,
                category['name'],
                category.get('is_active', True),
                category.get('position', 0),
                category.get('level', 1),
                category.get('product_count', 0)
            )
            
            self.cursor.execute(query, params)
            result = self.cursor.fetchone()
            self.conn.commit()
            
            if result and 'id' in result:
                return result['id']
            return None
            
        except Exception as e:
            self.conn.rollback()
            logger.error(f"Failed to insert category {category.get('name')}: {str(e)}")
            return None
    
    def insert_product(self, product: Dict) -> Optional[int]:
        """Insert a product into the database"""
        query = """
        INSERT INTO imports.products
        (original_id, sku, name, price, status, visibility, type, weight, created_at, updated_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (original_id) 
        DO UPDATE SET 
            sku = EXCLUDED.sku,
            name = EXCLUDED.name,
            price = EXCLUDED.price,
            status = EXCLUDED.status,
            visibility = EXCLUDED.visibility,
            type = EXCLUDED.type,
            weight = EXCLUDED.weight,
            created_at = EXCLUDED.created_at,
            updated_at = EXCLUDED.updated_at
        RETURNING id;
        """
        
        try:
            params = (
                product['id'],
                product['sku'],
                product['name'],
                product.get('price', 0),
                product.get('status', 1),
                product.get('visibility', 4),
                product.get('type_id', 'simple'),
                product.get('weight', 0),
                product.get('created_at'),
                product.get('updated_at')
            )
            
            self.cursor.execute(query, params)
            result = self.cursor.fetchone()
            self.conn.commit()
            
            if result and 'id' in result:
                return result['id']
            return None
            
        except Exception as e:
            self.conn.rollback()
            logger.error(f"Failed to insert product {product.get('sku')}: {str(e)}")
            return None
    
    def insert_product_categories(self, product_id: int, category_ids: List[int]) -> bool:
        """Insert product-category relationships"""
        if not category_ids:
            return True
            
        query = """
        INSERT INTO imports.product_categories
        (product_id, category_id, position)
        VALUES (%s, %s, %s)
        ON CONFLICT (product_id, category_id) 
        DO UPDATE SET position = EXCLUDED.position;
        """
        
        try:
            for position, category_id in enumerate(category_ids):
                self.cursor.execute(query, (product_id, category_id, position))
            
            self.conn.commit()
            return True
            
        except Exception as e:
            self.conn.rollback()
            logger.error(f"Failed to insert product categories for product {product_id}: {str(e)}")
            return False
    
    def insert_product_attributes(self, product_id: int, attributes: List[Dict]) -> bool:
        """Insert product attributes"""
        if not attributes:
            return True
            
        query = """
        INSERT INTO imports.product_attributes
        (product_id, attribute_code, value)
        VALUES (%s, %s, %s)
        ON CONFLICT (product_id, attribute_code) 
        DO UPDATE SET value = EXCLUDED.value;
        """
        
        try:
            for attr in attributes:
                if 'attribute_code' in attr and 'value' in attr:
                    self.cursor.execute(query, (
                        product_id, 
                        attr['attribute_code'], 
                        str(attr['value']) if attr['value'] is not None else None
                    ))
            
            self.conn.commit()
            return True
            
        except Exception as e:
            self.conn.rollback()
            logger.error(f"Failed to insert product attributes for product {product_id}: {str(e)}")
            return False
    
    def insert_product_media(self, product_id: int, media_entries: List[Dict]) -> bool:
        """Insert product media"""
        if not media_entries:
            return True
            
        query = """
        INSERT INTO imports.product_media
        (product_id, original_id, file_path, label, position, disabled, media_type)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (id) 
        DO UPDATE SET 
            file_path = EXCLUDED.file_path,
            label = EXCLUDED.label,
            position = EXCLUDED.position,
            disabled = EXCLUDED.disabled,
            media_type = EXCLUDED.media_type;
        """
        
        try:
            for media in media_entries:
                self.cursor.execute(query, (
                    product_id,
                    media.get('id'),
                    media.get('file'),
                    media.get('label'),
                    media.get('position', 0),
                    media.get('disabled', False),
                    media.get('media_type', 'image')
                ))
            
            self.conn.commit()
            return True
            
        except Exception as e:
            self.conn.rollback()
            logger.error(f"Failed to insert product media for product {product_id}: {str(e)}")
            return False
    
    def insert_product_inventory(self, product_id: int, inventory: Dict) -> bool:
        """Insert product inventory information"""
        query = """
        INSERT INTO imports.product_inventory
        (product_id, quantity, is_in_stock, manage_stock)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (product_id) 
        DO UPDATE SET 
            quantity = EXCLUDED.quantity,
            is_in_stock = EXCLUDED.is_in_stock,
            manage_stock = EXCLUDED.manage_stock;
        """
        
        try:
            self.cursor.execute(query, (
                product_id,
                inventory.get('qty', 0),
                inventory.get('is_in_stock', False),
                inventory.get('manage_stock', True)
            ))
            
            self.conn.commit()
            return True
            
        except Exception as e:
            self.conn.rollback()
            logger.error(f"Failed to insert product inventory for product {product_id}: {str(e)}")
            return False
    
    def get_category_id_mapping(self) -> Dict[int, int]:
        """Get mapping of original category IDs to database IDs"""
        query = "SELECT original_id, id FROM imports.categories"
        result = self.fetch_all(query)
        return {row['original_id']: row['id'] for row in result}
    
    def update_migration_progress(self, entity_type: str, status: str, 
                                total_count: int = None, processed_count: int = None, 
                                success_count: int = None, error_count: int = None,
                                last_processed_id: str = None, error_details: str = None) -> bool:
        """Update the migration progress"""
        query = """
        UPDATE imports.migration_progress
        SET
            status = %s,
            total_count = COALESCE(%s, total_count),
            processed_count = COALESCE(%s, processed_count),
            success_count = COALESCE(%s, success_count),
            error_count = COALESCE(%s, error_count),
            last_processed_id = COALESCE(%s, last_processed_id),
            error_details = COALESCE(%s, error_details),
            started_at = CASE WHEN %s = 'in_progress' AND started_at IS NULL THEN CURRENT_TIMESTAMP ELSE started_at END,
            completed_at = CASE WHEN %s IN ('completed', 'failed') THEN CURRENT_TIMESTAMP ELSE completed_at END
        WHERE entity_type = %s;
        """
        
        try:
            self.cursor.execute(query, (
                status,
                total_count,
                processed_count,
                success_count,
                error_count,
                last_processed_id,
                error_details,
                status,
                status,
                entity_type
            ))
            
            self.conn.commit()
            return True
            
        except Exception as e:
            self.conn.rollback()
            logger.error(f"Failed to update migration progress for {entity_type}: {str(e)}")
            return False
    
    def get_migration_progress(self, entity_type: str) -> Dict:
        """Get current migration progress"""
        query = """
        SELECT * FROM imports.migration_progress
        WHERE entity_type = %s;
        """
        
        result = self.fetch_one(query, (entity_type,))
        if result:
            return dict(result)
        return {}