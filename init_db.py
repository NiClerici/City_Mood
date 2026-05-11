#!/usr/bin/env python3
"""
Initialize City_Mood database from SQL scripts.
Reads .env for database credentials.
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
import mysql.connector
from mysql.connector import Error

# Load environment variables from .env
load_dotenv()

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "127.0.0.1"),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", "?1234"),
    "port": int(os.getenv("DB_PORT", 3306)),
}

SQL_FILES = [
    "init-metabase.sql",
    "init.sql",
    "calculate_mood_scores.sql",
    "mv_daily_mood.sql",
]

def execute_sql_file(connection, filepath, database=None):
    """Execute SQL file against connection."""
    cursor = connection.cursor()
    try:
        with open(filepath, 'r') as f:
            sql_content = f.read()
        
        # Select database if specified
        if database:
            cursor.execute(f"USE {database}")
        
        # Handle files with DELIMITER
        if 'DELIMITER' in sql_content:
            # Parse sections delimited by DELIMITER statements
            lines = sql_content.split('\n')
            current_delimiter = ';'
            statement_lines = []
            
            for line in lines:
                if line.strip().startswith('DELIMITER'):
                    # Flush current statement
                    if statement_lines:
                        stmt = '\n'.join(statement_lines).strip()
                        if stmt and not stmt.startswith('--'):
                            cursor.execute(stmt)
                            connection.commit()
                        statement_lines = []
                    # Update delimiter
                    current_delimiter = line.split()[-1]
                elif current_delimiter in line:
                    # Check if line ends with current delimiter
                    if line.rstrip().endswith(current_delimiter):
                        statement_lines.append(line.rstrip()[:-len(current_delimiter)])
                        stmt = '\n'.join(statement_lines).strip()
                        if stmt and not stmt.startswith('--'):
                            cursor.execute(stmt)
                            connection.commit()
                        statement_lines = []
                    else:
                        statement_lines.append(line)
                else:
                    statement_lines.append(line)
            
            # Flush any remaining statement
            if statement_lines:
                stmt = '\n'.join(statement_lines).strip()
                if stmt and not stmt.startswith('--'):
                    cursor.execute(stmt)
                    connection.commit()
        else:
            # Simple split by semicolon for regular SQL
            statements = sql_content.split(';')
            for statement in statements:
                # Clean up whitespace and comments
                statement = '\n'.join(
                    line if not line.strip().startswith('--') else ''
                    for line in statement.split('\n')
                ).strip()
                
                # Skip empty statements
                if not statement:
                    continue
                
                cursor.execute(statement)
                connection.commit()
        
        print(f"✅ {filepath}")
        return True
    except Error as e:
        print(f"❌ {filepath}: {e}")
        return False
    finally:
        cursor.close()

def main():
    print(f"\n🔧 Initializing City_Mood Database")
    print(f"   Host: {DB_CONFIG['host']}:{DB_CONFIG['port']}")
    print(f"   User: {DB_CONFIG['user']}\n")
    
    try:
        # Connect to MySQL (without database, to create it)
        print("📡 Connecting to MySQL...")
        connection = mysql.connector.connect(**DB_CONFIG)
        print("✅ Connected!\n")
        
        # Execute each SQL file
        print("📝 Loading SQL scripts...")
        all_success = True
        
        # First: Create metabase database and user
        if not execute_sql_file(connection, "init-metabase.sql"):
            all_success = False
        
        # Second: Create mood_city database and tables
        if not execute_sql_file(connection, "init.sql"):
            all_success = False
        
        # Third: Create stored procedure
        if not execute_sql_file(connection, "calculate_mood_scores.sql"):
            all_success = False
        
        # Fourth: Create materialized view
        if not execute_sql_file(connection, "mv_daily_mood.sql"):
            all_success = False
        
        connection.close()
        
        if all_success:
            print(f"\n✅ Database initialized successfully!")
            print(f"\n🎯 Next steps:")
            print(f"   1. Start the aggregator: python aggregator.py")
            print(f"   2. Monitor data collection (runs every 30 minutes)")
            print(f"   3. Query: SELECT * FROM mood_city.mood_score;")
            return 0
        else:
            print(f"\n⚠️  Some scripts failed. Check errors above.")
            return 1
            
    except Error as e:
        print(f"❌ Database connection failed: {e}")
        print(f"\n   Troubleshooting:")
        print(f"   - Is MySQL running? (brew services start mysql)")
        print(f"   - Check credentials in .env file")
        print(f"   - Verify DB_HOST and DB_PORT")
        return 1
    except FileNotFoundError as e:
        print(f"❌ SQL file not found: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
