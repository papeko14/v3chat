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

# --- Data Dashboard Page Content ---
st.title("📅 Data Show")
st.info("You can display a data table here.")

# Load and process data
df = get_data_from_csv('merged_data.csv')

if not df.empty:
# --- Data Filtering ---
    st.subheader("Filter Data")

# ให้ผู้ใช้เลือกคอลัมน์ที่จะฟิลเตอร์
column_to_filter = st.selectbox(
    'Select a column to filter:',
    df.columns.tolist()
)

# ให้ผู้ใช้เลือกค่าที่จะฟิลเตอร์จากคอลัมน์ที่เลือก
unique_values = ['All'] + list(df[column_to_filter].unique())
selected_value = st.selectbox(
    f'Select value for {column_to_filter}:',
    unique_values
)

# Apply filter to the DataFrame
filtered_df = df.copy()
if selected_value != 'All':
    filtered_df = filtered_df[filtered_df[column_to_filter] == selected_value]
    
st.markdown("---")

st.subheader("Filtered Data")

# --- Handling potential serialization issues ---
# If the filtered DataFrame is still too large, sample it
if filtered_df.shape[0] > 100:
    st.warning(f"DataFrame is too large to display. Showing a sample of 1000 rows.")
    filtered_df = filtered_df.sample(100)
    
# Convert all object dtypes to string to avoid serialization errors
for col in filtered_df.columns:
    if filtered_df[col].dtype == 'object':
        filtered_df[col] = filtered_df[col].astype(str)

# Display the filtered DataFrame as a table
st.dataframe(filtered_df)