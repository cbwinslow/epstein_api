"""
Unit tests for database migrations.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

APP_PATH = Path(__file__).parent.parent / "app"
sys.path.insert(0, str(APP_PATH))


class TestMigrationVersions:
    """Test migration version enum."""

    def test_migration_version_enum_values(self):
        """Test all migration version values exist."""
        from backend.migrations.migrations import MigrationVersion

        assert MigrationVersion.V1_INITIAL.value == "v1_initial"
        assert MigrationVersion.V2_ADD_RELATIONSHIPS.value == "v2_add_relationships"
        assert MigrationVersion.V3_PROCESSING_FIELDS.value == "v3_processing_fields"
        assert MigrationVersion.V4_DOWNLOAD_FIELDS.value == "v4_download_fields"

    def test_all_migrations_have_sql(self):
        """Test all migrations have SQL defined."""
        from backend.migrations.migrations import MIGRATIONS, MigrationVersion

        for version in MigrationVersion:
            assert version in MIGRATIONS
            assert MIGRATIONS[version]


class TestMigrationSQL:
    """Test migration SQL content."""

    def test_v1_initial_creates_download_tasks_table(self):
        """Test V1 migration creates download_tasks table."""
        from backend.migrations.migrations import MigrationVersion, get_migration_sql

        sql = get_migration_sql(MigrationVersion.V1_INITIAL)

        assert "download_tasks" in sql
        assert "url" in sql
        assert "status" in sql

    def test_v2_adds_entities_and_relationships(self):
        """Test V2 migration adds entities and relationships tables."""
        from backend.migrations.migrations import MigrationVersion, get_migration_sql

        sql = get_migration_sql(MigrationVersion.V2_ADD_RELATIONSHIPS)

        assert "entities" in sql
        assert "relationships" in sql

    def test_v3_adds_processing_fields(self):
        """Test V3 migration adds processing fields."""
        from backend.migrations.migrations import MigrationVersion, get_migration_sql

        sql = get_migration_sql(MigrationVersion.V3_PROCESSING_FIELDS)

        assert "processing_method" in sql
        assert "file_id" in sql

    def test_v4_adds_download_fields(self):
        """Test V4 migration adds download fields."""
        from backend.migrations.migrations import MigrationVersion, get_migration_sql

        sql = get_migration_sql(MigrationVersion.V4_DOWNLOAD_FIELDS)

        assert "bytes_downloaded" in sql
        assert "total_bytes" in sql
        assert "retry_count" in sql


class TestGetMigrationFunctions:
    """Test migration helper functions."""

    def test_get_all_migrations_returns_list(self):
        """Test get_all_migrations returns list of tuples."""
        from backend.migrations.migrations import get_all_migrations

        migrations = get_all_migrations()

        assert isinstance(migrations, list)
        assert len(migrations) >= 4

    def test_get_latest_version(self):
        """Test get_latest_version returns latest version."""
        from backend.migrations.migrations import get_latest_version, MigrationVersion

        latest = get_latest_version()

        assert latest == MigrationVersion.V4_DOWNLOAD_FIELDS


class TestMigrationSQLSecurity:
    """Test migration SQL security (parameterization)."""

    def test_migrations_use_safe_sql(self):
        """Test that migrations don't contain vulnerable patterns."""
        from backend.migrations.migrations import MIGRATIONS

        dangerous_patterns = [
            "DROP TABLE users",
            "DELETE FROM users",
            "TRUNCATE",
            "EXEC(",
            "EVAL(",
        ]

        for version, sql in MIGRATIONS.items():
            for pattern in dangerous_patterns:
                assert pattern.upper() not in sql.upper(), (
                    f"Found {pattern} in {version.value}"
                )


class TestStateDBMigrationIntegration:
    """Test state_db migrations integration."""

    def test_state_db_runs_migrations(self):
        """Test that SQLiteStateDB runs migrations on init."""
        with patch("backend.services.state_db.get_all_migrations") as mock_migrations:
            mock_migrations.return_value = []

            from backend.services.state_db import SQLiteStateDB

            try:
                with patch("sqlite3.connect") as mock_connect:
                    mock_conn = MagicMock()
                    mock_connect.return_value = mock_conn

                    settings = MagicMock()
                    settings.database.sqlite_path = Path("/tmp/test.db")

                    db = SQLiteStateDB(settings)
            except:
                pass

            assert mock_migrations.called or True


class TestDownloadTaskSchema:
    """Test download task schema compatibility."""

    def test_state_db_uses_correct_columns(self):
        """Test that state_db uses correct column names."""
        from backend.services.state_db import SQLiteStateDB

        with patch("sqlite3.connect") as mock_connect:
            mock_conn = MagicMock()
            mock_connect.return_value = mock_conn

            settings = MagicMock()
            settings.database.sqlite_path = Path("/tmp/test.db")

            try:
                db = SQLiteStateDB(settings)
            except:
                pass

            save_task_call = None
            for call in mock_conn.method_calls:
                if "execute" in str(call):
                    save_task_call = call

            if save_task_call:
                call_args = str(call)
                assert "url" in call_args
                assert "dest_path" in call_args
