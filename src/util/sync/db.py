from pathlib import Path
from typing import List

from ..common._json import json_dumps, json_loads
from ..common.config import appdata_path
from ..common.database import Database
from .info import SyncSourceInfo


class SyncDatabase(Database):
    def __init__(self):
        self.path = Path(appdata_path) / "Bili23 Downloader" / "sync.db"

        self.check_and_create_table()

    def check_and_create_table(self):
        self.execute_script("""
            PRAGMA journal_mode = WAL;
            CREATE TABLE IF NOT EXISTS "sync_source" (
                "id" INTEGER UNIQUE,
                "sync_id" TEXT UNIQUE,
                "title" TEXT,
                "url" TEXT,
                "source_type" TEXT,
                "enabled" INTEGER,
                "updated_time" INTEGER,
                "data" TEXT,
                PRIMARY KEY("id" AUTOINCREMENT)
            );
            CREATE INDEX IF NOT EXISTS "idx_sync_source_url" ON "sync_source" ("url");
            """)

    def query_sources(self) -> List[SyncSourceInfo]:
        result = self.query("""
            SELECT data FROM sync_source ORDER BY updated_time DESC
        """)

        source_list = []

        for entry in result:
            source = SyncSourceInfo()
            source.from_dict(json_loads(entry[0]))
            source_list.append(source)

        return source_list

    def add_source(self, source: SyncSourceInfo):
        self.execute("""
            INSERT INTO sync_source (sync_id, title, url, source_type, enabled, updated_time, data)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            source.sync_id,
            source.title,
            source.url,
            source.source_type,
            1 if source.enabled else 0,
            source.updated_time,
            json_dumps(source.to_dict()),
        ))

    def update_source(self, source: SyncSourceInfo):
        self.execute("""
            UPDATE sync_source
            SET title = ?, url = ?, source_type = ?, enabled = ?, updated_time = ?, data = ?
            WHERE sync_id = ?
        """, (
            source.title,
            source.url,
            source.source_type,
            1 if source.enabled else 0,
            source.updated_time,
            json_dumps(source.to_dict()),
            source.sync_id,
        ))

    def delete_source(self, sync_id: str):
        self.execute("""
            DELETE FROM sync_source WHERE sync_id = ?
        """, (sync_id,))

