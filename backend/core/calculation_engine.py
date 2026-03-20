"""PackagePro Estimator - Core Functions Module

This module provides the core functionality for the PackagePro Screen Print
packaging cost estimator system. It handles complex pricing calculations with
80+ interdependent variables, database operations, and invoice generation.

Key Features:
    - Dynamic calculation engine for packaging cost estimation
    - SQLite database integration for estimate persistence
    - PDF invoice generation with company branding
    - Support for customer inquiries and custom variables
    - Historical estimate retrieval and analysis

Author: [Your Name]
Company: PackagePro & Buckingham Screen Print
Date: 2024
"""

import pandas as pd
import numpy as np
import logging
import os
import sqlite3
from datetime import datetime

# Configure logging for better error tracking
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def estimate_total(df):
    """Calculate the final total cost for an estimate.
    
    Extracts the total cost from the 'QUANTITY INCLUDING OVERS (number)' row,
    which represents the final calculated estimate after all multipliers and
    equations have been applied.
    
    Args:
        df (pd.DataFrame): DataFrame containing all pricing variables and calculations
        
    Returns:
        float: Total cost in GBP, or None if calculation fails
    """
    try:
        total_row = "QUANTITY INCLUDING OVERS (number)"
        total_cost = df.loc[total_row, 'TOTAL (£)']
        
        return total_cost

    except Exception as e:
        logging.error(f"Error calculating total: {e}")
        return None

def update_totals(df):
    """Apply total cost equations to calculate pricing for each line item.
    
    Iterates through the DataFrame from bottom to top (reverse order) to ensure
    dependent calculations are performed in the correct sequence. Uses eval()
    to execute dynamic Python equations stored in the DataFrame.
    
    Args:
        df (pd.DataFrame): DataFrame with 'Equation for TOTAL (£)' column
        
    Returns:
        pd.DataFrame: Updated DataFrame with calculated totals
    """
    for index, row in df.iloc[::-1].iterrows():  # Iterate from bottom to top
            try:
                # Use eval() to calculate the new value of the Total
                new_value = eval(row["Equation for TOTAL (£)"])
                df.at[index, "TOTAL (£)"] = new_value
            except ZeroDivisionError:
                df.at[index, "TOTAL (£)"] = 0
            except Exception as e:
                print(f"Error applying totals equation for {index}: {e}. Equation: {row['Equation for TOTAL (£)']}")
    return df


def update_multiplier(df):
    """Update multiplier values based on their equations.
    
    Only updates multipliers that have not been manually set by customer inquiries
    (where 'Updated Multiplier' = 0). This allows customer-specified values to
    take precedence over formula calculations.
    
    Args:
        df (pd.DataFrame): DataFrame with 'Equation for Multiplier' column
        
    Returns:
        pd.DataFrame: Updated DataFrame with recalculated multipliers
    """
    for index, row in df.iterrows():
        # Check if this multiplier is updated by a customer inquiry
        if row['Updated Multiplier'] == 0:
            try:
                # Use eval() to calculate the new value of the Multiplier
                new_value = eval(row["Equation for Multiplier"])
                df.at[index, "Multiplier"] = new_value
            except ZeroDivisionError:
                df.at[index, "Multiplier"] = 0
            except Exception as e:
                print(f"Error applying multipliers equation for {index}: {e}")      
        else:
            continue
    return df

def update_enquiry(inquiry_updates, df):
    """Apply customer inquiry updates to the pricing model.
    
    Updates specific variables based on customer requirements and marks them
    as manually updated to prevent formula overwriting.
    
    Args:
        inquiry_updates (dict): Dictionary mapping variable names to new values
        df (pd.DataFrame): DataFrame to update
        
    Returns:
        pd.DataFrame: Updated DataFrame with inquiry changes applied
    """
    for key, value in inquiry_updates.items():
        df.loc[key, "Multiplier"] = value
        df.loc[key, "Updated Multiplier"] = 1
    print("Enquiry Updated")
    return df

def load_data():
    """Load the base pricing model from CSV file.
    
    Loads the preprocessed variables CSV file containing all pricing rules,
    equations, and base multipliers for the packaging cost calculator.
    
    Returns:
        pd.DataFrame: Indexed DataFrame with pricing model structure
    """
    # Load DataFrame from processed variables file
    df = pd.read_csv('/Users/q/PythonScript/Python/DataAnalysis/PackagePro/Variables_EQ_GPT.csv')
    # Set the first column as index for variable lookup
    df.set_index(df.columns[0], inplace=True)  
    # Set Index and column names for clarity
    df.columns.name = 'Variable Name'
    df.index.name = 'Feature'
    return df

def update_dataframe(inquiry_updates, df):
    """Master function to process estimate calculations.
    
    Orchestrates the complete calculation workflow:
    1. Loads base pricing model
    2. Applies customer inquiry updates
    3. Recalculates dependent multipliers
    4. Updates all cost totals
    5. Calculates final estimate
    
    Args:
        inquiry_updates (dict): Customer-specific variable updates
        df (pd.DataFrame): Initial DataFrame (reloaded from source)
        
    Returns:
        tuple: (final_estimate: float, updated_df: pd.DataFrame)
    """
    print("Starting update_dataframe...")
    
    # Step 0: Load DataFrame from source
    print("0. Loading DataFrame")
    df = load_data()


    # Step 1: Update the inquiry multipliers
    print("1. Updating inquiry multipliers...")
    df = update_enquiry(inquiry_updates, df)
    print("Inquiry update complete.")
    # Filter and print rows with indices matching the keys in `inquiry_updates`
    print("The following items where updated: ")
    keys = inquiry_updates.keys()
    filtered_df = df.loc[keys, ["Multiplier"]]  # Select rows with indices in `keys`
    print(filtered_df)


    # Step 2: Update multipliers based on their equations
    print("2. Updating multipliers...")
    df = update_multiplier(df)
    print("Multiplier update complete.")
    
    '''# Print items that have not been updated
    print("The following items where not updated: ")
    filtered_df = df[df["Updated Multiplier"] == 0]["Multiplier"]
    print(filtered_df)'''


    # Step 3: Update totals
    print("3. Updating totals...")
    df = update_totals(df)
    print("Totals update complete.")


    # Step 4: Estimate the final cost
    print("4. Estimating final total...")
    final_estimate = estimate_total(df)
    print(f"Final estimate: £{final_estimate}")

    return final_estimate, df
    

def save_entire_database_with_metadata(df, company_name, job_description, estimate_number):
    """Save complete estimate data to SQLite database.
    
    Stores the entire calculation DataFrame along with metadata for
    historical tracking and retrieval.
    
    Args:
        df (pd.DataFrame): Complete calculation DataFrame
        company_name (str): Customer company name
        job_description (str): Description of packaging job
        estimate_number (int): Unique estimate identifier
    """
    # Connect to the SQLite database
    conn = sqlite3.connect('estimates.sql')
    cursor = conn.cursor()

    # Create a table for estimates if it doesn't exist
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS detailed_estimates (
            estimate_number INTEGER PRIMARY KEY,
            company_name TEXT,
            job_description TEXT,
            estimate_data TEXT
        )
    ''')

    # Reset the index so variable names are part of the DataFrame
    df_reset = df.reset_index()

    # Convert DataFrame to a string to store in the database
    estimate_data = df_reset.to_csv(index=False)

    # Insert or update the estimate data with metadata
    cursor.execute('''
        INSERT INTO detailed_estimates (estimate_number, company_name, job_description, estimate_data)
        VALUES (?, ?, ?, ?)
    ''', (estimate_number, company_name, job_description, estimate_data))

    conn.commit()
    conn.close()
    print(f"Entire database saved with metadata for estimate {estimate_number} in estimates.sql.")
    
    
def save_estimate_metadata(company_name, job_description, estimate_number, final_estimate):
    """Save estimate metadata for quick lookups and reporting.
    
    Creates a lightweight metadata record with key information for
    estimate tracking and business analytics.
    
    Args:
        company_name (str): Customer company name
        job_description (str): Description of packaging job
        estimate_number (int): Unique estimate identifier
        final_estimate (float): Total cost in GBP
    """
    # Connect to the SQLite database
    conn = sqlite3.connect('estimates.sql')
    cursor = conn.cursor()

    # Create a table for metadata if it doesn't exist
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS estimate_metadata (
            estimate_number INTEGER PRIMARY KEY,
            company_name TEXT,
            job_description TEXT,
            date TEXT,
            time TEXT,
            final_estimate REAL
        )
    ''')

    # Get today's date and time
    from datetime import datetime
    date = datetime.now().strftime('%Y-%m-%d')
    time = datetime.now().strftime('%H:%M:%S')

    # Insert metadata
    cursor.execute('''
        INSERT INTO estimate_metadata (estimate_number, company_name, job_description, date, time, final_estimate)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (estimate_number, company_name, job_description, date, time, final_estimate))

    conn.commit()
    conn.close()
    print(f"Metadata saved for estimate {estimate_number} in estimates.sql, including final estimate of £{final_estimate}.")
    



def create_invoice(company_name, job_description, final_estimate, estimate_number):
    """Generate a professional PDF invoice for the estimate.
    
    Creates a branded PDF invoice with company details, customer information,
    and final cost estimate. Invoices are saved to the 'invoices' directory.
    
    Args:
        company_name (str): Customer company name
        job_description (str): Description of packaging job
        final_estimate (float): Total cost in GBP
        estimate_number (int): Unique estimate identifier
    """
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas
    import os
    from datetime import datetime
    # PackagePro company details for invoice header
    ksp_name = "PackagePro & Buckingham Screen Print"
    ksp_address = """
    3 Riverside
    Tramway Industrial Estate
    Banbury
    Oxfordshire
    OX16 5TU
    """

    # Define the folder where invoices will be saved
    folder_path = "invoices"
    os.makedirs(folder_path, exist_ok=True)

    # Define the file path for the invoice
    file_path = os.path.join(folder_path, f"Invoice_{estimate_number}.pdf")

    # Create a new PDF
    pdf = canvas.Canvas(file_path, pagesize=A4)
    width, height = A4

    # Add PackagePro details
    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(50, height - 50, ksp_name)

    pdf.setFont("Helvetica", 12)
    text = pdf.beginText(50, height - 70)
    for line in ksp_address.splitlines():
        text.textLine(line)
    pdf.drawText(text)

    # Add invoice title
    pdf.setFont("Helvetica-Bold", 14)
    pdf.drawString(50, height - 150, "INVOICE")

    # Add invoice metadata
    pdf.setFont("Helvetica", 12)
    pdf.drawString(50, height - 180, f"Estimate Number: {estimate_number}")
    pdf.drawString(50, height - 200, f"Date: {datetime.now().strftime('%Y-%m-%d')}")
    pdf.drawString(50, height - 220, f"Time: {datetime.now().strftime('%H:%M:%S')}")

    # Add customer details
    pdf.drawString(50, height - 260, f"Customer: {company_name}")
    pdf.drawString(50, height - 280, f"Job Description: {job_description}")

    # Add estimate total
    pdf.setFont("Helvetica-Bold", 14)
    pdf.drawString(50, height - 320, f"Final Estimate: £{final_estimate:.2f}")

    # Footer note
    pdf.setFont("Helvetica-Oblique", 10)
    pdf.drawString(50, 50, "Thank you for your business!")

    # Save the PDF
    pdf.save()

    print(f"Invoice {estimate_number} created at {file_path}.")
    
    
    
def get_next_estimate_number():
    """Generate the next sequential estimate number.
    
    Queries the database for the highest estimate number and increments it.
    Starts at 1 if no previous estimates exist.
    
    Returns:
        int: Next available estimate number
    """
    # Connect to the SQLite database
    conn = sqlite3.connect('estimates.sql')
    cursor = conn.cursor()

    # Query the maximum estimate number
    cursor.execute('SELECT MAX(estimate_number) FROM estimate_metadata')
    result = cursor.fetchone()

    conn.close()

    # If there are no records, start with 1; otherwise, increment the max
    return (result[0] + 1) if result[0] else 1



def retrieve_estimate(estimate_number):
    import sqlite3
    import pandas as pd
    from io import StringIO

    # Connect to the database
    conn = sqlite3.connect('estimates.sql')
    cursor = conn.cursor()

    # Fetch the estimate data and metadata
    cursor.execute(
        "SELECT estimate_data, company_name, job_description, date, time FROM detailed_estimates WHERE estimate_number = ?",
        (estimate_number,)
    )
    result = cursor.fetchone()
    conn.close()

    if result:
        # Unpack result
        estimate_data_csv, company_name, job_description, date, time = result

        # Convert the stored CSV-like string back into a DataFrame
        df = pd.read_csv(StringIO(estimate_data_csv))
        df.set_index("Feature", inplace=True)

        # Return variable data and metadata
        return df, {
            "company_name": company_name,
            "job_description": job_description,
            "date": date,
            "time": time
        }
    else:
        raise ValueError("Estimate not found.")
    

def retrieve_estimate_data(estimate_number):
    """Retrieve full estimate calculation data from database.
    
    Loads the complete DataFrame for a specific estimate, allowing
    review of all variables and calculations used.
    
    Args:
        estimate_number (int): Estimate identifier to retrieve
        
    Returns:
        pd.DataFrame: Complete estimate DataFrame
        
    Raises:
        ValueError: If estimate number not found
    """
    import sqlite3
    import pandas as pd
    from io import StringIO

    # Connect to the database
    conn = sqlite3.connect('estimates.sql')
    cursor = conn.cursor()

    # Fetch the estimate data
    cursor.execute(
        "SELECT estimate_data FROM detailed_estimates WHERE estimate_number = ?",
        (estimate_number,)
    )
    result = cursor.fetchone()
    conn.close()

    if result:
        # Convert the stored CSV-like string back into a DataFrame
        estimate_data_csv = result[0]  # Extract CSV string
        df = pd.read_csv(StringIO(estimate_data_csv))
        df.set_index("Feature", inplace=True)  # Ensure correct index
        print("Retrieved Estimate Data:")  # Debugging output
        print(df)  # Print the entire DataFrame to confirm structure
        return df
    else:
        raise ValueError("Estimate not found.")
    
def retrieve_estimate_meta(estimate_number):
    """Retrieve estimate metadata for display.
    
    Loads summary information for an estimate including company details,
    date/time, and final cost.
    
    Args:
        estimate_number (int): Estimate identifier to retrieve
        
    Returns:
        dict: Metadata dictionary with keys: company_name, job_description,
              date, time, final_estimate
              
    Raises:
        ValueError: If estimate number not found
    """
    import sqlite3

    # Connect to the database
    conn = sqlite3.connect('estimates.sql')
    cursor = conn.cursor()

    # Fetch the estimate metadata
    cursor.execute(
        "SELECT company_name, job_description, date, time, final_estimate FROM estimate_metadata WHERE estimate_number = ?",
        (estimate_number,)
    )
    result = cursor.fetchone()
    conn.close()

    if result:
        # Unpack the metadata into a dictionary
        metadata = {
            "company_name": result[0],
            "job_description": result[1],
            "date": result[2],
            "time": result[3],
            "final_estimate": result[4]
        }
        return metadata
    else:
        raise ValueError("Estimate metadata not found.")
    

def confirm_sale(estimate_number):
    """Convert an estimate to a confirmed sale.
    
    Moves estimate data to the Sales table for tracking purposes,
    marking it as an accepted quote with sale date/time.
    
    Args:
        estimate_number (int): Estimate to convert to sale
        
    Raises:
        ValueError: If estimate number not found
    """
    import sqlite3
    from datetime import datetime
    conn = sqlite3.connect('estimates.sql')
    cursor = conn.cursor()

    # Fetch the estimate data
    cursor.execute("SELECT * FROM detailed_estimates WHERE estimate_number = ?", (estimate_number,))
    estimate = cursor.fetchone()
    if not estimate:
        conn.close()
        raise ValueError("Estimate not found.")

    # Create the Sales table if it doesn't exist
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Sales (
            estimate_number INTEGER PRIMARY KEY,
            company_name TEXT,
            job_description TEXT,
            estimate_data TEXT
        )
    ''')

    # Create the Sales Metadata table if it doesn't exist
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Sales_Metadata (
            sale_id INTEGER PRIMARY KEY AUTOINCREMENT,
            estimate_number INTEGER,
            company_name TEXT,
            job_description TEXT,
            sale_date TEXT,
            sale_time TEXT,
            FOREIGN KEY (estimate_number) REFERENCES Sales (estimate_number)
        )
    ''')

    # Insert the estimate data into the Sales table
    cursor.execute('''
        INSERT INTO Sales (estimate_number, company_name, job_description, estimate_data)
        SELECT estimate_number, company_name, job_description, estimate_data
        FROM detailed_estimates
        WHERE estimate_number = ?
    ''', (estimate_number,))

    # Insert metadata into the Sales Metadata table
    sale_date = datetime.now().strftime('%Y-%m-%d')
    sale_time = datetime.now().strftime('%H:%M:%S')
    cursor.execute('''
        INSERT INTO Sales_Metadata (estimate_number, company_name, job_description, sale_date, sale_time)
        SELECT estimate_number, company_name, job_description, ?, ?
        FROM detailed_estimates
        WHERE estimate_number = ?
    ''', (sale_date, sale_time, estimate_number))

    # Commit changes and close connection
    conn.commit()
    conn.close()

    print(f"Estimate #{estimate_number} confirmed as a sale.")
    

def get_most_recent_estimate_number():
    """Fetch the most recent estimate number from the database.
    
    Returns:
        int: Most recent estimate number, or None if no estimates exist
    """
    import sqlite3
    conn = sqlite3.connect('estimates.sql')
    cursor = conn.cursor()
    cursor.execute("SELECT MAX(estimate_number) FROM detailed_estimates")
    result = cursor.fetchone()
    conn.close()
    return result[0] if result[0] else None


def generate_estimate(company_name, job_description, estimate_number, inquiry_updates):
    """Main function to generate a complete estimate.
    
    Orchestrates the entire estimate generation process:
    - Updates pricing model with customer requirements
    - Calculates final cost
    - Saves to database
    - Generates PDF invoice
    
    Args:
        company_name (str): Customer company name
        job_description (str): Description of packaging job
        estimate_number (int): Unique estimate identifier
        inquiry_updates (dict): Customer-specific variable updates
    """
    final_estimate, updated_df = update_dataframe(inquiry_updates, df)
    save_entire_database_with_metadata(updated_df, company_name, job_description, estimate_number)
    save_estimate_metadata(company_name, job_description, estimate_number, final_estimate)
    create_invoice(company_name, job_description, final_estimate, estimate_number)
    
        
        
# Example of setting up new inquiry
inquiry_updates ={ 
    "QUANTITY REQUIRED BY CUSTOMER (number)": 15000,
    "MECHANISM (number)": 0.17,
    "MITRE CORNERS OF OUTER SHEET 40mm (hours)": 0.033333333,
    "FLAT SIZE Length (mm)": 565,
    "FLAT SIZE Width (mm)": 165
}

df = load_data()

# Set display options to prevent truncation
pd.set_option('display.max_rows', None)       # Display all rows
pd.set_option('display.max_columns', None)    # Display all columns
pd.set_option('display.width', None)          # Set to None for unlimited width
pd.set_option('display.max_colwidth', None)   # Set to None to show full content of each cell

# Filter and print rows that contain "Dutch"
#print(df[df.apply(lambda row: row.astype(str).str.contains('QUANTI', case=False).any(), axis=1)])

# Reset options to default after printing (optional)
pd.reset_option('display.max_rows')
pd.reset_option('display.max_columns')
pd.reset_option('display.width')
pd.reset_option('display.max_colwidth')

# Now run the update process, respecting the updated multipliers
# Test Data
'''final_estimate, df = update_dataframe(inquiry_updates, df)

company_name = 'test_company'
job_description = 'test with 15000 items'
estimate_number = get_next_estimate_number()
generate_estimate(company_name, job_description, estimate_number, inquiry_updates)

df.to_csv('/Users/q/Desktop/TEST.csv')
'''
'''
for viewing the database in command line

sqlite3 estimates.sql
.tables  # List all tables
SELECT * FROM detailed_estimates;  # Check the contents of the table
'''
