import streamlit as st
import pandas as pd
import csv


def get_data_from_csv(file_path):
    """ฟังก์ชันสำหรับโหลดและทำความสะอาดข้อมูลจากไฟล์ CSV"""
    try:
        # Load CSV with specified encoding to avoid errors
        df = pd.read_csv(file_path, on_bad_lines='skip', engine='python', quoting=csv.QUOTE_NONE, quotechar='"' )
    except FileNotFoundError:
        st.error(f"Error: The file '{file_path}' was not found.")
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Error loading CSV file: {e}")
        return pd.DataFrame()
    
    # Identify and rename duplicate columns to make them unique for filtering
    cols = pd.Series(df.columns)
    for dup in df.columns[df.columns.duplicated(keep=False)]:
        cols[df.columns.get_loc(dup)] = [f"{x}_{i}" if i != 0 else x for i, x in enumerate(cols[df.columns.get_loc(dup)])]
    df.columns = cols
    return df

# --- Graph Page Content ---
st.title("📊 Data Visualization")
st.write("Welcome to the Data Dashboard!")
st.info("You can display a graph from your data here.")

# Load and process data
df = get_data_from_csv('merged_data.csv')

if not df.empty:
    st.markdown("---")
    st.subheader("Chart Options")

    # Allow user to select a column to plot
    numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
    
    # Assume 'name' column exists for the x-axis
    if 'Name' in df.columns:
        name_col = 'Name'
    else:
        name_col = None
        st.warning("Column 'name' not found. Cannot plot grouped bar chart.")

    if numeric_cols and name_col:
        selected_column = st.selectbox(
            "Select a numeric column to visualize:",
            numeric_cols
        )

        # --- Data Visualization (Graph) ---
        st.subheader(f"Bar Chart: '{selected_column}' by '{name_col}'")
        
        # Group data by name_col and plot the sum of the selected numeric column
        chart_data = df.groupby(name_col)[selected_column].sum()
        st.bar_chart(chart_data)
    elif not name_col:
        st.warning("Column 'name' not found. Please ensure your data has a 'name' column to use this chart.")
    elif not numeric_cols:
        st.warning("No numeric columns found in the data to plot.")