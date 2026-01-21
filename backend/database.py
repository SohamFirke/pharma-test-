"""
Database utilities for CSV/SQLite operations.
Handles all data persistence for the pharmacy system.
"""

import csv
import os
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional
import pandas as pd

# Base paths
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
MEDICINE_MASTER_PATH = DATA_DIR / "medicine_master.csv"
ORDER_HISTORY_PATH = DATA_DIR / "order_history.csv"

# Ensure data directory exists
DATA_DIR.mkdir(exist_ok=True)


class Database:
    """Main database interface for pharmacy system."""
    
    @staticmethod
    def load_medicine_master() -> pd.DataFrame:
        """Load medicine master data from CSV."""
        if not MEDICINE_MASTER_PATH.exists():
            # Create empty dataframe with schema
            df = pd.DataFrame(columns=[
                'medicine_name', 'unit_type', 'stock_level', 'prescription_required'
            ])
            df.to_csv(MEDICINE_MASTER_PATH, index=False)
            return df
        
        df = pd.read_csv(MEDICINE_MASTER_PATH)
        # Convert types
        df['stock_level'] = df['stock_level'].astype(int)
        df['prescription_required'] = df['prescription_required'].astype(str).str.lower() == 'true'
        return df
    
    @staticmethod
    def load_order_history() -> pd.DataFrame:
        """Load order history from CSV."""
        if not ORDER_HISTORY_PATH.exists():
            df = pd.DataFrame(columns=[
                'user_id', 'medicine_name', 'quantity', 'dosage_per_day', 'purchase_date'
            ])
            df.to_csv(ORDER_HISTORY_PATH, index=False)
            return df
        
        df = pd.read_csv(ORDER_HISTORY_PATH)
        # Convert types
        df['quantity'] = df['quantity'].astype(int)
        df['dosage_per_day'] = df['dosage_per_day'].astype(int)
        df['purchase_date'] = pd.to_datetime(df['purchase_date'], format='ISO8601')
        return df
    
    @staticmethod
    def get_medicine(medicine_name: str) -> Optional[Dict]:
        """Get specific medicine details."""
        df = Database.load_medicine_master()
        # Case-insensitive search
        result = df[df['medicine_name'].str.lower() == medicine_name.lower()]
        if result.empty:
            return None
        
        medicine = result.iloc[0].to_dict()
        # Ensure proper types
        medicine['stock_level'] = int(medicine['stock_level'])
        medicine['prescription_required'] = bool(medicine['prescription_required'])
        return medicine
    
    @staticmethod
    def update_stock(medicine_name: str, quantity_change: int) -> bool:
        """
        Update stock level for a medicine.
        
        Args:
            medicine_name: Name of the medicine
            quantity_change: Negative number to deduct, positive to add
        
        Returns:
            True if update successful, False otherwise
        """
        df = Database.load_medicine_master()
        mask = df['medicine_name'].str.lower() == medicine_name.lower()
        
        if not mask.any():
            return False
        
        # Ensure stock_level is int before calculation
        current_stock = int(df.loc[mask, 'stock_level'].iloc[0])
        new_stock = current_stock + int(quantity_change)
        
        # Ensure stock doesn't go negative
        if new_stock < 0:
            return False
        
        df.loc[mask, 'stock_level'] = new_stock
        
        df.to_csv(MEDICINE_MASTER_PATH, index=False)
        return True
    
    @staticmethod
    def save_order(user_id: str, medicine_name: str, quantity: int, 
                   dosage_per_day: int, purchase_date: Optional[str] = None) -> str:
        """
        Save new order to order history.
        
        Returns:
            Order ID (timestamp-based)
        """
        if purchase_date is None:
            purchase_date = datetime.now().isoformat()
        
        df = Database.load_order_history()
        
        new_order = pd.DataFrame([{
            'user_id': user_id,
            'medicine_name': medicine_name,
            'quantity': quantity,
            'dosage_per_day': dosage_per_day,
            'purchase_date': purchase_date
        }])
        
        df = pd.concat([df, new_order], ignore_index=True)
        df.to_csv(ORDER_HISTORY_PATH, index=False)
        
        # Generate order ID
        order_id = f"ORD-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        return order_id
    
    @staticmethod
    def get_user_history(user_id: str) -> List[Dict]:
        """Get order history for a specific user."""
        df = Database.load_order_history()
        user_orders = df[df['user_id'] == user_id]
        
        # Convert to dict and ensure proper types
        result = user_orders.to_dict('records')
        for order in result:
            order['quantity'] = int(order['quantity'])
            order['dosage_per_day'] = int(order['dosage_per_day'])
        
        return result
    
    @staticmethod
    def get_user_medicine_history(user_id: str, medicine_name: str) -> List[Dict]:
        """Get order history for a specific user and medicine."""
        df = Database.load_order_history()
        result = df[
            (df['user_id'] == user_id) & 
            (df['medicine_name'].str.lower() == medicine_name.lower())
        ]
        
        # Convert to dict and ensure proper types
        records = result.to_dict('records')
        for order in records:
            order['quantity'] = int(order['quantity'])
            order['dosage_per_day'] = int(order['dosage_per_day'])
        
        return records
    
    @staticmethod
    def get_low_stock_medicines(threshold: int = 50) -> List[Dict]:
        """Get medicines with stock below threshold."""
        df = Database.load_medicine_master()
        low_stock = df[df['stock_level'] < threshold]
        return low_stock.to_dict('records')
    
    @staticmethod
    def search_medicine_fuzzy(query: str) -> List[str]:
        """
        Fuzzy search for medicine names.
        Returns list of matching medicine names.
        """
        df = Database.load_medicine_master()
        query_lower = query.lower()
        
        # Exact match
        exact = df[df['medicine_name'].str.lower() == query_lower]
        if not exact.empty:
            return [exact.iloc[0]['medicine_name']]
        
        # Partial match
        partial = df[df['medicine_name'].str.lower().str.contains(query_lower)]
        return partial['medicine_name'].tolist()
