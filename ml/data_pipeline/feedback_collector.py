import pandas as pd
import os

def create_feedback_template():
    # Define the folder and file paths
    folder_path = "feedback"
    file_path = os.path.join(folder_path, "feedback_template.xlsx")

    # Create the folder if it doesn't exist
    os.makedirs(folder_path, exist_ok=True)

    # Define the columns for the feedback file
    columns = ["Job ID", "Variable Name", "Start Time", "Finish Time"]
    feedback_df = pd.DataFrame(columns=columns)

    # Save the template to the feedback folder
    feedback_df.to_excel(file_path, index=False)
    print(f"Feedback template created at {file_path}")

# Example usage
# create_feedback_template()

from datetime import datetime

def process_feedback(file_path, estimate_data):
    # Load the feedback file
    feedback_df = pd.read_excel(file_path)

    # Calculate actual durations
    feedback_df["Actual Duration (hours)"] = (
        pd.to_datetime(feedback_df["Finish Time"]) - pd.to_datetime(feedback_df["Start Time"])
    ).dt.total_seconds() / 3600

    # Compare actual durations with estimated durations
    feedback_df["Estimated Duration (hours)"] = feedback_df["Variable Name"].map(estimate_data)
    feedback_df["Difference (hours)"] = feedback_df["Actual Duration (hours)"] - feedback_df["Estimated Duration (hours)"]

    # Output feedback for analysis
    print(feedback_df)
    return feedback_df