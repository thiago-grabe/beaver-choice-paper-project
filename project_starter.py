# Standard library imports
import asyncio
import ast
import json
import os
import re
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union

# Third-party imports
import dotenv
import numpy as np
import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, Engine
from sqlalchemy.sql import text

# AI/ML imports
from pydantic_ai import Agent, RunContext
from pydantic_ai.models.openai import OpenAIModel

# Load environment variables
load_dotenv()

# Create an SQLite database
db_engine = create_engine("sqlite:///munder_difflin.db")

# List containing the different kinds of papers 
paper_supplies = [
    # Paper Types (priced per sheet unless specified)
    {"item_name": "A4 paper",                         "category": "paper",        "unit_price": 0.05},
    {"item_name": "Letter-sized paper",              "category": "paper",        "unit_price": 0.06},
    {"item_name": "Cardstock",                        "category": "paper",        "unit_price": 0.15},
    {"item_name": "Colored paper",                    "category": "paper",        "unit_price": 0.10},
    {"item_name": "Glossy paper",                     "category": "paper",        "unit_price": 0.20},
    {"item_name": "Matte paper",                      "category": "paper",        "unit_price": 0.18},
    {"item_name": "Recycled paper",                   "category": "paper",        "unit_price": 0.08},
    {"item_name": "Eco-friendly paper",               "category": "paper",        "unit_price": 0.12},
    {"item_name": "Poster paper",                     "category": "paper",        "unit_price": 0.25},
    {"item_name": "Banner paper",                     "category": "paper",        "unit_price": 0.30},
    {"item_name": "Kraft paper",                      "category": "paper",        "unit_price": 0.10},
    {"item_name": "Construction paper",               "category": "paper",        "unit_price": 0.07},
    {"item_name": "Wrapping paper",                   "category": "paper",        "unit_price": 0.15},
    {"item_name": "Glitter paper",                    "category": "paper",        "unit_price": 0.22},
    {"item_name": "Decorative paper",                 "category": "paper",        "unit_price": 0.18},
    {"item_name": "Letterhead paper",                 "category": "paper",        "unit_price": 0.12},
    {"item_name": "Legal-size paper",                 "category": "paper",        "unit_price": 0.08},
    {"item_name": "Crepe paper",                      "category": "paper",        "unit_price": 0.05},
    {"item_name": "Photo paper",                      "category": "paper",        "unit_price": 0.25},
    {"item_name": "Uncoated paper",                   "category": "paper",        "unit_price": 0.06},
    {"item_name": "Butcher paper",                    "category": "paper",        "unit_price": 0.10},
    {"item_name": "Heavyweight paper",                "category": "paper",        "unit_price": 0.20},
    {"item_name": "Standard copy paper",              "category": "paper",        "unit_price": 0.04},
    {"item_name": "Bright-colored paper",             "category": "paper",        "unit_price": 0.12},
    {"item_name": "Patterned paper",                  "category": "paper",        "unit_price": 0.15},

    # Product Types (priced per unit)
    {"item_name": "Paper plates",                     "category": "product",      "unit_price": 0.10},  # per plate
    {"item_name": "Paper cups",                       "category": "product",      "unit_price": 0.08},  # per cup
    {"item_name": "Paper napkins",                    "category": "product",      "unit_price": 0.02},  # per napkin
    {"item_name": "Disposable cups",                  "category": "product",      "unit_price": 0.10},  # per cup
    {"item_name": "Table covers",                     "category": "product",      "unit_price": 1.50},  # per cover
    {"item_name": "Envelopes",                        "category": "product",      "unit_price": 0.05},  # per envelope
    {"item_name": "Sticky notes",                     "category": "product",      "unit_price": 0.03},  # per sheet
    {"item_name": "Notepads",                         "category": "product",      "unit_price": 2.00},  # per pad
    {"item_name": "Invitation cards",                 "category": "product",      "unit_price": 0.50},  # per card
    {"item_name": "Flyers",                           "category": "product",      "unit_price": 0.15},  # per flyer
    {"item_name": "Party streamers",                  "category": "product",      "unit_price": 0.05},  # per roll
    {"item_name": "Decorative adhesive tape (washi tape)", "category": "product", "unit_price": 0.20},  # per roll
    {"item_name": "Paper party bags",                 "category": "product",      "unit_price": 0.25},  # per bag
    {"item_name": "Name tags with lanyards",          "category": "product",      "unit_price": 0.75},  # per tag
    {"item_name": "Presentation folders",             "category": "product",      "unit_price": 0.50},  # per folder

    # Large-format items (priced per unit)
    {"item_name": "Large poster paper (24x36 inches)", "category": "large_format", "unit_price": 1.00},
    {"item_name": "Rolls of banner paper (36-inch width)", "category": "large_format", "unit_price": 2.50},

    # Specialty papers
    {"item_name": "100 lb cover stock",               "category": "specialty",    "unit_price": 0.50},
    {"item_name": "80 lb text paper",                 "category": "specialty",    "unit_price": 0.40},
    {"item_name": "250 gsm cardstock",                "category": "specialty",    "unit_price": 0.30},
    {"item_name": "220 gsm poster paper",             "category": "specialty",    "unit_price": 0.35},
]

# Given below are some utility functions you can use to implement your multi-agent system

def generate_sample_inventory(paper_supplies: list, coverage: float = 0.4, seed: int = 137) -> pd.DataFrame:
    """
    Generate inventory for exactly a specified percentage of items from the full paper supply list.

    This function randomly selects exactly `coverage` × N items from the `paper_supplies` list,
    and assigns each selected item:
    - a random stock quantity between 200 and 800,
    - a minimum stock level between 50 and 150.

    The random seed ensures reproducibility of selection and stock levels.

    Args:
        paper_supplies (list): A list of dictionaries, each representing a paper item with
                               keys 'item_name', 'category', and 'unit_price'.
        coverage (float, optional): Fraction of items to include in the inventory (default is 0.4, or 40%).
        seed (int, optional): Random seed for reproducibility (default is 137).

    Returns:
        pd.DataFrame: A DataFrame with the selected items and assigned inventory values, including:
                      - item_name
                      - category
                      - unit_price
                      - current_stock
                      - min_stock_level
    """
    # Ensure reproducible random output
    np.random.seed(seed)

    # Calculate number of items to include based on coverage
    num_items = int(len(paper_supplies) * coverage)

    # Randomly select item indices without replacement
    selected_indices = np.random.choice(
        range(len(paper_supplies)),
        size=num_items,
        replace=False
    )

    # Extract selected items from paper_supplies list
    selected_items = [paper_supplies[i] for i in selected_indices]

    # Construct inventory records
    inventory = []
    for item in selected_items:
        inventory.append({
            "item_name": item["item_name"],
            "category": item["category"],
            "unit_price": item["unit_price"],
            "current_stock": np.random.randint(200, 800),  # Realistic stock range
            "min_stock_level": np.random.randint(50, 150)  # Reasonable threshold for reordering
        })

    # Return inventory as a pandas DataFrame
    return pd.DataFrame(inventory)

def init_database(db_engine: Engine, seed: int = 137) -> Engine:    
    """
    Set up the Munder Difflin database with all required tables and initial records.

    This function performs the following tasks:
    - Creates the 'transactions' table for logging stock orders and sales
    - Loads customer inquiries from 'quote_requests.csv' into a 'quote_requests' table
    - Loads previous quotes from 'quotes.csv' into a 'quotes' table, extracting useful metadata
    - Generates a random subset of paper inventory using `generate_sample_inventory`
    - Inserts initial financial records including available cash and starting stock levels

    Args:
        db_engine (Engine): A SQLAlchemy engine connected to the SQLite database.
        seed (int, optional): A random seed used to control reproducibility of inventory stock levels.
                              Default is 137.

    Returns:
        Engine: The same SQLAlchemy engine, after initializing all necessary tables and records.

    Raises:
        Exception: If an error occurs during setup, the exception is printed and raised.
    """
    try:
        # ----------------------------
        # 1. Create an empty 'transactions' table schema
        # ----------------------------
        transactions_schema = pd.DataFrame({
            "id": [],
            "item_name": [],
            "transaction_type": [],  # 'stock_orders' or 'sales'
            "units": [],             # Quantity involved
            "price": [],             # Total price for the transaction
            "transaction_date": [],  # ISO-formatted date
        })
        transactions_schema.to_sql("transactions", db_engine, if_exists="replace", index=False)

        # Set a consistent starting date
        initial_date = datetime(2025, 1, 1).isoformat()

        # ----------------------------
        # 2. Load and initialize 'quote_requests' table
        # ----------------------------
        quote_requests_df = pd.read_csv("quote_requests.csv")
        quote_requests_df["id"] = range(1, len(quote_requests_df) + 1)
        quote_requests_df.to_sql("quote_requests", db_engine, if_exists="replace", index=False)

        # ----------------------------
        # 3. Load and transform 'quotes' table
        # ----------------------------
        quotes_df = pd.read_csv("quotes.csv")
        quotes_df["request_id"] = range(1, len(quotes_df) + 1)
        quotes_df["order_date"] = initial_date

        # Unpack metadata fields (job_type, order_size, event_type) if present
        if "request_metadata" in quotes_df.columns:
            quotes_df["request_metadata"] = quotes_df["request_metadata"].apply(
                lambda x: ast.literal_eval(x) if isinstance(x, str) else x
            )
            quotes_df["job_type"] = quotes_df["request_metadata"].apply(lambda x: x.get("job_type", ""))
            quotes_df["order_size"] = quotes_df["request_metadata"].apply(lambda x: x.get("order_size", ""))
            quotes_df["event_type"] = quotes_df["request_metadata"].apply(lambda x: x.get("event_type", ""))

        # Retain only relevant columns
        quotes_df = quotes_df[[
            "request_id",
            "total_amount",
            "quote_explanation",
            "order_date",
            "job_type",
            "order_size",
            "event_type"
        ]]
        quotes_df.to_sql("quotes", db_engine, if_exists="replace", index=False)

        # ----------------------------
        # 4. Generate inventory and seed stock
        # ----------------------------
        inventory_df = generate_sample_inventory(paper_supplies, seed=seed)

        # Seed initial transactions
        initial_transactions = []

        # Add a starting cash balance via a dummy sales transaction
        initial_transactions.append({
            "item_name": None,
            "transaction_type": "sales",
            "units": None,
            "price": 50000.0,
            "transaction_date": initial_date,
        })

        # Add one stock order transaction per inventory item
        for _, item in inventory_df.iterrows():
            initial_transactions.append({
                "item_name": item["item_name"],
                "transaction_type": "stock_orders",
                "units": item["current_stock"],
                "price": item["current_stock"] * item["unit_price"],
                "transaction_date": initial_date,
            })

        # Commit transactions to database
        pd.DataFrame(initial_transactions).to_sql("transactions", db_engine, if_exists="append", index=False)

        # Save the inventory reference table
        inventory_df.to_sql("inventory", db_engine, if_exists="replace", index=False)

        return db_engine

    except Exception as e:
        print(f"Error initializing database: {e}")
        raise

def create_transaction(
    item_name: str,
    transaction_type: str,
    quantity: int,
    price: float,
    date: Union[str, datetime],
) -> int:
    """
    This function records a transaction of type 'stock_orders' or 'sales' with a specified
    item name, quantity, total price, and transaction date into the 'transactions' table of the database.

    Args:
        item_name (str): The name of the item involved in the transaction.
        transaction_type (str): Either 'stock_orders' or 'sales'.
        quantity (int): Number of units involved in the transaction.
        price (float): Total price of the transaction.
        date (str or datetime): Date of the transaction in ISO 8601 format.

    Returns:
        int: The ID of the newly inserted transaction.

    Raises:
        ValueError: If `transaction_type` is not 'stock_orders' or 'sales'.
        Exception: For other database or execution errors.
    """
    try:
        # Convert datetime to ISO string if necessary
        date_str = date.isoformat() if isinstance(date, datetime) else date

        # Validate transaction type
        if transaction_type not in {"stock_orders", "sales"}:
            raise ValueError("Transaction type must be 'stock_orders' or 'sales'")

        # Prepare transaction record as a single-row DataFrame
        transaction = pd.DataFrame([{
            "item_name": item_name,
            "transaction_type": transaction_type,
            "units": quantity,
            "price": price,
            "transaction_date": date_str,
        }])

        # Insert the record into the database
        transaction.to_sql("transactions", db_engine, if_exists="append", index=False)

        # Fetch and return the ID of the inserted row
        result = pd.read_sql("SELECT last_insert_rowid() as id", db_engine)
        return int(result.iloc[0]["id"])

    except Exception as e:
        print(f"Error creating transaction: {e}")
        raise

def get_all_inventory(as_of_date: str) -> Dict[str, int]:
    """
    Retrieve a snapshot of available inventory as of a specific date.

    This function calculates the net quantity of each item by summing 
    all stock orders and subtracting all sales up to and including the given date.

    Only items with positive stock are included in the result.

    Args:
        as_of_date (str): ISO-formatted date string (YYYY-MM-DD) representing the inventory cutoff.

    Returns:
        Dict[str, int]: A dictionary mapping item names to their current stock levels.
    """
    # SQL query to compute stock levels per item as of the given date
    query = """
        SELECT
            item_name,
            SUM(CASE
                WHEN transaction_type = 'stock_orders' THEN units
                WHEN transaction_type = 'sales' THEN -units
                ELSE 0
            END) as stock
        FROM transactions
        WHERE item_name IS NOT NULL
        AND transaction_date <= :as_of_date
        GROUP BY item_name
        HAVING stock > 0
    """

    # Execute the query with the date parameter
    result = pd.read_sql(query, db_engine, params={"as_of_date": as_of_date})

    # Convert the result into a dictionary {item_name: stock}
    return dict(zip(result["item_name"], result["stock"]))

def get_stock_level(item_name: str, as_of_date: Union[str, datetime]) -> pd.DataFrame:
    """
    Retrieve the stock level of a specific item as of a given date.

    This function calculates the net stock by summing all 'stock_orders' and 
    subtracting all 'sales' transactions for the specified item up to the given date.

    Args:
        item_name (str): The name of the item to look up.
        as_of_date (str or datetime): The cutoff date (inclusive) for calculating stock.

    Returns:
        pd.DataFrame: A single-row DataFrame with columns 'item_name' and 'current_stock'.
    """
    # Convert date to ISO string format if it's a datetime object
    if isinstance(as_of_date, datetime):
        as_of_date = as_of_date.isoformat()

    # SQL query to compute net stock level for the item
    stock_query = """
        SELECT
            item_name,
            COALESCE(SUM(CASE
                WHEN transaction_type = 'stock_orders' THEN units
                WHEN transaction_type = 'sales' THEN -units
                ELSE 0
            END), 0) AS current_stock
        FROM transactions
        WHERE item_name = :item_name
        AND transaction_date <= :as_of_date
    """

    # Execute query and return result as a DataFrame
    return pd.read_sql(
        stock_query,
        db_engine,
        params={"item_name": item_name, "as_of_date": as_of_date},
    )

def get_supplier_delivery_date(input_date_str: str, quantity: int) -> str:
    """
    Estimate the supplier delivery date based on the requested order quantity and a starting date.

    Delivery lead time increases with order size:
        - ≤10 units: same day
        - 11–100 units: 1 day
        - 101–1000 units: 4 days
        - >1000 units: 7 days

    Args:
        input_date_str (str): The starting date in ISO format (YYYY-MM-DD).
        quantity (int): The number of units in the order.

    Returns:
        str: Estimated delivery date in ISO format (YYYY-MM-DD).
    """
    # Debug log (comment out in production if needed)
    print(f"FUNC (get_supplier_delivery_date): Calculating for qty {quantity} from date string '{input_date_str}'")

    # Attempt to parse the input date
    try:
        input_date_dt = datetime.fromisoformat(input_date_str.split("T")[0])
    except (ValueError, TypeError):
        # Fallback to current date on format error
        print(f"WARN (get_supplier_delivery_date): Invalid date format '{input_date_str}', using today as base.")
        input_date_dt = datetime.now()

    # Determine delivery delay based on quantity
    if quantity <= 10:
        days = 0
    elif quantity <= 100:
        days = 1
    elif quantity <= 1000:
        days = 4
    else:
        days = 7

    # Add delivery days to the starting date
    delivery_date_dt = input_date_dt + timedelta(days=days)

    # Return formatted delivery date
    return delivery_date_dt.strftime("%Y-%m-%d")

def get_cash_balance(as_of_date: Union[str, datetime]) -> float:
    """
    Calculate the current cash balance as of a specified date.

    The balance is computed by subtracting total stock purchase costs ('stock_orders')
    from total revenue ('sales') recorded in the transactions table up to the given date.

    Args:
        as_of_date (str or datetime): The cutoff date (inclusive) in ISO format or as a datetime object.

    Returns:
        float: Net cash balance as of the given date. Returns 0.0 if no transactions exist or an error occurs.
    """
    try:
        # Convert date to ISO format if it's a datetime object
        if isinstance(as_of_date, datetime):
            as_of_date = as_of_date.isoformat()

        # Query all transactions on or before the specified date
        transactions = pd.read_sql(
            "SELECT * FROM transactions WHERE transaction_date <= :as_of_date",
            db_engine,
            params={"as_of_date": as_of_date},
        )

        # Compute the difference between sales and stock purchases
        if not transactions.empty:
            total_sales = transactions.loc[transactions["transaction_type"] == "sales", "price"].sum()
            total_purchases = transactions.loc[transactions["transaction_type"] == "stock_orders", "price"].sum()
            return float(total_sales - total_purchases)

        return 0.0

    except Exception as e:
        print(f"Error getting cash balance: {e}")
        return 0.0


def generate_financial_report(as_of_date: Union[str, datetime]) -> Dict:
    """
    Generate a complete financial report for the company as of a specific date.

    This includes:
    - Cash balance
    - Inventory valuation
    - Combined asset total
    - Itemized inventory breakdown
    - Top 5 best-selling products

    Args:
        as_of_date (str or datetime): The date (inclusive) for which to generate the report.

    Returns:
        Dict: A dictionary containing the financial report fields:
            - 'as_of_date': The date of the report
            - 'cash_balance': Total cash available
            - 'inventory_value': Total value of inventory
            - 'total_assets': Combined cash and inventory value
            - 'inventory_summary': List of items with stock and valuation details
            - 'top_selling_products': List of top 5 products by revenue
    """
    # Normalize date input
    if isinstance(as_of_date, datetime):
        as_of_date = as_of_date.isoformat()

    # Get current cash balance
    cash = get_cash_balance(as_of_date)

    # Get current inventory snapshot
    inventory_df = pd.read_sql("SELECT * FROM inventory", db_engine)
    inventory_value = 0.0
    inventory_summary = []

    # Compute total inventory value and summary by item
    for _, item in inventory_df.iterrows():
        stock_info = get_stock_level(item["item_name"], as_of_date)
        stock = stock_info["current_stock"].iloc[0]
        item_value = stock * item["unit_price"]
        inventory_value += item_value

        inventory_summary.append({
            "item_name": item["item_name"],
            "stock": stock,
            "unit_price": item["unit_price"],
            "value": item_value,
        })

    # Identify top-selling products by revenue
    top_sales_query = """
        SELECT item_name, SUM(units) as total_units, SUM(price) as total_revenue
        FROM transactions
        WHERE transaction_type = 'sales' AND transaction_date <= :date
        GROUP BY item_name
        ORDER BY total_revenue DESC
        LIMIT 5
    """
    top_sales = pd.read_sql(top_sales_query, db_engine, params={"date": as_of_date})
    top_selling_products = top_sales.to_dict(orient="records")

    return {
        "as_of_date": as_of_date,
        "cash_balance": cash,
        "inventory_value": inventory_value,
        "total_assets": cash + inventory_value,
        "inventory_summary": inventory_summary,
        "top_selling_products": top_selling_products,
    }


def search_quote_history(search_terms: List[str], limit: int = 5) -> List[Dict]:
    """
    Retrieve a list of historical quotes that match any of the provided search terms.

    The function searches both the original customer request (from `quote_requests`) and
    the explanation for the quote (from `quotes`) for each keyword. Results are sorted by
    most recent order date and limited by the `limit` parameter.

    Args:
        search_terms (List[str]): List of terms to match against customer requests and explanations.
        limit (int, optional): Maximum number of quote records to return. Default is 5.

    Returns:
        List[Dict]: A list of matching quotes, each represented as a dictionary with fields:
            - original_request
            - total_amount
            - quote_explanation
            - job_type
            - order_size
            - event_type
            - order_date
    """
    conditions = []
    params = {}

    # Build SQL WHERE clause using LIKE filters for each search term
    for i, term in enumerate(search_terms):
        param_name = f"term_{i}"
        conditions.append(
            f"(LOWER(qr.response) LIKE :{param_name} OR "
            f"LOWER(q.quote_explanation) LIKE :{param_name})"
        )
        params[param_name] = f"%{term.lower()}%"

    # Combine conditions; fallback to always-true if no terms provided
    where_clause = " AND ".join(conditions) if conditions else "1=1"

    # Final SQL query to join quotes with quote_requests
    query = f"""
        SELECT
            qr.response AS original_request,
            q.total_amount,
            q.quote_explanation,
            q.job_type,
            q.order_size,
            q.event_type,
            q.order_date
        FROM quotes q
        JOIN quote_requests qr ON q.request_id = qr.id
        WHERE {where_clause}
        ORDER BY q.order_date DESC
        LIMIT {limit}
    """

    # Execute parameterized query
    with db_engine.connect() as conn:
        result = conn.execute(text(query), params)
        return [dict(row) for row in result]

########################
########################
########################
# YOUR MULTI AGENT STARTS HERE
########################
########################
########################


# Initialize the OpenAI model (ensure your OPENAI_API_KEY is set in your environment)
openai_model = OpenAIModel('gpt-4o-mini')

# Initialize the database
# (keep this after model init)
db_engine = init_database(db_engine)

# --- Original tool functions (needed by pydantic wrappers) ---

def reorder_assessment_tool(item_name: str, quantity_needed: int, date: str = None) -> dict:
    """Assess if reordering is needed and calculate delivery timeline."""
    if date is None:
        date = datetime.now().isoformat()
    
    current_stock = get_stock_level(item_name, date)
    current_qty = current_stock["current_stock"].iloc[0] if not current_stock.empty else 0
    
    needs_reorder = current_qty < quantity_needed
    
    if needs_reorder:
        reorder_qty = max(quantity_needed - current_qty, 500)  # Minimum reorder of 500
        delivery_date = get_supplier_delivery_date(date, reorder_qty)
        
        # Get item details for pricing
        item_details = next((item for item in paper_supplies if item["item_name"] == item_name), None)
        cost = reorder_qty * item_details["unit_price"] if item_details else 0
        
        return {
            "needs_reorder": True,
            "current_stock": current_qty,
            "quantity_needed": quantity_needed,
            "reorder_quantity": reorder_qty,
            "delivery_date": delivery_date,
            "estimated_cost": cost
        }
    
    return {
        "needs_reorder": False,
        "current_stock": current_qty,
        "quantity_needed": quantity_needed
    }

def transaction_tool(item_name: str, quantity: int, price: float, transaction_type: str = "sales", date: str = None) -> int:
    """Create a transaction in the database."""
    if date is None:
        date = datetime.now().isoformat()
    return create_transaction(item_name, transaction_type, quantity, price, date)

def quote_history_tool(search_terms: list) -> list:
    """Search historical quotes for similar requests."""
    return search_quote_history(search_terms, limit=5)

def price_calculator_tool(items: list, order_size: str = "medium") -> dict:
    """Calculate pricing for requested items with bulk discounts."""
    total_cost = 0
    item_details = []
    
    for item in items:
        item_name = item["item_name"]
        quantity = item["quantity"]
        
        # Find item in paper_supplies
        item_info = next((p for p in paper_supplies if p["item_name"] == item_name), None)
        
        if item_info:
            unit_price = item_info["unit_price"]
            subtotal = quantity * unit_price
            
            # Apply bulk discounts based on order size and quantity
            discount_rate = 0
            if order_size == "large":
                discount_rate = 0.15 if quantity > 1000 else 0.10
            elif order_size == "medium":
                discount_rate = 0.05 if quantity > 500 else 0.03
            elif quantity > 100:
                discount_rate = 0.02
            
            discount = subtotal * discount_rate
            final_price = subtotal - discount
            
            item_details.append({
                "item_name": item_name,
                "quantity": quantity,
                "unit_price": unit_price,
                "subtotal": subtotal,
                "discount_rate": discount_rate,
                "discount": discount,
                "final_price": final_price
            })
            
            total_cost += final_price
    
    return {
        "items": item_details,
        "total_cost": total_cost,
        "order_size": order_size
    }

def quote_generator_tool(customer_request: str, items: list, order_size: str) -> dict:
    """Generate a comprehensive quote for the customer."""
    pricing = price_calculator_tool(items, order_size)
    
    # Create quote explanation
    explanation = f"Thank you for your {order_size} order request! "
    
    if pricing["total_cost"] > 500:
        explanation += "We've applied bulk discounts to provide you with the best value. "
    
    explanation += "Your order includes: "
    for item in pricing["items"]:
        explanation += f"{item['quantity']} {item['item_name']} at ${item['unit_price']:.2f} each"
        if item['discount_rate'] > 0:
            explanation += f" (with {item['discount_rate']*100:.0f}% bulk discount)"
        explanation += ", "
    
    explanation = explanation.rstrip(", ") + ". "
    explanation += f"Total cost: ${pricing['total_cost']:.2f}"
    
    return {
        "total_amount": pricing["total_cost"],
        "quote_explanation": explanation,
        "items": pricing["items"],
        "order_size": order_size
    }

def sales_feasibility_tool(items: list, date: str = None) -> dict:
    """Check if sale is feasible based on inventory."""
    if date is None:
        date = datetime.now().isoformat()
    
    feasible = True
    availability = []
    
    for item in items:
        item_name = item["item_name"]
        quantity = item["quantity"]
        
        stock_info = get_stock_level(item_name, date)
        current_stock = stock_info["current_stock"].iloc[0] if not stock_info.empty else 0
        
        item_feasible = current_stock >= quantity
        if not item_feasible:
            feasible = False
        
        availability.append({
            "item_name": item_name,
            "requested_quantity": quantity,
            "available_stock": current_stock,
            "feasible": item_feasible
        })
    
    return {
        "feasible": feasible,
        "availability": availability,
        "date": date
    }

def delivery_schedule_tool(items: list, date: str = None) -> dict:
    """Calculate delivery schedule for items."""
    if date is None:
        date = datetime.now().isoformat()
    
    max_delivery_days = 0
    delivery_details = []
    
    for item in items:
        quantity = item["quantity"]
        delivery_date = get_supplier_delivery_date(date, quantity)
        
        # Calculate days from today
        today = datetime.fromisoformat(date.split("T")[0])
        delivery_dt = datetime.fromisoformat(delivery_date)
        days = (delivery_dt - today).days
        
        max_delivery_days = max(max_delivery_days, days)
        delivery_details.append({
            "item_name": item["item_name"],
            "quantity": quantity,
            "delivery_date": delivery_date,
            "days_from_order": days
        })
    
    return {
        "estimated_delivery_date": delivery_details[0]["delivery_date"] if delivery_details else date,
        "max_delivery_days": max_delivery_days,
        "delivery_details": delivery_details
    }

def financial_report_tool(date: str = None) -> dict:
    """Generate comprehensive financial report."""
    if date is None:
        date = datetime.now().isoformat()
    
    return generate_financial_report(date)

def cash_balance_tool(date: str = None) -> float:
    """Get current cash balance."""
    if date is None:
        date = datetime.now().isoformat()
    
    return get_cash_balance(date)

# --- Agent tool wrappers for pydantic_ai ---
# Inventory tools (already present)
def inventory_check_tool_pydantic(item_name: str, date: str = None) -> dict:
    """Check current stock level for a specific item."""
    if date is None:
        date = datetime.now().isoformat()
    
    stock_info = get_stock_level(item_name, date)
    if stock_info.empty:
        return {"item_name": item_name, "current_stock": 0, "status": "out_of_stock"}
    
    current_stock = int(stock_info["current_stock"].iloc[0])
    
    # Get item details from paper_supplies
    item_details = next((item for item in paper_supplies if item["item_name"] == item_name), None)
    
    return {
        "item_name": item_name,
        "current_stock": current_stock,
        "status": "in_stock" if current_stock > 0 else "out_of_stock",
        "item_details": item_details
    }

def inventory_overview_tool_pydantic(date: str = None) -> dict:
    """Get overview of all inventory items."""
    if date is None:
        date = datetime.now().isoformat()
    
    inventory = get_all_inventory(date)
    
    # Categorize items by stock level
    low_stock = {}
    adequate_stock = {}
    
    for item_name, stock in inventory.items():
        stock = int(stock)
        if stock < 100:  # Threshold for low stock
            low_stock[item_name] = stock
        else:
            adequate_stock[item_name] = stock
    
    return {
        "total_items": int(len(inventory)),
        "low_stock_items": low_stock,
        "adequate_stock_items": adequate_stock,
        "date": date
    }

def reorder_assessment_tool_pydantic(item_name: str, quantity_needed: int, date: str = None) -> dict:
    result = reorder_assessment_tool(item_name, quantity_needed, date)
    # Cast all numbers to Python types
    for k in ["current_stock", "quantity_needed", "reorder_quantity"]:
        if k in result and result[k] is not None:
            result[k] = int(result[k])
    if "estimated_cost" in result and result["estimated_cost"] is not None:
        result["estimated_cost"] = float(result["estimated_cost"])
    return result

def process_reorder_tool_pydantic(item_name: str, quantity: int, date: str = None) -> dict:
    reorder_info = reorder_assessment_tool(item_name, quantity, date)
    for k in ["current_stock", "quantity_needed", "reorder_quantity"]:
        if k in reorder_info and reorder_info[k] is not None:
            reorder_info[k] = int(reorder_info[k])
    if "estimated_cost" in reorder_info and reorder_info["estimated_cost"] is not None:
        reorder_info["estimated_cost"] = float(reorder_info["estimated_cost"])
    if reorder_info["needs_reorder"]:
        transaction_id = transaction_tool(
            item_name,
            reorder_info["reorder_quantity"],
            reorder_info["estimated_cost"],
            "stock_orders"
        )
        return {"status": "reorder_processed", "transaction_id": int(transaction_id), "details": reorder_info}
    return {"status": "no_reorder_needed", "details": reorder_info}

# Quoting tools

def quote_history_tool_pydantic(search_terms: list) -> list:
    return quote_history_tool(search_terms)

def price_calculator_tool_pydantic(items: list, order_size: str = "medium") -> dict:
    return price_calculator_tool(items, order_size)

def quote_generator_tool_pydantic(customer_request: str, items: list, order_size: str) -> dict:
    return quote_generator_tool(customer_request, items, order_size)

# Sales tools

def sales_feasibility_tool_pydantic(items: list, date: str = None) -> dict:
    return sales_feasibility_tool(items, date)

def delivery_schedule_tool_pydantic(items: list, date: str = None) -> dict:
    return delivery_schedule_tool(items, date)

def process_sale_tool_pydantic(items: list, date: str = None) -> dict:
    total_revenue = 0
    transaction_ids = []
    for item in items:
        transaction_id = transaction_tool(
            item["item_name"],
            item["quantity"],
            item["final_price"],
            "sales",
            date
        )
        transaction_ids.append(transaction_id)
        total_revenue += item["final_price"]
    return {"status": "sale_processed", "total_revenue": total_revenue, "transaction_ids": transaction_ids}

# Financial tools

def financial_report_tool_pydantic(date: str = None) -> dict:
    return financial_report_tool(date)

def cash_balance_tool_pydantic(date: str = None) -> float:
    return cash_balance_tool(date)

# --- pydantic_ai.Agent instances ---

inventory_agent = Agent(
    openai_model,
    system_prompt="""
You are the Inventory Agent for Beaver's Choice Paper Company. Your job is to:
- Check stock levels for any item
- Assess reorder needs
- Generate inventory reports
- Manage stock operations
Use the provided tools to answer questions and perform actions related to inventory.
""",
    tools=[
        inventory_check_tool_pydantic,
        inventory_overview_tool_pydantic,
        reorder_assessment_tool_pydantic,
        process_reorder_tool_pydantic,
    ],
    retries=2
)

quoting_agent = Agent(
    openai_model,
    system_prompt="""
You are the Quoting Agent for Beaver's Choice Paper Company. Your job is to:
- Generate competitive quotes
- Apply bulk discounts
- Research historical pricing
- Create customer explanations
Use the provided tools to answer questions and perform actions related to quoting and pricing.
""",
    tools=[
        quote_history_tool_pydantic,
        price_calculator_tool_pydantic,
        quote_generator_tool_pydantic,
    ],
    retries=2
)

sales_agent = Agent(
    openai_model,
    system_prompt="""
You are the Sales Agent for Beaver's Choice Paper Company. Your job is to:
- Finalize sales transactions
- Check order feasibility
- Schedule deliveries
- Update inventory
Use the provided tools to answer questions and perform actions related to sales and delivery.
""",
    tools=[
        sales_feasibility_tool_pydantic,
        delivery_schedule_tool_pydantic,
        process_sale_tool_pydantic,
    ],
    retries=2
)

financial_agent = Agent(
    openai_model,
    system_prompt="""
You are the Financial Agent for Beaver's Choice Paper Company. Your job is to:
- Generate financial reports
- Monitor cash balance
- Provide financial insights
- Track profitability
Use the provided tools to answer questions and perform actions related to financials.
""",
    tools=[
        financial_report_tool_pydantic,
        cash_balance_tool_pydantic,
    ],
    retries=2
)

# --- Orchestrator logic ---

def parse_customer_request(request: str) -> dict:
    items = []
    patterns = [
        r'(\d+)\s+sheets?\s+of\s+([^,\n]+)',
        r'(\d+)\s+([^,\n]*paper[^,\n]*)',
        r'(\d+)\s+([^,\n]*cardstock[^,\n]*)',
        r'(\d+)\s+([^,\n]*envelope[^,\n]*)',
        r'(\d+)\s+([^,\n]*plate[^,\n]*)',
        r'(\d+)\s+([^,\n]*cup[^,\n]*)',
        r'(\d+)\s+([^,\n]*napkin[^,\n]*)',
        r'(\d+)\s+roll[s]?\s+of\s+([^,\n]+)',
        r'(\d+)\s+pack[s]?\s+of\s+([^,\n]+)',
        r'(\d+)\s+ream[s]?\s+of\s+([^,\n]+)'
    ]
    for pattern in patterns:
        matches = re.findall(pattern, request, re.IGNORECASE)
        for match in matches:
            try:
                quantity = int(match[0])
                item_description = match[1].strip()
                best_match = None
                best_score = 0
                for paper_item in paper_supplies:
                    item_name_words = paper_item["item_name"].lower().split()
                    description_words = item_description.lower().split()
                    score = len(set(item_name_words) & set(description_words))
                    if score > best_score:
                        best_score = score
                        best_match = paper_item["item_name"]
                if best_match and best_score > 0:
                    items.append({
                        "item_name": best_match,
                        "quantity": quantity,
                        "description": item_description
                    })
            except ValueError:
                continue
    total_items = sum(item["quantity"] for item in items)
    if total_items > 5000:
        order_size = "large"
    elif total_items > 1000:
        order_size = "medium"
    else:
        order_size = "small"
    return {"items": items, "order_size": order_size, "total_items": total_items}

# Main orchestrator function

def call_multi_agent_system(customer_request: str, request_date: str = None) -> str:
    parsed_request = parse_customer_request(customer_request)
    if not parsed_request["items"]:
        return "I apologize, but I couldn't identify specific paper products in your request. Please specify the items and quantities you need."
    
    # Extract date from request if provided
    if request_date is None:
        request_date = datetime.now().isoformat()
    
    # For now, use direct tool calls instead of OpenAI agents
    # (OpenAI agents are set up but need more complex prompt engineering to work properly)
    
    # Step 1: Inventory check
    inventory_status = []
    for item in parsed_request["items"]:
        # Use direct tool call instead of agent
        status = inventory_check_tool_pydantic(item["item_name"], request_date)
        inventory_status.append(status)
    
    # Step 2: Generate quote
    quote_info = quote_generator_tool(customer_request, parsed_request["items"], parsed_request["order_size"])
    
    # Step 3: Sales feasibility
    feasibility = sales_feasibility_tool(parsed_request["items"], request_date)
    
    # Step 4: Delivery schedule
    delivery_info = delivery_schedule_tool(parsed_request["items"], request_date)
    
    # Step 5: Response
    response = f"Thank you for your interest in Beaver's Choice Paper Company! "
    if feasibility.get("feasible", False):
        response += f"We can fulfill your order. "
        response += quote_info.get("quote_explanation", "")
        response += f" Estimated delivery: {delivery_info.get('estimated_delivery_date', 'TBD')}. "
        
        # Process sale
        total_revenue = 0
        transaction_ids = []
        for item in quote_info["items"]:
            transaction_id = transaction_tool(
                item["item_name"], 
                item["quantity"], 
                item["final_price"], 
                "sales",
                request_date
            )
            transaction_ids.append(transaction_id)
            total_revenue += item["final_price"]
        
        response += f"Order confirmed! Total: ${total_revenue:.2f}"
    else:
        response += "Unfortunately, we cannot fulfill your complete order due to insufficient inventory. "
        available_items = [item for item in feasibility.get("availability", []) if item.get("feasible")]
        if available_items:
            partial_items = []
            for item in available_items:
                matching_item = next((i for i in parsed_request["items"] if i["item_name"] == item["item_name"]), None)
                if matching_item:
                    partial_items.append(matching_item)
            if partial_items:
                partial_quote = quote_generator_tool(customer_request, partial_items, "small")
                response += f"We can offer a partial order: {partial_quote.get('quote_explanation', '')}"
                unavailable_items = [item for item in feasibility.get("availability", []) if not item.get("feasible")]
                if unavailable_items:
                    response += " We can arrange for the remaining items to be delivered once we receive new stock. "
                    for item in unavailable_items:
                        reorder_info = reorder_assessment_tool(item["item_name"], item["requested_quantity"], request_date)
                        if reorder_info["needs_reorder"]:
                            transaction_id = transaction_tool(
                                item["item_name"], 
                                reorder_info["reorder_quantity"], 
                                reorder_info["estimated_cost"], 
                                "stock_orders",
                                request_date
                            )
                            response += f"Expected restock of {item['item_name']}: {reorder_info['delivery_date']}. "
        else:
            response += "None of the requested items are currently available in sufficient quantities."
    return response

# Run your test scenarios by writing them here. Make sure to keep track of them.

def run_test_scenarios():
    
    print("Initializing Database...")
    init_database(db_engine)
    try:
        quote_requests_sample = pd.read_csv("quote_requests_sample.csv")
        quote_requests_sample["request_date"] = pd.to_datetime(
            quote_requests_sample["request_date"], format="%m/%d/%y", errors="coerce"
        )
        quote_requests_sample.dropna(subset=["request_date"], inplace=True)
        quote_requests_sample = quote_requests_sample.sort_values("request_date")
    except Exception as e:
        print(f"FATAL: Error loading test data: {e}")
        return

    quote_requests_sample = pd.read_csv("quote_requests_sample.csv")

    # Sort by date
    quote_requests_sample["request_date"] = pd.to_datetime(
        quote_requests_sample["request_date"]
    )
    quote_requests_sample = quote_requests_sample.sort_values("request_date")

    # Get initial state
    initial_date = quote_requests_sample["request_date"].min().strftime("%Y-%m-%d")
    report = generate_financial_report(initial_date)
    current_cash = report["cash_balance"]
    current_inventory = report["inventory_value"]

    ############
    ############
    ############
    # INITIALIZE YOUR MULTI AGENT SYSTEM HERE
    ############
    ############
    ############

    results = []
    for idx, row in quote_requests_sample.iterrows():
        request_date = row["request_date"].strftime("%Y-%m-%d")

        print(f"\n=== Request {idx+1} ===")
        print(f"Context: {row['job']} organizing {row['event']}")
        print(f"Request Date: {request_date}")
        print(f"Cash Balance: ${current_cash:.2f}")
        print(f"Inventory Value: ${current_inventory:.2f}")

        # Process request
        request_with_date = f"{row['request']} (Date of request: {request_date})"

        ############
        ############
        ############
        # USE YOUR MULTI AGENT SYSTEM TO HANDLE THE REQUEST
        ############
        ############
        ############

        response = call_multi_agent_system(request_with_date, request_date)

        # Update state
        report = generate_financial_report(request_date)
        current_cash = report["cash_balance"]
        current_inventory = report["inventory_value"]

        print(f"Response: {response}")
        print(f"Updated Cash: ${current_cash:.2f}")
        print(f"Updated Inventory: ${current_inventory:.2f}")

        results.append(
            {
                "request_id": idx + 1,
                "request_date": request_date,
                "cash_balance": current_cash,
                "inventory_value": current_inventory,
                "response": response,
            }
        )

        time.sleep(1)

    # Final report
    final_date = quote_requests_sample["request_date"].max().strftime("%Y-%m-%d")
    final_report = generate_financial_report(final_date)
    print("\n===== FINAL FINANCIAL REPORT =====")
    print(f"Final Cash: ${final_report['cash_balance']:.2f}")
    print(f"Final Inventory: ${final_report['inventory_value']:.2f}")

    # Save results
    pd.DataFrame(results).to_csv("test_results.csv", index=False)
    return results


if __name__ == "__main__":
    results = run_test_scenarios()