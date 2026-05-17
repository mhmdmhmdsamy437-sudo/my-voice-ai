import os
import sqlite3
import uuid
import streamlit as st
import time
import io
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from groq import Groq 

# 1. إعدادات الواجهة المستقرة
st.set_page_config(page_title="صوتك | Sawtak AI", page_icon="🎙️", layout="wide")

if "user_id" not in st.session_state:
    st.session_state.user_id = str(uuid.uuid4())

# إضافة محرك لتوليد مفاتيح عشوائية لمنع المتصفح من تكرار الصوت القديم
if "audio_session_key" not in st.session_state:
    st.session_state.audio_session_key = str(uuid.uuid4())[:8]

USER_DIR = f"user_data/{st.session_state.user_id}"
USER_DOCS_DIR = os.path.join(USER_DIR, "temp_docs")
USER_DB_DIR = os.path.join(USER_DIR, "chroma_db")

for path in [USER_DOCS_DIR, USER_DB_DIR]:
    if not os.path.exists(path):
        os.makedirs(path)

st.markdown("""
    <style>
    .stApp {
        background-color: #111827 !important;
        color: #f3f4f6 !important;
    }
    .chat-container {
        display: flex;
        flex-direction: column;
        gap: 16px;
        padding: 5px;
        margin-bottom: 20px;
    }
    .chat-bubble-user {
        background: linear-gradient(135deg, #2563eb, #1d4ed8);
        color: #ffffff !important;
        padding: 12px 18px;
        border-radius: 16px 16px 4px 16px;
        align-self: flex-end;
        max-width: 85%;
        margin-left: auto;
        text-align: right;
    }
    .chat-bubble-ai {
        background-color: #1f2937;
        color: #f3f4f6 !important;
        padding: 14px 20px;
        border-radius: 16px 16px 16px 4px;
        align-self: flex-start;
        max-width: 85%;
        margin-right: auto;
        text-align: right;
        border: 1px solid #374151;
    }
    .stExpander {
        background-color: #1f2937 !important;
        border: 1px solid #374151 !important;
        border-radius: 8px !important;
    }
    h1, h2, h3, p, span, label {
        color: #f3f4f6 !important;
    }
    </style>
""", unsafe_allow_html=True)

st.title("🎙️ صوتك | Sawtak AI")
st.caption("النسخة المقفلة والمطورة لحل مشاكل ميكروفون الهواتف الذكية")

# 2. لوحة التحكم العلوية الثابتة والبديلة عن القائمة الجانبية
with st.expander("⚙️ لوحة التحكم وإدارة رفع المستندات والملفات"):
    enable_tts = st.toggle("تفعيل الرد الصوتي التلقائي 🔊", value=True)
    st.markdown("---")
    uploaded_files = st.file_uploader("ارفع ملفات الـ PDF هنا:", type=["pdf"], accept_multiple_files=True)
    process_button = st.button("تحديث وفهرسة البيانات الذكية 🔄", use_container_width=True)
    
    if process_button and uploaded_files:
        with st.spinner("جاري قراءة وتأصيل البيانات..."):
            all_docs = []
            for uploaded_file in uploaded_files:
                file_path = os.path.join(USER_DOCS_DIR, uploaded_file.name)
                with open(file_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())
                loader = PyPDFLoader(file_path)
                all_docs.extend(loader.load())
                
            text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=80)
            final_chunks = text_splitter.split_documents(all_docs)
            Chroma.from_documents(documents=final_chunks, embedding=None, persist_directory=USER_DB_DIR)
            st.success("✅ تم حفظ وفهرسة مستنداتك بنجاح!")
            
    st.markdown("---")
    if st.button("🗑️ تفريغ ومسح سجل الحوار بالكامل", use_container_width=True):
        db_path = os.path.join(USER_DIR, "personal_chat.db")
        if os.path.exists(db_path):
            conn = sqlite3.connect(db_path, check_same_thread=False)
            conn.cursor().execute("DELETE FROM messages")
            conn.commit()
            conn.close()
        if os.path.exists(USER_DB_DIR):
            import shutil
            shutil.rmtree(USER_DB_DIR)
        st.session_state.chat_history = []
        st.session_state.last_processed_audio_size = 0
        st.success("تم تصفير التطبيق بالكامل!")
        time.sleep(0.5)
        st.rerun()

st.markdown("---")

# 3. معالجة وتخزين سجل الرسائل
def init_user_db():
    db_path = os.path.join(USER_DIR, "personal_chat.db")
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.cursor().execute("CREATE TABLE IF NOT EXISTS messages (id INTEGER PRIMARY KEY AUTOINCREMENT, role TEXT, text TEXT)")
    conn.commit()
    conn.close()

def load_user_chat():
    db_path = os.path.join(USER_DIR, "personal_chat.db")
    conn = sqlite3.connect(db_path, check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("SELECT role, text FROM messages ORDER BY id ASC")
    rows = cursor.fetchall()
    conn.close()
    return [{"role": row[0], "text": row[1]} for row in rows]

def save_user_message(role, text):
    try:
        db_path = os.path.join(USER_DIR, "personal_chat.db")
        conn = sqlite3.connect(db_path, check_same_thread=False)
        conn.cursor().execute("INSERT INTO messages (role, text) VALUES (?, ?)", (role, text))
        conn.commit()
        conn.close()
    except Exception:
        pass

init_user_db()

if "chat_history" not in st.session_state:
    st.session_state.chat_history = load_user_chat()

if "last_processed_audio_size" not in st.session_state:
    st.session_state.last_processed_audio_size = 0

chat_placeholder = st.empty()

def display_chat():
    with chat_placeholder.container():
        st.markdown("<div class='chat-container'>", unsafe_allow_html=True)
        for message in st.session_state.chat_history:
            if message["role"] == "user":
                st.markdown(f"<div class='chat-bubble-user'>{message['text']}</div>", unsafe_allow_html=True)
            else:
                st.markdown(f"<div class='chat-bubble-ai'>{message['text']}</div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

display_chat()

# 4. قسم أدوات الإدخال المحدث بمفتاح ديناميكي لمنع تجميد الصوت
st.markdown("### 🎙️ أدوات الإدخال")
# استخدام المفتاح المتغير لإجبار المتصفح على فتح خط صوتي نقي وجديد تماماً
audio_file = st.audio_input("تحدث الآن عبر الميكروفون:", key=f"audio_input_{st.session_state.audio_session_key}")
user_text_input = st.chat_input("أو اكتب سؤالك هنا يدوياً...")

final_query = ""

if user_text_input:
    final_query = user_text_input
elif audio_file:
    try:
        audio_bytes = audio_file.read()
        audio_size = len(audio_bytes)
        
        if audio_size > 2000 and audio_size != st.session_state.last_processed_audio_size:
            st.session_state.last_processed_audio_size = audio_size
            with st.spinner("🎙️ جاري تصفية الصوت وقراءة النص بوضوح..."):
                GROQ_API_KEY = st.secrets.get("GROQ_API_KEY", os.environ.get("GROQ_API_KEY", ""))
                client = Groq(api_key=GROQ_API_KEY)
                
                audio_buffer = io.BytesIO(audio_bytes)
                audio_buffer.name = "input_audio.wav"
                
                # إعطاء معايير تدريب حادة لمحرك الصوت لإلغاء أي دمج خاطئ للحروف
                transcription = client.audio.transcriptions.create(
                    file=audio_buffer,
                    model="whisper-large-v3",
                    language="ar",
                    prompt="مساء الخير، السلام عليكم، من هو رئيس، ما هو علاج. المتحدث ينطق باللغة العربية بوضوح تام.",
                    response_format="text"
                )
                captured_text = str(transcription).strip()
                if len(captured_text) > 1:
                    final_query = captured_text
                    
            # تغيير مفتاح الجلسة الصوتية فوراً لضمان عدم تكرار المقطع القديم إطلاقاً
            st.session_state.audio_session_key = str(uuid.uuid4())[:8]
    except Exception:
        pass

# 5. معالجة وتوليد ردود الذكاء الاصطناعي
if final_query != "":
    save_user_message("user", final_query)
    st.session_state.chat_history.append({"role": "user", "text": final_query})
    display_chat()
    
    pdf_context = ""
    if os.path.exists(USER_DB_DIR) and len(os.listdir(USER_DB_DIR)) > 0:
        try:
            vector_store = Chroma(persist_directory=USER_DB_DIR, embedding_function=None)
            retrieved_docs = vector_store.similarity_search(final_query, k=2)
            if retrieved_docs:
                pdf_context = "\n".join([doc.page_content for doc in retrieved_docs])
        except Exception:
            pass

    history_context = ""
    for msg in st.session_state.chat_history[-2:-1]:
        history_context += f"{msg['role']}: {msg['text']}\n"

    prompt_template = ChatPromptTemplate.from_messages([
        ("system", (
            "أنت مساعد ذكي وموسوعي فائق الدقة. "
            "أجب على سؤال المستخدم مباشرة باللغة العربية الفصحى وبشكل علمي صحيح 100% وبدون عبارات مكررة.\n\n"
            "سياق المستندات المرفوعة:\n{pdf_context}"
        )),
        ("user", "الحوار السابق:\n{history}\n\nالسؤال الحالي المطلوب الإجابة عليه الآن: {query}")
    ])
    
    GROQ_API_KEY = st.secrets.get("GROQ_API_KEY", os.environ.get("GROQ_API_KEY", ""))
    llm = ChatGroq(temperature=0.2, groq_api_key=GROQ_API_KEY, model_name="llama-3.3-70b-versatile")
    
    formatted_prompt = prompt_template.format_messages(pdf_context=pdf_context if pdf_context else "لا توجد مستندات.", history=history_context, query=final_query)
    
    with chat_placeholder.container():
        display_chat()
        with st.chat_message("assistant"):
            try:
                response_stream = llm.stream(formatted_prompt)
                ai_response = st.write_stream(response_stream)
                ai_response = ai_response.strip()
            except Exception:
                ai_response = "يرجى المحاولة مرة أخرى."
                st.write(ai_response)
    
    save_user_message("ai", ai_response)
    st.session_state.chat_history.append({"role": "ai", "text": ai_response})
    
    if enable_tts:
        clean_text = ai_response.replace("'", "\\'").replace("\n", " ")
        js_universal_tts = f"""
        <script>
        window.speechSynthesis.cancel();
        var msg = new SpeechSynthesisUtterance('{clean_text}');
        msg.lang = 'ar-SA';
        window.speechSynthesis.speak(msg);
        </script>
        """
        st.components.v1.html(js_universal_tts, height=0)
    
    final_query = ""
    st.rerun()

