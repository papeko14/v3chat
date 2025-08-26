import streamlit as st
import requests
import json
import os
import pandas as pd
import csv
import base64
from PIL import Image
import io

# --- Configuration ---
# URL ของ n8n webhook
N8N_WEBHOOK_URL = "https://rationally-tough-ant.ngrok-free.app/webhook/d8e551ba-6202-4544-be0a-74294ecff821"

def load_chat_history(machine_name):
    """
    ฟังก์ชันสำหรับโหลดประวัติการแชทจากไฟล์ JSON ตามชื่อโซนและเครื่องจักร
    """
    chat_history_file = f"{machine_name}.json"
    if os.path.exists(chat_history_file):
        try:
            with open(chat_history_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return []
    return []

def save_chat_history(machine_name, messages):
    """
    ฟังก์ชันสำหรับบันทึกประวัติการแชทลงในไฟล์ JSON ตามชื่อโซนและเครื่องจักร
    """
    chat_history_file = f"{machine_name}.json"
    with open(chat_history_file, "w", encoding="utf-8") as f:
        json.dump(messages, f, indent=4, ensure_ascii=False)

def image_to_base64(image):
    """
    แปลงรูปภาพเป็น base64 string
    """
    try:
        # แปลง PIL Image เป็น bytes
        img_buffer = io.BytesIO()
        image.save(img_buffer, format='PNG')
        img_buffer.seek(0)
        
        # เข้ารหัสเป็น base64
        img_base64 = base64.b64encode(img_buffer.getvalue()).decode()
        return img_base64
    except Exception as e:
        st.error(f"Error converting image to base64: {e}")
        return None

def resize_image(image, max_size=(800, 600)):
    """
    ปรับขนาดรูปภาพเพื่อลดขนาดไฟล์
    """
    try:
        # คำนวณขนาดใหม่โดยคงอัตราส่วน
        image.thumbnail(max_size, Image.Resampling.LANCZOS)
        return image
    except Exception as e:
        st.error(f"Error resizing image: {e}")
        return image

# --- Streamlit UI ---
st.set_page_config(page_title="n8n Chatbot with Image Support", layout="centered")

# --- Sidebar for machine selection ---
with st.sidebar:
    st.title("Main Menu")
    # Dropdown menu สำหรับเลือกเครื่องจักร
    machine_options = ('Exsample','iso10816-3')
    selected_machine = st.selectbox(
        "Select a machine:",
        machine_options,
        key="selected_machine"
    )
    st.markdown("---")
    st.info("✨ Now supports text and image messages!")
    st.info("Developed with Streamlit and n8n")

st.title(f"🤖 Chat with {selected_machine}")
st.write("Type your message or upload an image to analyze!")

# --- Main App Logic ---

# Check for a change in machine selection
current_state_key = (selected_machine)
if st.session_state.get("current_state_key") != current_state_key:
    st.session_state.messages = load_chat_history(selected_machine)
    st.session_state["current_state_key"] = current_state_key

# Display past messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        if message.get("type") == "image":
            # แสดงรูปภาพจาก base64
            try:
                img_data = base64.b64decode(message["image"])
                image = Image.open(io.BytesIO(img_data))
                st.image(image, width=300)
                if message.get("content"):
                    st.markdown(message["content"])
            except Exception as e:
                st.error(f"Error displaying image: {e}")
        else:
            st.markdown(message["content"])

# --- Image Upload Section ---
st.markdown("---")
col1, col2 = st.columns([2, 1])

# เพิ่ม flag เพื่อเคลียร์ file uploader หลังจากส่งข้อความ
if 'clear_file_uploader' not in st.session_state:
    st.session_state.clear_file_uploader = False

with col1:
    # ใช้ key ที่เปลี่ยนแปลงได้เพื่อ reset file uploader
    uploader_key = f"file_uploader_{st.session_state.get('uploader_counter', 0)}"
    uploaded_file = st.file_uploader(
        "Upload an image (optional)", 
        type=['png', 'jpg', 'jpeg', 'gif', 'bmp'],
        help="Upload an image to analyze along with your message",
        key=uploader_key
    )

with col2:
    if uploaded_file is not None:
        # แสดงรูปภาพที่อัปโหลด
        image = Image.open(uploaded_file)
        st.image(image, caption="Uploaded Image", width=200)

# --- User Input and n8n Integration ---
if prompt := st.chat_input("Say something..."):
    # ตรวจสอบว่ามีการอัปโหลดรูปภาพหรือไม่
    has_image = uploaded_file is not None
    
    if has_image:
        try:
            # เตรียมรูปภาพ
            image = Image.open(uploaded_file)
            
            # ปรับขนาดรูปภาพ
            image = resize_image(image)
            
            # แปลงเป็น base64
            image_base64 = image_to_base64(image)
            
            if image_base64:
                # Add user message with image to chat history
                user_message = {
                    "role": "user", 
                    "content": prompt,
                    "type": "image",
                    "image": image_base64,
                    "filename": uploaded_file.name
                }
                st.session_state.messages.append(user_message)
                
                with st.chat_message("user"):
                    st.image(image, width=300)
                    st.markdown(prompt)
                
                # Send message with image to n8n webhook
                payload = {
                    "message": prompt,
                    "machine": selected_machine,
                    "has_image": True,
                    "image": image_base64,
                    "filename": uploaded_file.name,
                    "image_type": uploaded_file.type
                }
            else:
                st.error("Failed to process the uploaded image.")
                st.stop()
                
        except Exception as e:
            st.error(f"Error processing image: {e}")
            st.stop()
    else:
        # Text-only message
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Send text message to n8n webhook
        payload = {
            "message": prompt,
            "machine": selected_machine,
            "has_image": False
        }

    try:
        # Send request to n8n webhook
        headers = {"Content-Type": "application/json"}
        
        with st.spinner("Sending to n8n..."):
            response = requests.post(N8N_WEBHOOK_URL, data=json.dumps(payload), headers=headers, timeout=60)
            response.raise_for_status()

        # Get n8n's response
        n8n_response_data = response.json()
        n8n_message = n8n_response_data.get("reply", "No reply received from n8n.")

        # Add n8n's response to chat history
        st.session_state.messages.append({"role": "assistant", "content": n8n_message})
        with st.chat_message("assistant"):
            st.markdown(n8n_message)

    except requests.exceptions.Timeout:
        error_message = "Request timed out. Please try again."
        st.error(error_message)
        st.session_state.messages.append({"role": "assistant", "content": error_message})
        with st.chat_message("assistant"):
            st.markdown(error_message)
    except requests.exceptions.RequestException as e:
        error_message = f"Error connecting to n8n: {e}"
        st.error(error_message)
        st.session_state.messages.append({"role": "assistant", "content": error_message})
        with st.chat_message("assistant"):
            st.markdown(error_message)
    except json.JSONDecodeError:
        error_message = "n8n returned an invalid JSON response."
        st.error(error_message)
        st.session_state.messages.append({"role": "assistant", "content": error_message})
        with st.chat_message("assistant"):
            st.markdown(error_message)

    # Save the updated chat history to file
    save_chat_history(selected_machine, st.session_state.messages)
    
    # เคลียร์ file uploader โดยการเพิ่ม counter เพื่อเปลี่ยน key
    if 'uploader_counter' not in st.session_state:
        st.session_state.uploader_counter = 0
    st.session_state.uploader_counter += 1
    
    st.rerun()

# --- Additional Features ---
st.markdown("---")
if st.button("🗑️ Clear Chat History", type="secondary"):
    if st.session_state.get("messages"):
        st.session_state.messages = []
        save_chat_history(selected_machine, [])
        st.success("Chat history cleared!")
        st.rerun()

# Show file info if image is uploaded
if uploaded_file is not None:

    st.info(f"📎 Ready to send: {uploaded_file.name} ({uploaded_file.size} bytes)")
