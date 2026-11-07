# JSON Orders ETL Pipeline

An end-to-end data engineering project that extracts nested retail order data from JSON, transforms and cleans it using Pandas, and loads the processed data into a relational MySQL database using SQLAlchemy.

## Project Overview

Retail order data is often stored in nested JSON structures containing customer information, order details, payment information, and multiple products per order.

This project builds an ETL pipeline to transform that nested data into structured relational tables and perform data quality checks and business analysis.

### Dataset

The project uses a synthetic retail orders dataset containing:

| Metric | Count |
|---|---:|
| Raw order records | 12,120 |
| Unique orders | 12,000 |
| Duplicate order records | 120 |
| Unique customers | 3,000 |
| Unique products | 500 |
| Original order line items | Approximately 38,383 |

The dataset includes missing customer cities, missing product categories, duplicate orders, and invalid quantities to simulate common data quality issues.

## Technology Stack

- Python
- Pandas
- MySQL
- SQLAlchemy
- PyMySQL
- SQL

## Architecture

```text
       Raw JSON Dataset
              |
              v
       Data Extraction
              |
              v
      JSON Normalization
              |
              v
     Data Transformation
              |
              v
       Data Cleaning
              |
              v
      Data Validation
              |
              v
       Data Enrichment
              |
              v
      SQLAlchemy Engine
              |
              v
        MySQL Database
              |
              v
      SQL Analysis
```

## ETL Workflow

### 1. Extraction

- Read raw JSON data using Python's JSON library.
- Load the nested records into memory.

### 2. Transformation

- Flatten nested order-level JSON using `pandas.json_normalize()`.
- Extract customer and product information into separate DataFrames.
- Extract nested product arrays into an order-items DataFrame.
- Preserve relationships using customer IDs, product IDs, and order IDs.

### 3. Data Cleaning

- Remove duplicate orders using `order_id`.
- Handle missing customer cities by replacing them with `Unknown`.
- Handle missing product categories using `Uncategorized`.
- Remove order items with zero or negative quantities.
- Retain valid relationships between orders and their line items.

### 4. Data Validation

The pipeline checks:

- Duplicate order IDs.
- Missing customer cities.
- Missing product categories.
- Invalid quantities.
- Missing customer references.
- Missing product references.
- Missing order references.

Data loading is stopped if validation fails.

### 5. Data Enrichment

- Calculate revenue for each order item using unit price multiplied by quantity.
- Aggregate line-item revenue to calculate total order revenue.
- Calculate total item quantities per order.
- Calculate overall revenue and average order value.

### 6. Database Loading

The transformed DataFrames are loaded into MySQL using Pandas `to_sql()` and SQLAlchemy.

A full-refresh strategy clears existing records before loading the latest dataset. Database operations are performed within a transaction.

## Database Schema

The pipeline creates four relational tables:

| Table | Description |
|---|---|
| customers | Customer information |
| products | Product information |
| orders | Order-level details |
| order_items | Individual products associated with orders |

### Relationships

- One customer can place multiple orders.
- One order can contain multiple order items.
- One product can appear in multiple order items.

Primary keys and foreign keys enforce relational integrity.

## Results

After cleaning and loading, the database contains:

| Table | Records |
|---|---:|
| Customers | 3,000 |
| Products | 500 |
| Orders | 12,000 |
| Order Items | 37,947 |

Additional results:

- 120 duplicate order records removed.
- 65 missing customer cities handled.
- 5 missing product categories handled.
- 45 invalid quantity records removed.
- No duplicate order IDs after cleaning.
- No missing customer, product, or order references.
- No mismatches between stored order revenue and independently aggregated line-item revenue.

Total calculated revenue: ₹102,685,455.

Average order value: ₹8,557.12.

## SQL Analysis

The loaded database supports business analysis using SQL.

Examples include:

### Top-selling products

```sql
SELECT
    p.product_name,
    SUM(oi.quantity) AS total_quantity_sold,
    SUM(oi.line_total) AS total_revenue
FROM products p
JOIN order_items oi
    ON p.product_id = oi.product_id
GROUP BY p.product_id, p.product_name
ORDER BY total_quantity_sold DESC
LIMIT 10;
```

### Revenue by customer city

```sql
SELECT
    c.customer_city,
    COUNT(o.order_id) AS total_orders,
    SUM(o.order_total) AS total_revenue
FROM customers c
JOIN orders o
    ON c.customer_id = o.customer_id
GROUP BY c.customer_city
ORDER BY total_revenue DESC;
```

### Highest-spending customers

```sql
SELECT
    c.customer_name,
    COUNT(o.order_id) AS total_orders,
    SUM(o.order_total) AS total_spent
FROM customers c
JOIN orders o
    ON c.customer_id = o.customer_id
GROUP BY c.customer_id, c.customer_name
ORDER BY total_spent DESC
LIMIT 10;
```

## Project Structure

```text
resume_project/
│
├── data/
│   └── orders.json
│
├── src/
│   ├── __init__.py
│   ├── etl.py
│   └── database.py
│
├── main.py
├── requirements.txt
├── .env
├── .env.example
├── .gitignore
└── README.md
```

## Setup and Execution

### 1. Clone the repository

```bash
git clone <repository-url>
cd resume_project
```

### 2. Create a virtual environment

```bash
python -m venv .venv
```

Activate it on Windows:

```powershell
.venv\Scripts\Activate.ps1
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure database credentials

Create a `.env` file in the project root:

```env
DB_USER=root
DB_PASSWORD=your_password
DB_HOST=localhost
DB_PORT=3306
DB_NAME=orders_db
```

### 5. Create the database

Run the database schema creation SQL in MySQL Workbench before executing the pipeline.

### 6. Run the pipeline

```bash
python main.py
```

## Future Improvements

- Add structured logging.
- Implement incremental data loading.
- Add automated unit tests.
- Introduce configurable data quality thresholds.
- Schedule pipeline execution.