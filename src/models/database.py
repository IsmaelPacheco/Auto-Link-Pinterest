"""
database.py
Gerencia o banco de dados SQLite local para histórico de postagens,
controle de deduplicação (anti-repetição) e contagem diária.
"""
import sqlite3
import logging
from datetime import datetime, date
from pathlib import Path
from typing import List, Dict, Any, Optional

logger = logging.getLogger("AutoLink.Database")

DB_PATH = Path(__file__).resolve().parent.parent.parent / "autolink.db"


class Database:
    """Interface SQLite para controle de publicações do AutoLink Pinterest."""

    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        """Cria as tabelas necessárias se não existirem."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS posted_pins (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    shopee_item_id TEXT UNIQUE,
                    title TEXT NOT NULL,
                    original_price REAL,
                    discount_price REAL,
                    affiliate_link TEXT,
                    image_path TEXT,
                    pinterest_pin_id TEXT,
                    pinterest_board_id TEXT,
                    pinterest_url TEXT,
                    status TEXT DEFAULT 'SUCCESS',
                    error_message TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_shopee_item 
                ON posted_pins (shopee_item_id)
            """)
            conn.commit()

    def is_already_posted(self, shopee_item_id: str) -> bool:
        """Verifica se um produto já foi postado com sucesso no Pinterest."""
        if not shopee_item_id:
            return False
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 1 FROM posted_pins 
                WHERE shopee_item_id = ? AND status = 'SUCCESS'
                LIMIT 1
            """, (str(shopee_item_id),))
            return cursor.fetchone() is not None

    def add_pin(
        self,
        shopee_item_id: str,
        title: str,
        affiliate_link: str,
        original_price: Optional[float] = None,
        discount_price: Optional[float] = None,
        image_path: Optional[str] = None,
        pinterest_pin_id: Optional[str] = None,
        pinterest_board_id: Optional[str] = None,
        pinterest_url: Optional[str] = None,
        status: str = "SUCCESS",
        error_message: Optional[str] = None
    ) -> int:
        """Registra uma publicação no banco de dados."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO posted_pins (
                    shopee_item_id, title, original_price, discount_price,
                    affiliate_link, image_path, pinterest_pin_id,
                    pinterest_board_id, pinterest_url, status, error_message, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                str(shopee_item_id) if shopee_item_id else None,
                title,
                original_price,
                discount_price,
                affiliate_link,
                image_path,
                pinterest_pin_id,
                pinterest_board_id,
                pinterest_url,
                status,
                error_message,
                datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            ))
            conn.commit()
            return cursor.lastrowid

    def get_pins_posted_today_count(self) -> int:
        """Retorna o número de pins postados com sucesso hoje."""
        today_str = date.today().strftime("%Y-%m-%d")
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT COUNT(*) FROM posted_pins
                WHERE status = 'SUCCESS' AND created_at >= ?
            """, (f"{today_str} 00:00:00",))
            row = cursor.fetchone()
            return row[0] if row else 0

    def get_all_pins(self, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """Retorna lista de pins postados para exibição na interface."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM posted_pins
                ORDER BY id DESC
                LIMIT ? OFFSET ?
            """, (limit, offset))
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def get_total_pins_count(self) -> int:
        """Total geral de pins postados com sucesso."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM posted_pins WHERE status = 'SUCCESS'")
            row = cursor.fetchone()
            return row[0] if row else 0

