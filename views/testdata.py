import streamlit as st
import psycopg2
import pandas as pd
import os
from datetime import datetime
import json
import base64
from PIL import Image
import io
import requests

# --- Database Configuration for Streamlit Cloud ---
class DatabaseConfig:
    """
    คลาสสำหรับจัดการการเชื่อมต่อ Database บน Streamlit Cloud
    """
    def __init__(self):
        # อ่านค่าจาก Streamlit secrets (สำหรับ Streamlit Cloud)
        try:
            self.host = st.secrets["database"]["host"]
            self.port = st.secrets["database"]["port"]
            self.database = st.secrets["database"]["dbname"]
            self.username = st.secrets["database"]["user"]
            self.password = st.secrets["database"]["password"]
            self.sslmode = st.secrets["database"].get("sslmode", "require")
            self.n8n_webhook_url = st.secrets["n8n"]["webhook_url"]
        except Exception as e:
            st.error("❌ Please configure database secrets in Streamlit Cloud dashboard")
            st.info("Required secrets: database.host, database.port, database.dbname, database.user, database.password, n8n.webhook_url")
            st.stop()

class DatabaseManager:
    """
    คลาสสำหรับจัดการการเชื่อมต่อและการทำงานกับ PostgreSQL
    """
    def __init__(self):
        self.config = DatabaseConfig()
        self.connection = None
    
    @st.cache_resource
    def get_connection(_self):
        """
        สร้างการเชื่อมต่อแบบ cached สำหรับ Streamlit Cloud
        """
        try:
            connection = psycopg2.connect(
                host=_self.config.host,
                port=_self.config.port,
                database=_self.config.database,
                user=_self.config.username,
                password=_self.config.password,
                sslmode=_self.config.sslmode,
                connect_timeout=10
            )
            return connection
        except Exception as e:
            st.error(f"❌ Database connection failed: {e}")
            return None
    
    def execute_query(self, query, params=None, fetch=True):
        """
        Execute SQL query อย่างปลอดภัย
        """
        connection = self.get_connection()
        if not connection:
            return None
        
        try:
            with connection.cursor() as cursor:
                cursor.execute(query, params)
                
                if fetch and query.strip().lower().startswith('select'):
                    columns = [desc[0] for desc in cursor.description]
                    rows = cursor.fetchall()
                    return pd.DataFrame(rows, columns=columns)
                else:
                    connection.commit()
                    return cursor.rowcount
                    
        except Exception as e:
            st.error(f"❌ Query execution failed: {e}")
            connection.rollback()
            return None
    
    def init_database(self):
        """
        สร้างตารางที่จำเป็นสำหรับแอปพลิเคชัน
        """
        create_tables_query = """
        CREATE TABLE IF NOT EXISTS chat_history (
            id SERIAL PRIMARY KEY,
            machine_name VARCHAR(100) NOT NULL,
            role VARCHAR(20) NOT NULL,
            content TEXT,
            message_type VARCHAR(20) DEFAULT 'text',
            image_data TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            session_id VARCHAR(100)
        );
        
        CREATE INDEX IF NOT EXISTS idx_chat_machine_name ON chat_history(machine_name);
        CREATE INDEX IF NOT EXISTS idx_chat_created_at ON chat_history(created_at);
        CREATE INDEX IF NOT EXISTS idx_chat_session_id ON chat_history(session_id);
        
        CREATE TABLE IF NOT EXISTS app_statistics (
            id SERIAL PRIMARY KEY,
            machine_name VARCHAR(100),
            action VARCHAR(50),
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            user_session VARCHAR(100)
        );
        """
        return self.execute_query(create_tables_query, fetch=False)
    
    def insert_chat_message(self, machine_name, role, content, message_type='text', image_data=None, session_id=None):
        """
        บันทึกข้อความแชทลงในฐานข้อมูล
        """
        query = """
        INSERT INTO chat_history (machine_name, role, content, message_type, image_data, session_id, created_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        RETURNING id
        """
        params = (machine_name, role, content, message_type, image_data, session_id, datetime.now())
        result = self.execute_query(query, params, fetch=True)
        return result is not None
    
    def get_chat_history(self, machine_name, session_id=None, limit=100):
        """
        ดึงประวัติการแชทจากฐานข้อมูล
        """
        if session_id:
            query = """
            SELECT role, content, message_type, image_data, created_at
            FROM chat_history 
            WHERE machine_name = %s AND session_id = %s
            ORDER BY created_at ASC
            LIMIT %s
            """
            params = (machine_name, session_id, limit)
        else:
            query = """
            SELECT role, content, message_type, image_data, created_at
            FROM chat_history 
            WHERE machine_name = %s 
            ORDER BY created_at DESC
            LIMIT %s
            """
            params = (machine_name, limit)
        
        return self.execute_query(query, params)
    
    def clear_chat_history(self, machine_name, session_id=None):
        """
        ลบประวัติการแชท
        """
        if session_id:
            query = "DELETE FROM chat_history WHERE machine_name = %s AND session_id = %s"
            params = (machine_name, session_id)
        else:
            query = "DELETE FROM chat_history WHERE machine_name = %s"
            params = (machine_name,)
        
        return self.execute_query(query, params, fetch=False)
    
    def get_statistics(self):
        """
        ดึงสถิติการใช้งาน
        """
        query = """
        SELECT 
            machine_name,
            COUNT(*) as total_messages,
            COUNT(DISTINCT session_id) as unique_sessions,
            MAX(created_at) as last_activity
        FROM chat_history 
        GROUP BY machine_name
        ORDER BY total_messages DESC
        """
        return self.execute_query(query)
    
    def log_activity(self, machine_name, action, session_id):
        """
        บันทึกกิจกรรมการใช้งาน
        """
        query = """
        INSERT INTO app_statistics (machine_name, action, user_session)
        VALUES (%s, %s, %s)
        """
        return self.execute_query(query, (machine_name, action, session_id), fetch=False)

# --- Helper Functions ---
def get_session_id():
    """
    สร้าง session ID สำหรับผู้ใช้แต่ละคน
    """
    if 'session_id' not in st.session_state:
        import uuid
        st.session_state.session_id = str(uuid.uuid4())
    return st.session_state.session_id

def image_to_base64(image):
    """
    แปลงรูปภาพเป็น base64
    """
    try:
        img_buffer = io.BytesIO()
        image.save(img_buffer, format='PNG')
        img_buffer.seek(0)
        return base64.b64encode(img_buffer.getvalue()).decode()
    except Exception as e:
        st.error(f"Error converting image: {e}")
        return None

def send_to_n8n(message, machine_name, has_image=False, image_data=None):
    """
    ส่งข้อมูลไป n8n webhook
    """
    try:
        payload = {
            "message": message,
            "machine": machine_name,
            "has_image": has_image,
            "timestamp": datetime.now().isoformat()
        }
        
        if has_image and image_data:
            payload["image"] = image_data
        
        db_config = DatabaseConfig()
        headers = {"Content-Type": "application/json"}
        
        response = requests.post(
            db_config.n8n_webhook_url, 
            data=json.dumps(payload), 
            headers=headers,
            timeout=30
        )
        response.raise_for_status()
        
        result = response.json()
        return result.get("reply", "No response from AI")
        
    except Exception as e:
        return f"Error communicating with AI: {e}"

# --- Main Streamlit Application ---
def main():
    st.set_page_config(
        page_title="AI Chat Assistant", 
        page_icon="🤖",
        layout="centered",
        initial_sidebar_state="expanded"
    )
    
    # Initialize database
    if 'db_manager' not in st.session_state:
        st.session_state.db_manager = DatabaseManager()
        # สร้างตารางถ้ายังไม่มี
        st.session_state.db_manager.init_database()
    
    db_manager = st.session_state.db_manager
    session_id = get_session_id()
    
    # --- Sidebar ---
    with st.sidebar:
        st.title("🤖 AI Assistant")
        st.write(f"Session: `{session_id[:8]}...`")
        
        # Database connection status
        with st.expander("📊 System Status"):
            if st.button("Test Database Connection"):
                connection = db_manager.get_connection()
                if connection:
                    st.success("✅ Database Connected")
                    try:
                        connection.close()
                    except:
                        pass
                else:
                    st.error("❌ Database Connection Failed")
            
            # Show statistics
            if st.button("Show Usage Statistics"):
                stats = db_manager.get_statistics()
                if stats is not None and not stats.empty:
                    st.dataframe(stats, use_container_width=True)
                else:
                    st.info("No data available")
        
        # Machine selection
        st.markdown("### 🔧 Select Machine")
        machine_options = [
            'FAN 2', 'FAN 1', 'PUMP 1', 'PUMP 2', 'PUMP 3',
            'BENCH TMPLT VRSPD', 'BENCH DA3',
            'EGL-ISO10816-3', 'FLC-ISO10816-3', 'MV-x ISO10816-3',
            '1A-1 - Pump', 'Gear EX', 'Pump Gateway'
        ]
        
        selected_machine = st.selectbox(
            "Machine:",
            machine_options,
            key="selected_machine"
        )
        
        # Actions
        st.markdown("### ⚙️ Actions")
        if st.button("🗑️ Clear This Session"):
            if db_manager.clear_chat_history(selected_machine, session_id):
                st.success("Session cleared!")
                st.session_state.messages = []
                st.rerun()
        
        if st.button("🗂️ Clear All History"):
            if db_manager.clear_chat_history(selected_machine):
                st.success("All history cleared!")
                st.session_state.messages = []
                st.rerun()
        
        st.markdown("---")
        st.info("💾 Data stored securely in PostgreSQL")
        st.caption("Deployed on Streamlit Cloud")
    
    # --- Main Chat Interface ---
    st.title(f"💬 Chat with {selected_machine}")
    st.caption("🌐 Public AI Assistant - Powered by PostgreSQL & n8n")
    
    # Load chat history
    if st.session_state.get("current_machine") != selected_machine:
        # Log machine change
        db_manager.log_activity(selected_machine, "machine_selected", session_id)
        
        # Load chat history for this session
        chat_df = db_manager.get_chat_history(selected_machine, session_id)
        st.session_state.messages = []
        
        if chat_df is not None and not chat_df.empty:
            for _, row in chat_df.iterrows():
                message = {
                    "role": row['role'],
                    "content": row['content'],
                    "type": row['message_type']
                }
                if row['image_data']:
                    message["image"] = row['image_data']
                st.session_state.messages.append(message)
        
        st.session_state.current_machine = selected_machine
    
    # Display chat messages
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            if message.get("type") == "image" and message.get("image"):
                try:
                    img_data = base64.b64decode(message["image"])
                    image = Image.open(io.BytesIO(img_data))
                    st.image(image, width=300)
                    if message.get("content"):
                        st.markdown(message["content"])
                except Exception as e:
                    st.error(f"Error displaying image: {e}")
                    st.markdown(message.get("content", ""))
            else:
                st.markdown(message["content"])
    
    # Image upload
    uploaded_file = st.file_uploader(
        "📎 Upload Image (optional)",
        type=['png', 'jpg', 'jpeg', 'gif', 'bmp'],
        help="Upload an image to analyze",
        key=f"uploader_{st.session_state.get('upload_key', 0)}"
    )
    
    if uploaded_file:
        col1, col2 = st.columns([1, 3])
        with col1:
            image = Image.open(uploaded_file)
            st.image(image, caption="Ready to send", width=150)
        with col2:
            st.info(f"📎 {uploaded_file.name} ({uploaded_file.size:,} bytes)")
    
    # Chat input
    if prompt := st.chat_input("Type your message here..."):
        # Process image if uploaded
        image_base64 = None
        message_type = "text"
        
        if uploaded_file:
            try:
                image = Image.open(uploaded_file)
                image.thumbnail((800, 600), Image.Resampling.LANCZOS)
                image_base64 = image_to_base64(image)
                message_type = "image"
            except Exception as e:
                st.error(f"Error processing image: {e}")
        
        # Add user message
        user_message = {
            "role": "user",
            "content": prompt,
            "type": message_type
        }
        if image_base64:
            user_message["image"] = image_base64
        
        st.session_state.messages.append(user_message)
        
        # Save to database
        db_manager.insert_chat_message(
            selected_machine, "user", prompt, message_type, 
            image_base64, session_id
        )
        
        # Display user message
        with st.chat_message("user"):
            if image_base64:
                try:
                    img_data = base64.b64decode(image_base64)
                    image = Image.open(io.BytesIO(img_data))
                    st.image(image, width=300)
                except:
                    pass
            st.markdown(prompt)
        
        # Get AI response
        with st.chat_message("assistant"):
            with st.spinner("🤔 Thinking..."):
                ai_response = send_to_n8n(
                    prompt, selected_machine, 
                    bool(image_base64), image_base64
                )
                st.markdown(ai_response)
        
        # Save AI response
        assistant_message = {
            "role": "assistant",
            "content": ai_response,
            "type": "text"
        }
        st.session_state.messages.append(assistant_message)
        
        db_manager.insert_chat_message(
            selected_machine, "assistant", ai_response, "text", 
            None, session_id
        )
        
        # Log activity
        db_manager.log_activity(selected_machine, "message_sent", session_id)
        
        # Clear uploaded file
        if 'upload_key' not in st.session_state:
            st.session_state.upload_key = 0
        st.session_state.upload_key += 1
        
        st.rerun()

if __name__ == "__main__":
    main()