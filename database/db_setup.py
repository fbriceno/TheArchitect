"""
Database setup utilities for Confluence Documentation Generator
"""

import asyncio
import logging
import os
from pathlib import Path
from sqlalchemy import text
from .manager import DatabaseManager
from .models import Base

logger = logging.getLogger(__name__)

async def create_database_if_not_exists():
    """Create database if it doesn't exist"""
    try:
        # Connect to postgres database to create our target database
        db_host = os.getenv("POSTGRES_HOST", "localhost")
        db_port = os.getenv("POSTGRES_PORT", "5432")
        db_name = os.getenv("POSTGRES_DB", "confluence_docs")
        db_user = os.getenv("POSTGRES_USER", "postgres")
        db_password = os.getenv("POSTGRES_PASSWORD", "password")
        
        # First connect to postgres database
        postgres_url = f"postgresql+asyncpg://{db_user}:{db_password}@{db_host}:{db_port}/postgres"
        
        from sqlalchemy.ext.asyncio import create_async_engine
        engine = create_async_engine(postgres_url, isolation_level="AUTOCOMMIT")
        
        async with engine.connect() as conn:
            # Check if database exists
            result = await conn.execute(
                text("SELECT 1 FROM pg_database WHERE datname = :db_name"),
                {"db_name": db_name}
            )
            
            if not result.fetchone():
                # Create database
                await conn.execute(text(f"CREATE DATABASE {db_name}"))
                logger.info(f"Created database: {db_name}")
            else:
                logger.info(f"Database {db_name} already exists")
        
        await engine.dispose()
        
    except Exception as e:
        logger.error(f"Failed to create database: {e}")
        raise

async def setup_database():
    """Setup database with all tables and initial data"""
    try:
        # Create database if needed
        await create_database_if_not_exists()
        
        # Initialize database manager
        db_manager = DatabaseManager()
        await db_manager.initialize()
        
        logger.info("Database setup completed successfully")
        
        await db_manager.close()
        
    except Exception as e:
        logger.error(f"Database setup failed: {e}")
        raise

async def run_sql_scripts():
    """Run SQL initialization scripts"""
    try:
        db_manager = DatabaseManager()
        await db_manager.initialize()
        
        # Get script directory
        script_dir = Path(__file__).parent.parent.parent / "database" / "init"
        
        if not script_dir.exists():
            logger.warning(f"SQL script directory not found: {script_dir}")
            return
        
        # Get all SQL files in order
        sql_files = sorted(script_dir.glob("*.sql"))
        
        async with db_manager.async_session_maker() as session:
            for sql_file in sql_files:
                logger.info(f"Executing SQL script: {sql_file.name}")
                
                try:
                    with open(sql_file, 'r') as f:
                        sql_content = f.read()
                    
                    # Split by statements (simple split on ;\n)
                    statements = [stmt.strip() for stmt in sql_content.split(';\n') if stmt.strip()]
                    
                    for statement in statements:
                        if statement:
                            await session.execute(text(statement))
                    
                    await session.commit()
                    logger.info(f"Successfully executed: {sql_file.name}")
                    
                except Exception as e:
                    await session.rollback()
                    logger.error(f"Failed to execute {sql_file.name}: {e}")
                    # Continue with other scripts
        
        await db_manager.close()
        logger.info("SQL scripts execution completed")
        
    except Exception as e:
        logger.error(f"Failed to run SQL scripts: {e}")
        raise

def check_database_connection():
    """Check if database connection is working"""
    import asyncio
    
    async def _check():
        try:
            db_manager = DatabaseManager()
            await db_manager.initialize()
            
            # Try a simple query
            async with db_manager.async_session_maker() as session:
                result = await session.execute(text("SELECT 1"))
                row = result.fetchone()
                if row and row[0] == 1:
                    logger.info("Database connection successful")
                    return True
                else:
                    logger.error("Database connection test failed")
                    return False
                    
        except Exception as e:
            logger.error(f"Database connection failed: {e}")
            return False
        finally:
            if db_manager:
                await db_manager.close()
    
    return asyncio.run(_check())

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    import sys
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "setup":
            asyncio.run(setup_database())
        elif command == "scripts":
            asyncio.run(run_sql_scripts())
        elif command == "check":
            success = check_database_connection()
            sys.exit(0 if success else 1)
        else:
            print("Usage: python db_setup.py [setup|scripts|check]")
            sys.exit(1)
    else:
        # Default: full setup
        asyncio.run(setup_database())
        asyncio.run(run_sql_scripts())