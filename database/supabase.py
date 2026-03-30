import psycopg2
from config.settings import DATABASE_URL

class SupabaseDB:
    def __init__(self):
        self.conn = psycopg2.connect(DATABASE_URL)
        self.cur = self.conn.cursor()
    
    def execute(self, query, params=None):
        self.cur.execute(query, params)
        self.conn.commit()
        return self.cur
    
    def fetch_one(self, query, params=None):
        self.cur.execute(query, params)
        return self.cur.fetchone()
    
    def fetch_all(self, query, params=None):
        self.cur.execute(query, params)
        return self.cur.fetchall()
    
    def close(self):
        self.cur.close()
        self.conn.close()

db = SupabaseDB()
