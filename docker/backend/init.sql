-- Kaasb Database Initialization
-- This runs when the PostgreSQL container is first created

-- Enable useful extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";  -- For fuzzy text search

-- Grant permissions
GRANT ALL PRIVILEGES ON DATABASE kaasb_db TO kaasb_user;
