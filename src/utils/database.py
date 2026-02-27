# src/utils/database.py
"""Database utilities for PostgreSQL connection and DDInter data loading."""

import os
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

import asyncpg
import pandas as pd

from ..utils.logging import logger


async def get_db_pool():
    """Create PostgreSQL connection pool.

    Strips sslmode from the URL and passes ssl='require' directly,
    as asyncpg does not support all sslmode values used by cloud providers.
    """
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise ValueError("DATABASE_URL environment variable not set")

    parsed = urlparse(database_url)
    params = parse_qs(parsed.query, keep_blank_values=True)
    params.pop("sslmode", None)
    clean_url = urlunparse(parsed._replace(query=urlencode(params, doseq=True)))

    return await asyncpg.create_pool(clean_url, ssl="require")


async def init_failed_lookups_table(pool):
    """Create failed_drug_lookups table if it does not exist."""
    async with pool.acquire() as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS failed_drug_lookups (
                id SERIAL PRIMARY KEY,
                drugs TEXT[] NOT NULL,
                source VARCHAR(50) NOT NULL,
                failed_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            );
        """)
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_failed_lookups_source
            ON failed_drug_lookups(source);
        """)
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_failed_lookups_failed_at
            ON failed_drug_lookups(failed_at DESC);
        """)
    logger.info("failed_drug_lookups table and indexes ensured")


async def init_ddinter_table(pool):
    """Create DDInter table with constraints and indexes."""
    async with pool.acquire() as conn:
        async with conn.transaction():
            # Create severity enum
            await conn.execute("""
                DO $$ BEGIN
                    CREATE TYPE severity_level AS ENUM ('Minor', 'Moderate', 'Major', 'Unknown');
                EXCEPTION
                    WHEN duplicate_object THEN null;
                END $$;
            """)

            # Create table for processed data
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS ddinter (
                    id SERIAL PRIMARY KEY,
                    ddinter_id_a TEXT NOT NULL CHECK (ddinter_id_a <> '' AND length(ddinter_id_a) <= 50),
                    ddinter_id_b TEXT NOT NULL CHECK (ddinter_id_b <> '' AND length(ddinter_id_b) <= 50),
                    drug_a VARCHAR(255) NOT NULL CHECK (drug_a <> ''),
                    drug_b VARCHAR(255) NOT NULL CHECK (drug_b <> ''),
                    severity severity_level NOT NULL,
                    categories TEXT NOT NULL CHECK (categories <> ''),
                    UNIQUE(ddinter_id_a, ddinter_id_b)
                );
            """)

            # Create indexes for fast lookups
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_ddinter_ids
                ON ddinter(ddinter_id_a, ddinter_id_b);
            """)

            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_ddinter_drugs_lower
                ON ddinter(lower(drug_a), lower(drug_b));
            """)

            # Enable Row Level Security
            await conn.execute("""
                ALTER TABLE ddinter ENABLE ROW LEVEL SECURITY;
            """)

            # Public read access policy
            await conn.execute("""
                DROP POLICY IF EXISTS "Public read access" ON ddinter;
                CREATE POLICY "Public read access" ON ddinter
                    FOR SELECT USING (true);
            """)

        logger.info("DDInter table, RLS policies, and indexes created")


async def load_ddinter_csv(pool, csv_path: str):
    """Load processed DDInter CSV data into PostgreSQL using COPY for performance."""
    csv_file = Path(csv_path)
    if not csv_file.exists():
        raise FileNotFoundError(f"DDInter CSV not found: {csv_path}")

    # Read processed CSV (no validation needed - data already cleaned)
    df = pd.read_csv(csv_path)
    logger.info(f"Loading {len(df)} processed DDInter records from {csv_path}")

    # Convert to records for COPY
    records = [
        (
            row.ddinter_id_a,
            row.ddinter_id_b,
            row.drug_a,
            row.drug_b,
            row.severity,
            row.categories,
        )
        for row in df.itertuples(index=False)
    ]

    async with pool.acquire() as conn:
        async with conn.transaction():
            # Clear existing data
            await conn.execute("TRUNCATE TABLE ddinter RESTART IDENTITY")

            # Bulk insert using COPY
            await conn.copy_records_to_table(
                "ddinter",
                records=records,
                columns=[
                    "ddinter_id_a",
                    "ddinter_id_b",
                    "drug_a",
                    "drug_b",
                    "severity",
                    "categories",
                ],
            )

        logger.info(f"Loaded {len(records)} DDInter records")


async def setup_database(csv_path: str = "./data/ddinter_pg.csv") -> dict:
    """Initialize database and load DDInter data. Returns connection info."""
    pool = await get_db_pool()
    try:
        await init_ddinter_table(pool)
        await init_failed_lookups_table(pool)
        await load_ddinter_csv(pool, csv_path)
        logger.info("Database setup complete with RLS enabled")

        # Return connection info instead of live pool
        database_url = os.getenv("DATABASE_URL")
        return {"database_url": database_url, "status": "ready"}
    finally:
        await pool.close()
