import sqlite3
import pandas as pd

conn = sqlite3.connect("olist_ecommerce.db")

query = """
SELECT COUNT(*) AS total_orders
FROM orders;
"""

df = pd.read_sql_query(query, conn)

print(df)

conn.close()