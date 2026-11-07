import json
import pandas as pd

def extract_data(file_path):
    # Load raw JSON data from file
    with open(file_path, "r", encoding="utf-8") as file:
        data = json.load(file)
    return data

def transform_data(orders):

    # Flatten nested order-level JSON data into a DataFrame
    orders_df = pd.json_normalize(orders, sep="_")

    # Remove duplicate orders using order_id, keeping the first occurrence
    unique_orders = {}

    for order in orders:
        unique_orders.setdefault(order["order_id"], order)

    # Convert unique order records back into a list
    unique_order_records = list(unique_orders.values())

    # Extract product records from unique orders while retaining the parent order_id
    items_df = pd.json_normalize(
        unique_order_records,
        record_path="products",
        meta=["order_id"],
        sep="_"
    )

    # Extract customer details and retain one record per unique customer_id
    customer_df = orders_df[
        [
            "customer_customer_id",
            "customer_name",
            "customer_email",
            "customer_city"
        ]
    ].drop_duplicates(subset=["customer_customer_id"])

    # Extract product details and retain one record per unique product_id
    product_df = items_df[
        [
            "product_id",
            "product_name",
            "category",
            "unit_price"
        ]
    ].drop_duplicates(subset=["product_id"])

    # Return the transformed DataFrames
    return orders_df, customer_df, product_df, items_df


def clean_data(orders_df, customers_df, products_df, items_df):
    # Work on copies so that original DataFrames remain unchanged
    orders_df = orders_df.copy()
    customers_df = customers_df.copy()
    products_df = products_df.copy()
    items_df = items_df.copy()

    # 1. Remove duplicate orders
    orders_df = orders_df.drop_duplicates(
        subset=["order_id"],
        keep="first"
    )

    # 2. Keep only items belonging to valid orders
    valid_order_ids = orders_df["order_id"]
    items_df = items_df[
        items_df["order_id"].isin(valid_order_ids)
    ]

    # 3. Handle missing customer cities
    customers_df["customer_city"] = (
        customers_df["customer_city"].fillna("Unknown")
    )

    # 4. Handle missing product categories
    products_df["category"] = (
        products_df["category"].fillna("Uncategorized")
    )

    # 5. Remove invalid order items
    items_df = items_df[
        items_df["quantity"] > 0
    ]

    return orders_df, customers_df, products_df, items_df


def validate_data(orders_df, customers_df, products_df, items_df):
    print("\n========== POST-CLEANING VALIDATION ==========")

    # 1. Check whether duplicate orders still exist
    duplicate_orders = orders_df["order_id"].duplicated().sum()
    print("Duplicate orders:", duplicate_orders)

    # 2. Check for missing customer cities
    missing_cities = customers_df["customer_city"].isna().sum()
    print("Missing customer cities:", missing_cities)

    # 3. Check for missing product categories
    missing_categories = products_df["category"].isna().sum()
    print("Missing product categories:", missing_categories)

    # 4. Check for invalid quantities
    invalid_quantities = (items_df["quantity"] <= 0).sum()
    print("Invalid quantities:", invalid_quantities)

    # 5. Check referential integrity: Every order should reference an existing customer
    missing_customers = (
        ~orders_df["customer_customer_id"].isin(
            customers_df["customer_customer_id"]
        )
    ).sum()
    print("Orders with missing customers:", missing_customers)

    # 6. Check referential integrity: Every order item should reference an existing product
    missing_products = (
        ~items_df["product_id"].isin(products_df["product_id"])
    ).sum()
    print("Order items with missing products:", missing_products)

    # 7. Check referential integrity: Every order item should reference an existing order
    missing_orders = (
        ~items_df["order_id"].isin(orders_df["order_id"])
    ).sum()
    print("Order items with missing orders:", missing_orders)

    # 8. Evaluate overall validation result
    checks = [
        duplicate_orders == 0,
        missing_cities == 0,
        missing_categories == 0,
        invalid_quantities == 0,
        missing_customers == 0,
        missing_products == 0,
        missing_orders == 0
    ]

    validation_passed = all(checks)

    if validation_passed:
        print("\nVALIDATION PASSED: All checks successful.")
    else:
        print("\nVALIDATION FAILED: Some checks need attention.")

    return validation_passed

def enrich_data(orders_df, items_df):
    
    orders_df = orders_df.copy()
    items_df = items_df.copy()

    # ----------------------------------------
    # 1. CALCULATE LINE-ITEM REVENUE
    # ----------------------------------------

    items_df["line_total"] = items_df["unit_price"] * items_df["quantity"]

    # ----------------------------------------
    # 2. CALCULATE TOTAL REVENUE PER ORDER
    # ----------------------------------------

    order_revenue = items_df.groupby("order_id")["line_total"].sum().reset_index()

    order_revenue = order_revenue.rename(columns = {"line_total" : "order_total"})

    # ----------------------------------------
    # 3. MERGE ORDER REVENUE WITH ORDERS
    # ----------------------------------------

    orders_df = orders_df.merge(
        order_revenue,
        on = "order_id",
        how = "left"
    )

    # ----------------------------------------
    # 4. CALCULATE TOTAL ITEMS PER ORDER
    # ----------------------------------------

    item_counts = items_df.groupby("order_id")["quantity"].sum().reset_index()

    item_counts = item_counts.rename(columns={"quantity": "total_items"})

    orders_df = orders_df.merge(
        item_counts,
        on="order_id",
        how="left"
    )
    orders_df[["order_total", "total_items"]] = orders_df[["order_total", "total_items"]].fillna(0)
    

    # Convert order_date to Pandas datetime format
    orders_df["order_date"] = pd.to_datetime(orders_df["order_date"])

    # Ensure order_id has the same integer type across DataFrames
    items_df["order_id"] = items_df["order_id"].astype("int64")

    # Convert total_items from float to integer
    orders_df["total_items"] = orders_df["total_items"].astype("int64")
    
    return orders_df, items_df