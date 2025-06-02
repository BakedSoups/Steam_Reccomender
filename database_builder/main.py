import sqlite3
import sys

def warning():
    response = input("WARNING: the creation of the database takes 1 day due to endpoint restrictions\n I understand(y/n): ")
    return response.lower().strip() == 'y'

def migrate():
    conn = sqlite3.connect('./steam_api.db')
    conn.execute("PRAGMA foreign_keys = ON;")
    create_steam_review_table(conn)
    migrate_steam_review(conn)
    conn.close()

def main():
    if warning():
        print("Proceeding...")
    else:
        print("Operation canceled.")
        return
    
    create_steam_spy()
    init_db()
    migrate()

if __name__ == "__main__":
    from db import init_db
    from init_steamspy import create_steam_spy
    from ign_migration import create_steam_review_table, migrate_steam_review
    main()