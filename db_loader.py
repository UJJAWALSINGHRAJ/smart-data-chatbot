import sqlite3
import pandas as pd
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = BASE_DIR / "olist_ecommerce.db"

def load_csv(file_name):
    file_path = DATA_DIR / file_name
    print(f"Loading {file_name}...")
    return pd.read_csv(file_path)

def main():
    conn = sqlite3.connect(DB_PATH)

    customers = load_csv("olist_customers_dataset.csv")
    orders = load_csv("olist_orders_dataset.csv")
    items = load_csv("olist_order_items_dataset.csv")
    payments = load_csv("olist_order_payments_dataset.csv")
    reviews = load_csv("olist_order_reviews_dataset.csv")
    products = load_csv("olist_products_dataset.csv")
    sellers = load_csv("olist_sellers_dataset.csv")

    customers.to_sql("customers", conn, if_exists="replace", index=False)
    orders.to_sql("orders", conn, if_exists="replace", index=False)
    items.to_sql("order_items", conn, if_exists="replace", index=False)
    payments.to_sql("payments", conn, if_exists="replace", index=False)
    reviews.to_sql("reviews", conn, if_exists="replace", index=False)
    products.to_sql("products", conn, if_exists="replace", index=False)
    sellers.to_sql("sellers", conn, if_exists="replace", index=False)

    print("Database created successfully!")

    conn.close()

if __name__ == "__main__":
    main()