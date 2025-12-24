import sqlite3
import json

class Database:
    def __init__(self, config_path='config.json'):
        with open(config_path, 'r') as f:
            self.config = json.load(f)
        
        self.db_type = self.config['type']
        if self.db_type == 'sqlite':
            self.conn = sqlite3.connect(self.config['database'])
        else:
            raise ValueError("Bu örnek için sadece SQLite desteklenmektedir.")

    def get_schema(self):
        """
        Tablo isimlerini VE sütun tiplerini çeker.
        Örnek Çıktı: {'Users': ['id (INTEGER)', 'name (TEXT)']}
        """
        cursor = self.conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        
        schema = {}
        for table in tables:
            table_name = table[0]
            # PRAGMA table_info sütunları: (cid, name, type, notnull, dflt_value, pk)
            cursor.execute(f'PRAGMA table_info("{table_name}")')
            columns = cursor.fetchall()
            # Kritik Düzeltme: Sütun isminin yanına tipini ekliyoruz.
            schema[table_name] = [f"{col[1]} ({col[2]})" for col in columns]
            
        return schema

    def execute_query(self, query):
        """Sadece SELECT sorgularını çalıştırır (Read-Only mod)."""
        cursor = self.conn.cursor()
        
        # Güvenlik: Sadece SELECT sorgularına izin ver
        if not query.strip().upper().startswith('SELECT'):
            return "SQL Hatası: Güvenlik nedeniyle sadece SELECT sorguları desteklenmektedir."
        
        try:
            cursor.execute(query)
            columns = [description[0] for description in cursor.description]
            rows = cursor.fetchall()
            return {"columns": columns, "data": rows}
        except Exception as e:
            return f"SQL Hatası: {str(e)}"

    def close(self):
        self.conn.close()