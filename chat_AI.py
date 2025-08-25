import streamlit as st
import json
import os
# --- Page Configurations ---

st.set_page_config(page_title="n8n Chatbot App", layout="centered")
# --- Sidebar for Navigation ---
# สร้างเมนูทางด้านซ้าย (Sidebar)
#Data = st.Page(page='views/testdata.py',title='Data', icon='📅')
chat_bot = st.Page(page='v3chat/views/Chat_page.py',title='Chat_bot', icon='🤖')
chat_zone = st.Page(page='v3chat/views/Chat_page_zone.py',title='Chat_bot_zone',icon='🤖')
#graph = st.Page(page='v3chat/views/Graph_data.py',title='graph', icon='📊')
#test_data = st.Page(page='v3chat/views/Table_Data.py',title='Table_Data', icon='📊')
pg = st.navigation(
        pages=[chat_bot,chat_zone]
    )
pg.run()



