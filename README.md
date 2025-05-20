Kara to Medusa.js Migration Tool
This tool migrates products and categories from Kara's e-commerce platform to a PostgreSQL database compatible with Medusa.js.
Features

Migrates categories with hierarchical structure
Migrates products with their attributes, inventory, and media
Downloads product images to local storage
Runs in Docker containers with persistent storage
Visual progress indicators and detailed logging

Prerequisites

Docker
Docker Compose
Internet connection to access Kara's API

Setup

Clone this repository:
git clone https://github.com/yourusername/kara-medusa-migration.git
cd kara-medusa-migration

(Optional) Create a .env file in the project root to customize the configuration:
KARA_API_USERNAME=elevated
KARA_API_PASSWORD=nynwEd-7bucpe-rysdim
BATCH_SIZE=50
DOWNLOAD_IMAGES=True
LOG_LEVEL=INFO

Make sure the entrypoint script is executable:
chmod +x entrypoint.sh


Running the Migration
To run the full migration:
bashdocker-compose up --build
This will:

Build and start the necessary containers
Create the database schema
Migrate categories from Kara
Migrate products from Kara
Download product images (if enabled)

Additional Options
You can pass additional arguments to the migrator:
bashdocker-compose run migrator python -m src.migrator --clean
Available options:

--clean: Clean existing data before migration
--skip-categories: Skip categories migration
--skip-products: Skip products migration
--skip-media: Skip media download

Directory Structure
kara-medusa-migration/
├── src/                   # Source code
│   ├── api_client.py      # API interaction functions
│   ├── config.py          # Configuration settings
│   ├── db_client.py       # Database interaction functions
│   ├── migrator.py        # Main migration script
│   ├── schema.py          # Database schema definitions
│   └── transformer.py     # Data transformation functions
├── utils/                 # Utility functions
│   ├── logger.py          # Logging configuration
│   └── progress.py        # Progress visualization utilities
├── logs/                  # Log files (created by the migrator)
├── media/                 # Downloaded media files (created by the migrator)
├── Dockerfile             # Docker configuration for migration app
├── docker-compose.yml     # Services configuration
├── entrypoint.sh          # Container entrypoint script
├── requirements.txt       # Python dependencies
└── README.md              # This file
Persistent Storage
The migration tool uses Docker volumes to provide persistent storage:

postgres_data: Stores the PostgreSQL database data
./logs: Stores log files from the migration process
./media: Stores downloaded product images

Troubleshooting
If you encounter issues:

Check the logs in the logs directory
Ensure the API credentials are correct
Verify that PostgreSQL is running and accessible
Try running with the --clean option to reset the database

License
MIT