import streamlit as st
import json
import os
# --- Page Configurations ---

st.set_page_config(page_title="n8n Chatbot App", layout="centered")
# --- Sidebar for Navigation ---
# สร้างเมนูทางด้านซ้าย (Sidebar)
Data = st.Page(page=r'C:\Users\papeko14\Documents\fastwork\สอนไพธอน\mentor\2025-07-29\views\testdata.py',title='Data', icon='📅')
chat_bot = st.Page(page=r'C:\Users\papeko14\Documents\fastwork\สอนไพธอน\mentor\2025-07-29\views\Chat_page.py',title='Chat_bot', icon='🤖')
chat_zone = st.Page(page=r'C:\Users\papeko14\Documents\fastwork\สอนไพธอน\mentor\2025-07-29\views\Chat_page_zone.py',title='Chat_bot_zone',icon='🤖')
graph = st.Page(page=r'C:\Users\papeko14\Documents\fastwork\สอนไพธอน\mentor\2025-07-29\views\Graph_data.py',title='graph', icon='📊')
test_data = st.Page(page=r'C:\Users\papeko14\Documents\fastwork\สอนไพธอน\mentor\2025-07-29\views\Table_Data.py',title='Table_Data', icon='📊')
pg = st.navigation(
        pages=[chat_bot,Data,graph,chat_zone,test_data]
    )
pg.run()
