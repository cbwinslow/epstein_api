"""
Database migrations module.
All SQL statements must be defined here and imported by services.
Never write raw SQL in service functions.
"""

from enum import Enum


class MigrationVersion(Enum):
    V1_INITIAL = "v1_initial"
    V2_ADD_RELATIONSHIPS = "v2_add_relationships"
    V3_PROCESSING_FIELDS = "v3_processing_fields"


MIGRATIONS: dict[MigrationVersion, str] = {
    MigrationVersion.V1_INITIAL: """
        CREATE TABLE IF NOT EXISTS download_tasks (
            url TEXT PRIMARY KEY,
            dest_path TEXT NOT NULL,
            status TEXT NOT NULL,
            retries INTEGER DEFAULT 0,
            error_message TEXT,
            sha256_hash TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        CREATE INDEX IF NOT EXISTS idx_download_tasks_status 
        ON download_tasks(status);
        
        CREATE INDEX IF NOT EXISTS idx_download_tasks_hash 
        ON download_tasks(sha256_hash);
    """,
    MigrationVersion.V2_ADD_RELATIONSHIPS: """
        CREATE TABLE IF NOT EXISTS entities (
            id TEXT PRIMARY KEY,
            entity_type TEXT NOT NULL,
            name TEXT NOT NULL,
            properties TEXT,
            source_file TEXT,
            confidence TEXT DEFAULT 'medium',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        CREATE INDEX IF NOT EXISTS idx_entities_type ON entities(entity_type);
        CREATE INDEX IF NOT EXISTS idx_entities_name ON entities(name);
        CREATE INDEX IF NOT EXISTS idx_entities_source ON entities(source_file);
        
        CREATE TABLE IF NOT EXISTS relationships (
            id TEXT PRIMARY KEY,
            from_entity_id TEXT NOT NULL,
            to_entity_id TEXT NOT NULL,
            relationship_type TEXT NOT NULL,
            score INTEGER DEFAULT 1,
            evidence TEXT,
            source_files TEXT,
            first_seen DATE,
            last_seen DATE,
            confidence TEXT DEFAULT 'medium',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (from_entity_id) REFERENCES entities(id),
            FOREIGN KEY (to_entity_id) REFERENCES entities(id)
        );
        
        CREATE INDEX IF NOT EXISTS idx_relationships_from ON relationships(from_entity_id);
        CREATE INDEX IF NOT EXISTS idx_relationships_to ON relationships(to_entity_id);
        CREATE INDEX IF NOT EXISTS idx_relationships_type ON relationships(relationship_type);
    """,
    MigrationVersion.V3_PROCESSING_FIELDS: """
        ALTER TABLE download_tasks ADD COLUMN processing_method TEXT;
        ALTER TABLE download_tasks ADD COLUMN file_id INTEGER;
        CREATE INDEX IF NOT EXISTS idx_download_tasks_id ON download_tasks(file_id);
    """,
}


def get_migration_sql(version: MigrationVersion) -> str:
    """Get SQL for a specific migration version."""
    return MIGRATIONS.get(version, "")


def get_all_migrations() -> list[tuple[MigrationVersion, str]]:
    """Get all migrations in order."""
    return [(k, v) for k, v in MIGRATIONS.items()]


def get_latest_version() -> MigrationVersion:
    """Get the latest migration version."""
    return list(MigrationVersion)[-1]
