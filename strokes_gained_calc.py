import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
import time
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

def load_data(round_file, distance_table_file):
    """
    Load and merge the round data and distance table.
    """
    # Load round data with error handling
    round_df = pd.read_csv(round_file, on_bad_lines='skip')  # This will skip problematic rows
    
    # Drop the unnecessary index column if it exists
    if 'Unnamed: 0' in round_df.columns:
        round_df = round_df.drop(columns=['Unnamed: 0'])
    
    # Load distance table
    distance_df = pd.read_csv(distance_table_file)
    
    # Merge the data based on course name and hole number
    merged_df = round_df.merge(distance_df, on=['course_name', 'hole_number'], how='left', suffixes=('_round', '_distance'))
    
    # Print column names to verify
    print("Available columns:", merged_df.columns.tolist())
    
    return merged_df

def assign_shot_numbers(df):
    """
    Assign sequential shot numbers for each player's hole.
    """
    df['shot'] = df.groupby(['player_name', 'round_id', 'hole_number']).cumcount() + 1
    return df

def determine_starting_distance(df):
    """
    Determine the correct starting distance based on par value.
    """
    df['starting_distance'] = df.apply(
        lambda row: row['yardage'] if row['par_distance'] in [4, 5] else row['approach_distance'], axis=1
    )
    
    # If starting distance is missing, leave it blank
    df['starting_distance'] = df['starting_distance'].apply(lambda x: '' if pd.isna(x) else x)
    
    return df

def get_strokes_gained(start_lie, start_distance, landing_lie, landing_distance):
    """
    Automate Golfity website interaction to retrieve strokes gained values.
    """
    # Convert lie descriptions to codes
    lie_codes = {
        'Tee': 't',
        'Fairway': 'f',
        'Rough': 'r',
        'Sand': 's',
        'Green': 'g'
    }
    
    # Debug print
    print(f"Attempting calculation with: Start lie: {start_lie}, Start distance: {start_distance}, Landing lie: {landing_lie}, Landing distance: {landing_distance}")
    
    driver = webdriver.Chrome()
    try:
        driver.get("https://www.golfity.com/strokes-gained-calculator")
        wait = WebDriverWait(driver, 10)  # Wait up to 10 seconds
        
        # Wait for and select starting location lie
        start_lie_dropdown = wait.until(
            EC.presence_of_element_located((By.ID, "start_lie"))
        )
        start_lie_code = lie_codes.get(start_lie, 'f')  # default to fairway if unknown
        start_lie_dropdown.send_keys(start_lie_code)
        
        # Input starting distance
        start_distance_input = wait.until(
            EC.presence_of_element_located((By.ID, "start_distance"))
        )
        start_distance_input.send_keys(str(start_distance))
        
        # Select landing location lie
        landing_lie_dropdown = wait.until(
            EC.presence_of_element_located((By.ID, "end_lie"))
        )
        landing_lie_code = lie_codes.get(landing_lie, 'f')  # default to fairway if unknown
        landing_lie_dropdown.send_keys(landing_lie_code)
        
        # Input landing distance
        landing_distance_input = wait.until(
            EC.presence_of_element_located((By.ID, "end_distance"))
        )
        landing_distance_input.send_keys(str(landing_distance))
        landing_distance_input.send_keys(Keys.RETURN)
        
        # Wait for and retrieve strokes gained value
        strokes_gained_element = wait.until(
            EC.presence_of_element_located((By.ID, "strokes-gained-result"))
        )
        return strokes_gained_element.text
        
    except TimeoutException:
        print(f"Timeout waiting for elements: {start_lie} ({start_lie_code}), {start_distance}, {landing_lie} ({landing_lie_code}), {landing_distance}")
        return ''
    except Exception as e:
        print(f"Error: {e}")
        return ''
    finally:
        driver.quit()

def calculate_strokes_gained(df):
    """
    Loop through shots and retrieve strokes gained for each.
    """
    def process_distance(distance):
        try:
            return int(float(distance)) if pd.notna(distance) else ''
        except (ValueError, TypeError):
            return ''

    def determine_start_lie(row):
        # First shot on any hole is from the tee
        if row['shot'] == 1:
            return 'Tee'
        # For other shots, use the previous shot's landing location
        return row['tee_ball_location']

    df['strokes_gained'] = df.apply(
        lambda row: get_strokes_gained(
            # Start lie - always Tee for first shot of hole
            determine_start_lie(row),
            # Start distance
            process_distance(row['starting_distance']),
            # Landing lie
            row['tee_ball_location'],
            # Landing distance
            process_distance(row['approach_distance'])
        ) if pd.notna(row['starting_distance']) and pd.notna(row['approach_distance']) else '', axis=1
    )
    return df

# Load data
round_file = "Joe_Pagdin_Lake_Las_Vegas_02_24_2025.csv"  # Placeholder for uploaded file
course_table_file = "las_vegas_starting_distance_table.csv"  # Placeholder for uploaded table
df = load_data(round_file, course_table_file)

# Assign shot numbers
df = assign_shot_numbers(df)

# Determine starting distance
df = determine_starting_distance(df)

# Calculate strokes gained
df = calculate_strokes_gained(df)

# Show processed data
print(df.head())

# Create output filename using player name and date
player_name = df['player_name'].iloc[0].replace(" ", "_")
date = df['start_date'].iloc[0]
output_file = f"{player_name}_{date}_processed.csv"

# Save to CSV
df.to_csv(output_file, index=False)
print(f"\nData saved to {output_file}")




