from contextlib import contextmanager
from db import get_db_connection

@contextmanager
def get_cursor(dict_cursor=True):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=dict_cursor)
    try:
        yield cursor, conn
        conn.commit()
    except:
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()
