"""
Database schema definitions for Medusa.js compatible tables
"""

# SQL statements to create the necessary tables for Medusa.js

CREATE_SCHEMA_SQL = """
-- Create custom schema for our imported data
CREATE SCHEMA IF NOT EXISTS imports;

-- Store categories in a hierarchical structure
CREATE TABLE IF NOT EXISTS imports.categories (
    id SERIAL PRIMARY KEY,
    original_id INTEGER NOT NULL,
    parent_id INTEGER,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    position INTEGER,
    level INTEGER,
    product_count INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(original_id)
);

-- Store products imported from Kara
CREATE TABLE IF NOT EXISTS imports.products (
    id SERIAL PRIMARY KEY,
    original_id INTEGER NOT NULL,
    sku VARCHAR(255) NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    price DECIMAL(10, 2),
    status SMALLINT,
    visibility SMALLINT,
    type VARCHAR(50),
    weight DECIMAL(10, 2),
    created_at TIMESTAMP WITH TIME ZONE,
    updated_at TIMESTAMP WITH TIME ZONE,
    UNIQUE(original_id),
    UNIQUE(sku)
);

-- Store product-category relationships
CREATE TABLE IF NOT EXISTS imports.product_categories (
    id SERIAL PRIMARY KEY,
    product_id INTEGER NOT NULL,
    category_id INTEGER NOT NULL,
    position INTEGER,
    UNIQUE(product_id, category_id),
    FOREIGN KEY (product_id) REFERENCES imports.products(id) ON DELETE CASCADE,
    FOREIGN KEY (category_id) REFERENCES imports.categories(id) ON DELETE CASCADE
);

-- Store product attributes/custom_attributes
CREATE TABLE IF NOT EXISTS imports.product_attributes (
    id SERIAL PRIMARY KEY,
    product_id INTEGER NOT NULL,
    attribute_code VARCHAR(255) NOT NULL,
    value TEXT,
    UNIQUE(product_id, attribute_code),
    FOREIGN KEY (product_id) REFERENCES imports.products(id) ON DELETE CASCADE
);

-- Store product images/media
CREATE TABLE IF NOT EXISTS imports.product_media (
    id SERIAL PRIMARY KEY,
    product_id INTEGER NOT NULL,
    original_id INTEGER,
    file_path VARCHAR(255) NOT NULL,
    label VARCHAR(255),
    position INTEGER,
    disabled BOOLEAN DEFAULT FALSE,
    media_type VARCHAR(50),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (product_id) REFERENCES imports.products(id) ON DELETE CASCADE
);

-- Store product inventory information
CREATE TABLE IF NOT EXISTS imports.product_inventory (
    id SERIAL PRIMARY KEY,
    product_id INTEGER NOT NULL,
    quantity INTEGER DEFAULT 0,
    is_in_stock BOOLEAN DEFAULT FALSE,
    manage_stock BOOLEAN DEFAULT TRUE,
    UNIQUE(product_id),
    FOREIGN KEY (product_id) REFERENCES imports.products(id) ON DELETE CASCADE
);

-- Store migration progress and status
CREATE TABLE IF NOT EXISTS imports.migration_progress (
    id SERIAL PRIMARY KEY,
    entity_type VARCHAR(50) NOT NULL,
    total_count INTEGER NOT NULL DEFAULT 0,
    processed_count INTEGER NOT NULL DEFAULT 0,
    success_count INTEGER NOT NULL DEFAULT 0,
    error_count INTEGER NOT NULL DEFAULT 0,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    last_processed_id VARCHAR(255),
    error_details TEXT
);
"""

# SQL statements to clean up tables (for rerunning migrations)
CLEANUP_SQL = """
DROP TABLE IF EXISTS imports.product_inventory CASCADE;
DROP TABLE IF EXISTS imports.product_media CASCADE;
DROP TABLE IF EXISTS imports.product_attributes CASCADE;
DROP TABLE IF EXISTS imports.product_categories CASCADE;
DROP TABLE IF EXISTS imports.products CASCADE;
DROP TABLE IF EXISTS imports.categories CASCADE;
DROP TABLE IF EXISTS imports.migration_progress CASCADE;
DROP SCHEMA IF EXISTS imports CASCADE;
"""

# Indexes for better query performance
CREATE_INDEXES_SQL = """
CREATE INDEX IF NOT EXISTS idx_categories_parent_id ON imports.categories(parent_id);
CREATE INDEX IF NOT EXISTS idx_categories_original_id ON imports.categories(original_id);
CREATE INDEX IF NOT EXISTS idx_products_sku ON imports.products(sku);
CREATE INDEX IF NOT EXISTS idx_products_original_id ON imports.products(original_id);
CREATE INDEX IF NOT EXISTS idx_product_attributes_code ON imports.product_attributes(attribute_code);
CREATE INDEX IF NOT EXISTS idx_product_media_product_id ON imports.product_media(product_id);
"""

# Initial setup for migration progress tracking
INIT_MIGRATION_PROGRESS_SQL = """
INSERT INTO imports.migration_progress (entity_type, status) 
VALUES ('categories', 'pending'), ('products', 'pending'), ('media', 'pending')
ON CONFLICT DO NOTHING;
"""