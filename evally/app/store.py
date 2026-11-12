"""The bookstore's fake back office: books and orders in an in-memory SQLite database.

Every run starts from seed.json, so results never depend on what an earlier run did.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import date
from pathlib import Path

SEED = Path(__file__).with_name("seed.json")
TODAY = date(2026, 11, 12)  # fixed, so return-window answers never change between runs
RETURN_WINDOW_DAYS = 30


class Store:
    def __init__(self, db: sqlite3.Connection):
        self.db = db
        self.db.row_factory = sqlite3.Row
        self._tickets = 0

    @classmethod
    def from_seed(cls, seed: Path = SEED) -> "Store":
        data = json.loads(seed.read_text())
        db = sqlite3.connect(":memory:")
        db.executescript("""
            CREATE TABLE books (isbn TEXT PRIMARY KEY, title TEXT, author TEXT, price REAL,
                                warehouse TEXT, stock INTEGER);
            CREATE TABLE orders (id TEXT PRIMARY KEY, email TEXT, status TEXT,
                                 ordered TEXT, delivered TEXT);
            CREATE TABLE order_items (order_id TEXT, isbn TEXT);
        """)
        db.executemany("INSERT INTO books VALUES (:isbn,:title,:author,:price,:warehouse,:stock)", data["books"])
        db.executemany("INSERT INTO orders VALUES (:id,:email,:status,:ordered,:delivered)", data["orders"])
        db.executemany("INSERT INTO order_items VALUES (?,?)",
                       [(o["id"], i) for o in data["orders"] for i in o["isbns"]])
        return cls(db)

    def order(self, order_id: str, email: str) -> dict | None:
        row = self.db.execute("SELECT * FROM orders WHERE id=? AND lower(email)=lower(?)",
                              (order_id.strip().upper(), email.strip())).fetchone()
        if row is None:
            return None
        items = self.db.execute(
            "SELECT b.title, b.isbn, b.price FROM order_items i JOIN books b ON b.isbn=i.isbn WHERE i.order_id=?",
            (row["id"],)).fetchall()
        return {"order_id": row["id"], "status": row["status"], "ordered": row["ordered"],
                "delivered": row["delivered"], "items": [dict(i) for i in items]}

    def book(self, isbn: str) -> dict | None:
        row = self.db.execute("SELECT * FROM books WHERE isbn=?", (isbn.strip(),)).fetchone()
        return dict(row) if row else None

    def next_ticket(self) -> str:
        self._tickets += 1
        return f"T-{self._tickets}"
