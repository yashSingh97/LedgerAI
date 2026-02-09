from core.state import AgentState
import pickle 
import sqlite3
import pandas as pd 
from dotenv import load_dotenv 
import os 

load_dotenv() 


def prediction_savings_action(state: AgentState) -> AgentState:
    """
    Prediction Agent:
    - Reads categories requested by user
    - Loads RF model and fetches transaction data from SQLite
    - Computes ML-based next-month savings predictions
    - Updates memory
    - Appends results for responder
    """
    print("\n===== Prediction Agent Node =====")
    current_task = state.get("current_task", {})
    entities = current_task.get("entities", {})
    categories_requested = entities.get("categories")
    
    print(f"[Prediction Agent] Current task: {current_task}")
    
    # All available categories
    all_categories = [
        "groceries", "transport", "eating_out", "entertainment",
        "utilities", "healthcare", "education", "miscellaneous"
    ]

    # Normalize categories list
    if categories_requested == "all":
        categories = all_categories
    else:
        categories = [c.lower() for c in categories_requested if c.lower() in all_categories]
    
    print(f"[Prediction Agent] Final category list: {categories}")
    
    # Load the RF model
    try:
        with open(os.getenv("PREDICTION_MODEL_PATH"), 'rb') as file:
            model_package = pickle.load(file)
            rf_model = model_package['model']
            metadata = model_package['metadata']
        print("[Prediction Agent] Model loaded successfully")
    except Exception as e:
        print(f"[Prediction Agent] Error loading model: {e}")
        return {
            "results": state.get("results", []) + [{
                "type": "predict_savings",
                "error": "Failed to load prediction model"
            }],
            "should_continue": True
        }
    
    # Fetch category-wise spending from SQLite
    try:
        conn = sqlite3.connect('finance.db')
        cursor = conn.cursor()
        
        # Query to get category-wise total spending
        query = """
            SELECT 
                category,
                SUM(amount) as total_spending
            FROM transactions
            GROUP BY category
        """
        
        cursor.execute(query)
        results = cursor.fetchall()
        conn.close()
        
        # Create spending dictionary with proper capitalization for model
        spending_data = {}
        category_map = {
            "groceries": "Groceries",
            "transport": "Transport",
            "eating_out": "Eating_Out",
            "entertainment": "Entertainment",
            "utilities": "Utilities",
            "healthcare": "Healthcare",
            "education": "Education",
            "miscellaneous": "Miscellaneous"
        }
        
        # Initialize all categories with 0
        for cat in all_categories:
            spending_data[category_map[cat]] = 0.0
        
        # Fill in actual spending data
        for row in results:
            category_lower = row[0].lower()
            if category_lower in category_map:
                spending_data[category_map[category_lower]] = float(row[1])
        
        print(f"[Prediction Agent] Spending data: {spending_data}")
        
    except Exception as e:
        print(f"[Prediction Agent] Error fetching transaction data: {e}")
        spending_data = {
            "Groceries": 0.0, "Transport": 0.0, "Eating_Out": 0.0,
            "Entertainment": 0.0, "Utilities": 0.0, "Healthcare": 0.0,
            "Education": 0.0, "Miscellaneous": 0.0
        }
    
    # Set default values for other features
    default_features = {
        'Income': 20000.0,
        'Age': 30.0,
        'Dependents': 1.0,
        'Rent': 20000.0,
        'Loan_Repayment': 5000.0,
        'Insurance': 2000.0,
        'Desired_Savings_Percentage': 20.0,
        'Desired_Savings': 10000.0,
        'Disposable_Income': 33000.0,
        'Savings_Rate': 20.0,
        'Occupation_Professional': True,
        'Occupation_Retired': False,
        'Occupation_Self Employed': False,
        'Occupation_Student': False,
        'Occupation_Unknown': False,
        'City_Tier_TIER_1': True,
        'City_Tier_TIER_2': False,
        'City_Tier_TIER_3': False,
        'City_Tier_UNKNOWN': False
    }
    
    # Merge spending data with defaults
    input_features = {**default_features, **spending_data}
    
    # Create DataFrame with correct feature order
    feature_names = metadata['feature_names']
    input_df = pd.DataFrame([input_features], columns=feature_names)
    
    print(f"[Prediction Agent] Input features shape: {input_df.shape}")
    
    # Make predictions
    try:
        predictions_array = rf_model.predict(input_df)[0]
        target_names = metadata['target_names']
        
        # Map all predictions from model
        all_predictions = {}
        prediction_map = {
            "groceries": "Potential_Savings_Groceries",
            "transport": "Potential_Savings_Transport",
            "eating_out": "Potential_Savings_Eating_Out",
            "entertainment": "Potential_Savings_Entertainment",
            "utilities": "Potential_Savings_Utilities",
            "healthcare": "Potential_Savings_Healthcare",
            "education": "Potential_Savings_Education",
            "miscellaneous": "Potential_Savings_Miscellaneous"
        }
        
        # Extract ALL predictions from model
        for cat, target_name in prediction_map.items():
            if target_name in target_names:
                idx = target_names.index(target_name)
                all_predictions[cat] = round(float(predictions_array[idx]), 2)
        
        # Filter to only requested categories
        category_predictions = {
            cat: all_predictions[cat] 
            for cat in categories 
            if cat in all_predictions
        }
        
        print(f"[Prediction Agent] All predictions: {all_predictions}")
        print(f"[Prediction Agent] Filtered predictions for requested categories: {category_predictions}")
        
    except Exception as e:
        print(f"[Prediction Agent] Error making predictions: {e}")
        category_predictions = {cat: 0.0 for cat in categories}
    
    # Add result for responder
    result_entry = {
        "type": "predict_savings",
        "categories": categories,
        "predictions": category_predictions,
        "type_of_data": "this is prediction done for SAVINGS for NEXT MONTH, not how much user NEED"
    }
    updated_results = state.get("results", []) + [result_entry]
    print(f"[Prediction Agent] Result entry: {result_entry}")
    
    return {
        "results": updated_results,
        "should_continue": True
    }