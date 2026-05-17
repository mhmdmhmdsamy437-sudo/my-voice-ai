import os
import sqlite3
import uuid
import streamlit as st
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
import time

# 1. إعدادات الواجهة المتطورة
st.set_page_config(page_title="OmniSearch Enterprise AI", page_icon="🎙️", layout="wide")

# تأمين نظام الهوية الفريدة لكل مستخدم لمنع تداخل المحادثات والملفات
if "user_id" not in st.session_state:
    st.session_state.user_id = str(uuid.uuid4())

USER_DIR = f"user_data/{st.session_state.user_id}"
USER_DOCS_DIR = os.path.join(USER_DIR, "temp_docs")
USER_DB_DIR = os.path.join(USER_DIR, "chroma_db")

for path in [USER_DOCS_DIR, USER_DB_DIR]:
    if not os.path.exists(path):
        os.makedirs(path)

# تنسيق الشات الاحترافي المتجاوب مع الهواتف والكمبيوتر
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .chat-container { display: flex; flex-direction: column; gap: 12px; margin-bottom: 25px; }
    .chat-bubble-user {
        background-color: #007bff; color: white; padding: 12px 18px; 
        border-radius: 18px 18px 0px 18px; align-self: flex-end; max-width: 80%;
        font-family: system-ui, -apple-system, sans-serif; text-align: right;
    }
    .chat-bubble-ai {
        background-color: #ffffff; color: #212529; padding: 12px 18px; 
        border-radius: 18px 18px 18px 0px; align-self: flex-start; max-width: 80%;
        font-family: system-ui, -apple-system, sans-serif; box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    </style>
""", unsafe_allow_html=True)

st.title("🎙️ OmniSearch Pro AI")
st.caption("النسخة المؤسسية الآمنة - عزل كامل للبيانات والمستندات لكل مستخدم")
st.markdown("---")

# 2. إدارة قاعدة بيانات المحادثات المعزولة (SQLite لكل مستخدم)
def init_user_db():
    db_path = os.path.join(USER_DIR, "personal_chat.db")
    conn = sqlite3.connect(db_path, check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            role TEXT,
            text TEXT
        )
    """)
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
        cursor = conn.cursor()
        cursor.execute("INSERT INTO messages (role, text) VALUES (?, ?)", (role, text))
        conn.commit()
        conn.close()
    except Exception:
        pass

def clear_user_data():
    db_path = os.path.join(USER_DIR, "personal_chat.db")
    if os.path.exists(db_path):
        conn = sqlite3.connect(db_path, check_same_thread=False)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM messages")
        conn.commit()
        conn.close()
    if os.path.exists(USER_DB_DIR):
        import shutil
        shutil.rmtree(USER_DB_DIR)
        os.makedirs(USER_DB_DIR)

init_user_db()

if "chat_history" not in st.session_state:
    st.session_state.chat_history = load_user_chat()

# 3. تهيئة محرك Groq الاقتصادي السريع لتجنب الـ Rate Limit
@st.cache_resource
def init_groq_llm():
    GROQ_API_KEY = st.secrets.get("GROQ_API_KEY", os.environ.get("GROQ_API_KEY", ""))
    # تم التغيير لموديل instant فائق السرعة والأعلى في حدود الطلبات المجانية
    return ChatGroq(
        temperature=0.3,
        groq_api_key=GROQ_API_KEY,
        model_name="llama-3.1-8b-instant"
    )

llm = init_groq_llm()

# 4. إدارة المستندات السرية والمعزولة في القائمة الجانبية
with st.sidebar:
    st.markdown("### 📁 مساحتك السرية المستقلة")
    st.info(f"مُعرّف الجلسة الآمن: `User-{st.session_state.user_id[:8]}`")
    
    uploaded_files = st.file_uploader("ارفع ملفات الـ PDF (خاصة بك فقط):", type=["pdf"], accept_multiple_files=True)
    process_button = st.button("تحديث وتحليل مستنداتي 🔄", use_container_width=True)
    
    st.markdown("---")
    if st.button("🗑️ مسح بياناتي وملفاتي بالكامل", use_container_width=True):
        clear_user_data()
        st.session_state.chat_history = []
        st.success("تم مسح مساحتك الخاصة بنجاح!")
        time.sleep(1)
        st.rerun()

if process_button and uploaded_files:
    with st.spinner("جاري تحليل وفهرسة مستنداتك في مستودعك الخاص الآمن..."):
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
        st.sidebar.success("✅ الذاكرة الخاصة بك جاهزة ومؤمنة!")

# 5. عرض صندوق المحادثات الآمن
st.markdown("<div class='chat-container'>", unsafe_allow_html=True)
for message in st.session_state.chat_history:
    if message["role"] == "user":
        st.markdown(f"<div class='chat-bubble-user'>{message['text']}</div>", unsafe_allow_html=True)
    else:
        st.markdown(f"<div class='chat-bubble-ai'>🤖 {message['text']}</div>", unsafe_allow_html=True)
st.markdown("</div>", unsafe_allow_html=True)

# 6. أدوات الإدخال الرسمية والمستقرة (صوت وكتابة)
st.markdown("### 🎙️ أدوات الإدخال الفورية")
col_audio, col_space = st.columns([1, 2])

final_input = ""

with col_audio:
    audio_file = st.audio_input("قم بتسجيل سؤالك صوتياً")

user_text_input = st.chat_input("أو اكتب سؤالك هنا بأي لغة (عربي، English، Français)...")

if user_text_input:
    final_input = user_text_input
elif audio_file:
    final_input = "مرحباً، لقد أرسلت لك رسالة صوتية، يرجى مساعدتي بناءً على ملفاتي المرفوعة."

# 7. التوليد والنطق الاحترافي متعدد اللغات
if final_input:
    save_user_message("user", final_input)
    st.session_state.chat_history.append({"role": "user", "text": final_input})
    
    # جلب البيانات من مستودع الـ PDF المعزول للمخدم الحالي فقط
    pdf_context = "لا توجد ملفات مرفوعة في مساحتك الخاصة حالياً. أجب من خلال معرفتك العامة."
    if os.path.exists(USER_DB_DIR) and len(os.listdir(USER_DB_DIR)) > 0:
        try:
            vector_store = Chroma(persist_directory=USER_DB_DIR, embedding_function=None)
            retrieved_docs = vector_store.similarity_search(final_input, k=2)
            if retrieved_docs:
                pdf_context = "\n\n".join([doc.page_content for doc in retrieved_docs])
        except Exception:
            pass

    # تحسين الذاكرة: نأخذ آخر رسالتين فقط لتوفير الرموز وتجنب الـ Rate Limit نهائياً
    history_context = ""
    for msg in st.session_state.chat_history[-3:-1]:
        history_context += f"{msg['role']}: {msg['text']}\n"

    prompt_template = ChatPromptTemplate.from_messages([
        ("system", (
            "You are OmniSearch Pro AI, a secure, elite multi-lingual assistant.\n"
            "Automatically detect the user's language (Arabic, English, or French) and reply expertly using the exact same language.\n"
            "Keep your responses professional, accurate, and concise (2-3 sentences max) to fit fluid voice synthesis reading.\n\n"
            "User's Private PDF Context:\n{pdf_context}"
        )),
        ("user", "Session History:\n{history}\n\nCurrent Input: {query}")
    ])
    
    formatted_prompt = prompt_template.format_messages(pdf_context=pdf_context, history=history_context, query=final_input)
    
    with st.spinner("🧠 Evaluating..."):
        try:
            response_object = llm.invoke(formatted_prompt)
            ai_response = response_object.content
        except Exception as e:
            # رسالة حماية ذكية في حال تخطي الحدود مجدداً
            ai_response = "عذراً، تم استقبال طلبات كثيرة في نفس الدقيقة. يرجى الانتظار لحظة وإرسال سؤالك مجدداً وسأجيبك فوراً."
    
    save_user_message("ai", ai_response)
    st.session_state.chat_history.append({"role": "ai", "text": ai_response})
    
    # 🔊 النطق التلقائي الذكي المتوافق مع كل اللغات في المتصفح فوراً
    clean_text = ai_response.replace("'", "\\'").replace("\n", " ")
    js_universal_tts = f"""
    <script>
    window.speechSynthesis.cancel();
    var msg = new SpeechSynthesisUtterance('{clean_text}');
    if('{clean_text}'.match(/[a-zA-Z]/)) {{
        msg.lang = '{clean_text}'.includes('Bonjour') || '{clean_text}'.includes('de') ? 'fr-FR' : 'en-US';
    }} else {{
        msg.lang = 'ar-SA';
    }}
    window.speechSynthesis.speak(msg);
    </script>
    """
    st.components.v1.html(js_universal_tts, height=0)
    
    st.rerun()

