#!/usr/bin/env python3
import sqlite3
from rich.console import Console
from rich.table import Table

console = Console()
conn = sqlite3.connect("db.sqlite3")
cursor = conn.cursor()

# Users table
cursor.execute("SELECT * FROM users")
users = cursor.fetchall()
table = Table(title="Users Database")
table.add_column("ID")
table.add_column("Name")
table.add_column("Username")
table.add_column("Status")
table.add_column("Created")
table.add_column("Updated")

for row in users:
    table.add_row(
        str(row[0]), row[1], row[2] or "None", row[3], row[4][:19], row[5][:19]
    )

console.print(table)

# Pending verifications table
cursor.execute("SELECT * FROM pending_verifications")
pending = cursor.fetchall()

if pending:
    ptable = Table(title="Pending Verifications")
    ptable.add_column("User ID")
    ptable.add_column("Chat ID")
    ptable.add_column("Name")
    ptable.add_column("Question")
    ptable.add_column("Answer")
    ptable.add_column("Created")

    for row in pending:
        ptable.add_row(str(row[0]), str(row[1]), row[2], row[3], row[4], row[5][:19])

    console.print(ptable)

conn.close()
