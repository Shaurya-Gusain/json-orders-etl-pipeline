from src.etl import extract_data, transform_data, clean_data, validate_data, enrich_data
from src.database import engine
from sqlalchemy import text


# ==================================================
# STEP 1: EXTRACT
# ==================================================

# Define path to the raw JSON dataset
file_path = "data/orders.json"

# Load JSON data into Python
orders = extract_data(file_path)

print("========== EXTRACTION ==========")
print("Total raw records:", len(orders))


# ==================================================
# STEP 2: TRANSFORM
# ==================================================

# Convert nested JSON into separate Pandas DataFrames
orders_df, customers_df, products_df, items_df = transform_data(orders)

print("\n========== DATAFRAME SUMMARY ==========")
print("Orders:", orders_df.shape)
print("Customers:", customers_df.shape)
print("Products:", products_df.shape)
print("Order Items:", items_df.shape)


# ==================================================
# STEP 3: DATA QUALITY CHECKS
# ==================================================

# 3.1 Check duplicate order IDs
print("\n========== ORDER VALIDATION ==========")
print("Total order records:", len(orders_df))
print("Unique order IDs:", orders_df["order_id"].nunique())
print("Duplicate order IDs:", orders_df["order_id"].duplicated().sum())


# 3.2 Check missing values
print("\n========== MISSING VALUES ==========")
print("Missing customer cities:", customers_df["customer_city"].isna().sum())
print("Missing product categories:", products_df["category"].isna().sum())


# 3.3 Check invalid quantities
print("\n========== QUANTITY VALIDATION ==========")
invalid_quantities = items_df[items_df["quantity"] <= 0]
print("Invalid quantity records:", len(invalid_quantities))
print(invalid_quantities.head())


# 3.4 Check unique customers and products
print("\n========== ENTITY VALIDATION ==========")
print("Unique customers:", customers_df["customer_customer_id"].nunique())
print("Unique products:", products_df["product_id"].nunique())


# ==================================================
# STEP 4: INVESTIGATE DATA CONSISTENCY
# ==================================================

# 4.1 Inspect the most frequently occurring order IDs
print("\n========== DUPLICATE ORDER INVESTIGATION ==========")
print(orders_df["order_id"].value_counts().head(10))


# 4.2 Check whether one customer ID maps to multiple email addresses
print("\n========== CUSTOMER CONSISTENCY ==========")
customer_email_counts = (
    orders_df.groupby("customer_customer_id")["customer_email"]
    .nunique()
)
print("Number of distinct emails per customer:")
print(customer_email_counts.value_counts())


# 4.3 Check whether one product ID maps to multiple product names
print("\n========== PRODUCT CONSISTENCY ==========")
product_name_counts = (
    items_df.groupby("product_id")["product_name"]
    .nunique()
)
print("Number of distinct names per product:")
print(product_name_counts.value_counts())


# ==================================================
# STEP 5: CLEAN AND VALIDATE DATA
# ==================================================

# Clean the DataFrames using cleaning logic
orders_df, customers_df, products_df, items_df = clean_data(
    orders_df,
    customers_df,
    products_df,
    items_df
)

print("\n========== CLEANED DATA SUMMARY ==========")
print("Orders:", orders_df.shape)
print("Customers:", customers_df.shape)
print("Products:", products_df.shape)
print("Order Items:", items_df.shape)

# Run post-cleaning validation checks
validation_passed = validate_data(
    orders_df,
    customers_df,
    products_df,
    items_df
)

if not validation_passed:
    raise ValueError(
        "Data validation failed. Stopping pipeline."
    )

# ==================================================
# STEP 6: FEATURE ENGINEERING   
# ==================================================

orders_df, items_df = enrich_data(orders_df, items_df)

print("\n========== REVENUE ANALYSIS ==========")

# Display order-level revenue
print("\nOrders with calculated revenue:")
print(orders_df[["order_id", "order_total", "total_items"]].head())

# Display product-level revenue
print("\nOrder items with calculated revenue:")
print(items_df[["order_id", "product_name", "line_total"]].head())

# Calculate overall revenue
total_revenue = items_df["line_total"].sum()

print("\nTotal Revenue: ₹", total_revenue)

# Calculate average order value
average_order_value = orders_df["order_total"].mean()

print("Average Order Value: ₹", round(average_order_value, 2))

print("\n========== DATAFRAME SCHEMAS ==========")

for name, df in {
    "Orders": orders_df,
    "Customers": customers_df,
    "Products": products_df,
    "Order Items": items_df
}.items():

    print(f"\n{name}")
    print(df.dtypes)

# Prepare Customers DataFrame
customers_to_load = customers_df.rename(
    columns={"customer_customer_id": "customer_id"}
)

# Prepare Products DataFrame
products_to_load = products_df.copy()

# Prepare Orders DataFrame
orders_to_load = orders_df[
    [
        "order_id",
        "order_date",
        "order_status",
        "customer_customer_id",
        "payment_method",
        "payment_status",
        "order_total",
        "total_items"
    ]
].rename(
    columns={"customer_customer_id": "customer_id"}
)

# Prepare Order Items DataFrame
order_items_to_load = items_df[
    [
        "order_id",
        "product_id",
        "quantity",
        "unit_price",
        "line_total"
    ]
]

# Load data into MySQL using a full-refresh strategy

try:
    with engine.begin() as connection:

        # Delete existing records in reverse dependency order
        connection.execute(text("DELETE FROM order_items"))
        connection.execute(text("DELETE FROM orders"))
        connection.execute(text("DELETE FROM products"))
        connection.execute(text("DELETE FROM customers"))

        # Load parent tables first
        customers_to_load.to_sql(
            name="customers",
            con=connection,
            if_exists="append",
            index=False
        )

        products_to_load.to_sql(
            name="products",
            con=connection,
            if_exists="append",
            index=False
        )

        # Load dependent tables
        orders_to_load.to_sql(
            name="orders",
            con=connection,
            if_exists="append",
            index=False
        )

        order_items_to_load.to_sql(
            name="order_items",
            con=connection,
            if_exists="append",
            index=False
        )

    print("\nDATA SUCCESSFULLY LOADED INTO MYSQL!")

except Exception as e:
    print("\nDATABASE LOADING FAILED:", e)
    raise