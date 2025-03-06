import pandas as pd
import streamlit as st

def load_data(player_data_path, course_data_path):
    """Load player and course data from CSV files"""
    try:
        player_df = pd.read_csv(player_data_path)
        course_df = pd.read_csv(course_data_path)
        return player_df, course_df
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return None, None

def create_analysis_df(player_df, course_df):
    """Create a new DataFrame combining data from player and course DataFrames"""
    # Merge the dataframes on course_name and hole_number
    merged_df = pd.merge(
        player_df,
        course_df,
        on=['course_name', 'hole_number'],
        how='left',
        suffixes=('', '_course')
    )
    
    # Filter to include only the specified columns
    columns_to_keep = [
        'player_name', 'tournament_name', 'start_date', 'course_name', 'round_id', 
        'hole_number', 'gir', 'par', 'sand', 'score', 'putts', 'in_position', 
        'tee_ball_location', 'approach_distance', 'putt_one_distance', 
        'putt_two_distance', 'putt_three_distance', 'putt_four_distance', 
        'putt_five_distance', 'second_shot', 'gir_of_third', 'lay_up_location', 
        'go_for_location', 'yardage'
    ]
    
    # Only keep columns that exist in the merged DataFrame
    available_columns = [col for col in columns_to_keep if col in merged_df.columns]
    filtered_df = merged_df[available_columns]
    
    return filtered_df

def create_shot_by_shot_df(filtered_df):
    """
    Expand the DataFrame to create one row per shot based on the score column
    """
    # Create an empty list to store the expanded rows
    expanded_rows = []
    
    # Iterate through each row in the filtered DataFrame
    for _, row in filtered_df.iterrows():
        score = row['score']
        
        # Create a row for each shot
        for shot_number in range(1, int(score) + 1):
            # Create a copy of the original row
            shot_row = row.copy()
            
            # Add a shot number column
            shot_row['shot_number'] = shot_number
            
            # Determine starting location lie and distance based on shot number
            if shot_number == 1:
                # First shot is from the tee
                shot_row['starting_location_lie'] = 'tee'
                
                # For par 3 holes, use approach_distance instead of yardage
                if row['par'] == 3 and 'approach_distance' in row and pd.notna(row['approach_distance']):
                    shot_row['starting_location_distance'] = row['approach_distance']
                else:
                    shot_row['starting_location_distance'] = row['yardage']
            elif shot_number == 2:
                # Second shot location depends on tee shot
                if row['tee_ball_location'] is not None and pd.notna(row['tee_ball_location']):
                    shot_row['starting_location_lie'] = row['tee_ball_location']
                else:
                    shot_row['starting_location_lie'] = 'unknown'
                
                # Use approach distance if available for second shot
                if 'approach_distance' in row and pd.notna(row['approach_distance']):
                    shot_row['starting_location_distance'] = row['approach_distance']
                else:
                    shot_row['starting_location_distance'] = None
            elif shot_number > row['putts'] + 1:
                # Shots before putting (approach or around green)
                shot_row['starting_location_lie'] = 'approach'
                shot_row['starting_location_distance'] = None
            else:
                # Putting
                putt_number = shot_number - (score - row['putts'])
                putt_distance_col = f'putt_{putt_number}_distance'
                
                shot_row['starting_location_lie'] = 'green'
                if putt_distance_col in row and pd.notna(row[putt_distance_col]):
                    shot_row['starting_location_distance'] = row[putt_distance_col]
                else:
                    shot_row['starting_location_distance'] = None
            
            # Add the row to our list
            expanded_rows.append(shot_row)
    
    # Create a new DataFrame from the expanded rows
    shot_by_shot_df = pd.DataFrame(expanded_rows)
    
    return shot_by_shot_df

def run_streamlit_app():
    """Run the Streamlit app"""
    st.title("Golf Performance Analysis")
    
    # File uploaders
    player_data = st.file_uploader("Upload player data CSV", type="csv")
    course_data = st.file_uploader("Upload course data CSV", type="csv")
    
    if player_data is not None and course_data is not None:
        player_df, course_df = load_data(player_data, course_data)
        
        if player_df is not None and course_df is not None:
            st.success("Data loaded successfully!")
            
            # Display raw data
            st.subheader("Player Data Preview")
            st.dataframe(player_df.head())
            
            st.subheader("Course Data Preview")
            st.dataframe(course_df)
            
            # Create analysis DataFrame
            analysis_df = create_analysis_df(player_df, course_df)
            
            # Check if yardage is present in the analysis_df
            st.subheader("Yardage Check")
            if 'yardage' in analysis_df.columns:
                st.write("Yardage column is present in the analysis DataFrame")
                st.write(f"Sample yardage values: {analysis_df['yardage'].head().tolist()}")
            else:
                st.write("Yardage column is missing from the analysis DataFrame")
                st.write(f"Available columns: {analysis_df.columns.tolist()}")
            
            # Create shot-by-shot DataFrame
            shot_by_shot_df = create_shot_by_shot_df(analysis_df)
            
            # Display analysis data
            st.subheader("Combined Analysis Data Preview")
            st.dataframe(analysis_df.head())
            
            st.subheader("Shot-by-Shot Data Preview")
            st.dataframe(shot_by_shot_df)
            
            # Display some statistics
            st.subheader("Shot Statistics")
            st.write(f"Total shots in dataset: {len(shot_by_shot_df)}")
            
            # Group by round_id and count shots
            shots_per_round = shot_by_shot_df.groupby('round_id').size().reset_index(name='shots')
            st.write("Shots per round:")
            st.dataframe(shots_per_round)

if __name__ == "__main__":
    run_streamlit_app()


