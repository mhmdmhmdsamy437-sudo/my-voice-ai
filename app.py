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

# 1. إعدادات الواجهة الفاخرة والمستقرة تماماً
st.set_page_config(page_title="صوتك | Sawtak AI", page_icon="🎙️", layout="wide")

if "user_id" not in st.session_state:
    st.session_state.user_id = str(uuid.uuid4())

USER_DIR = f"user_data/{st.session_state.user_id}"
USER_DOCS_DIR = os.path.join(USER_DIR, "temp_docs")
USER_DB_DIR = os.path.join(USER_DIR, "chroma_db")

for path in [USER_DOCS_DIR, USER_DB_DIR]:
    if not os.path.exists(path):
        os.makedirs(path)

# تثبيت التصميم الداكن الفاخر بنسبة 100% وإخفاء أدوات المطورين وجيت هاب تماماً
st.markdown("""
    <style>
    /* إخفاء زر الجيت هاب والشريط العلوي لتبدو كواجهة تطبيق كاملة */
    #MainMenu, header, footer {
        visibility: hidden !important;
        height: 0px !important;
    }
    .stAppDeployButton {
        display: none !important;
    }
    
    .stApp, .main, .block-container {
        background-color: #111827 !important;
        color: #f3f4f6 !important;
        padding-top: 10px !important;
    }
    .chat-container {
        display: flex;
        flex-direction: column;
        gap: 20px;
        padding: 10px;
        margin-bottom: 40px;
    }
    .chat-bubble-user {
        background: linear-gradient(135deg, #2563eb, #1d4ed8);
        color: #ffffff !important;
        padding: 14px 20px;
        border-radius: 20px 20px 4px 20px;
        align-self: flex-end;
        max-width: 70%;
        margin-left: auto;
        font-family: system-ui, -apple-system, sans-serif;
        text-align: right;
        box-shadow: 0 4px 12px rgba(37, 99, 235, 0.15);
    }
    .chat-bubble-ai {
        background-color: #1f2937;
        color: #f3f4f6 !important;
        padding: 16px 22px;
        border-radius: 20px 20px 20px 4px;
        align-self: flex-start;
        max-width: 70%;
        margin-right: auto;
        font-family: system-ui, -apple-system, sans-serif;
        text-align: right;
        border: 1px solid #374151;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
    }
    .stSidebar {
        background-color: #1f2937 !important;
        border-right: 1px solid #374151;
    }
    h1, h2, h3, p, span, label {
        color: #f3f4f6 !important;
    }
    .stChatInputContainer input {
        background-color: #1f2937 !important;
        color: white !important;
        border: 1px solid #4b5563 !important;
    }
    </style>
""", unsafe_allow_html=True)

st.title("🎙️ صوتك | Sawtak AI")
st.caption("الجيل المطور والمستقر للمحادثات الصوتية والذكية بجودة تدفق عالمية")
st.markdown("---")

# 2. إدارة قاعدة البيانات المحلية للمحادثات
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

if "last_processed_audio_size" not in st.session_state:
    st.session_state.last_processed_audio_size = 0

# 3. تهيئة محرك الذكاء الاصطناعي بنسبة متزنة جداً
GROQ_API_KEY = st.secrets.get("GROQ_API_KEY", os.environ.get("GROQ_API_KEY", ""))

@st.cache_resource
def init_groq_llm():
    return ChatGroq(
        temperature=0.1,                          
        groq_api_key=GROQ_API_KEY,
        model_name="llama-3.3-70b-versatile"     
    )

llm = init_groq_llm()

# 4. إدارة المستندات والإعدادات (الـ Sidebar الجانبي)
with st.sidebar:
    st.markdown("### ⚙️ التحكم بالصوت")
    # زر واحد متكامل للتشغيل والإيقاف على طريقة التطبيقات العالمية وحسب رغبتك
    enable_tts = st.toggle("تفعيل النطق الصوتي التلقائي 🔊", value=True)
    
    st.markdown("---")
    st.markdown("### 📁 المستندات والملفات الذكية")
    st.info(f"المستخدم: `Sawtak-{st.session_state.user_id[:6].upper()}`")
    
    uploaded_files = st.file_uploader("ارفع ملفات الـ PDF هنا:", type=["pdf"], accept_multiple_files=True)
    process_button = st.button("تحديث الفهرس الذكي 🔄", use_container_width=True)
    
    st.markdown("---")
    if st.button("🗑️ مسح السجل وإعادة التصفير", use_container_width=True):
        clear_user_data()
        st.session_state.chat_history = []
        st.session_state.last_processed_audio_size = 0
        st.success("تم مسح السجل والملفات بنجاح!")
        time.sleep(1)
        st.rerun()

if process_button and uploaded_files:
    with st.spinner("جاري معالجة المستندات وفهرستها..."):
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
        st.sidebar.success("✅ تم الفهرسة بنجاح!")

# 5. عرض ساحة المحادثة المستقرة
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

# 6. قسم أدوات الإدخال والمعالجة
st.markdown("### 🎙️ أداة الإدخال")
col_audio, col_space = st.columns([1, 2])

final_query = ""

with col_audio:
    audio_file = st.audio_input("تحدث الآن")

user_text_input = st.chat_input("اكتب سؤالك هنا يدوياً...")

if user_text_input:
    final_query = user_text_input
elif audio_file:
    try:
        audio_bytes = audio_file.read()
        audio_size = len(audio_bytes)
        
        if audio_size > 2000 and audio_size != st.session_state.last_processed_audio_size:
            st.session_state.last_processed_audio_size = audio_size
            with st.spinner("🎙️ جاري السماع وفهم النص..."):
                client = Groq(api_key=GROQ_API_KEY)
                
                audio_buffer = io.BytesIO(audio_bytes)
                audio_buffer.name = "input_audio.wav"
                
                transcription = client.audio.transcriptions.create(
                    file=audio_buffer,
                    model="whisper-large-v3",
                    language="ar",
                    prompt="المتحدث يتحدث باللغة العربية. يرجى كتابة ما يقوله بدقة إملائية تامة وبدون أي مقدمات.",
                    response_format="text"
                )
                captured_text = str(transcription).strip()
                if len(captured_text) > 1:
                    final_query = captured_text
    except Exception:
        st.warning("يرجى المحاولة مجدداً والتحدث بوضوح.")

# 7. معالجة الرد النهائي بنظام التدفق الذكي العالمي (Streaming)
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
    for msg in st.session_state.chat_history[-7:-1]:
        history_context += f"{msg['role']}: {msg['text']}\n"

    prompt_template = ChatPromptTemplate.from_messages([
        ("system", (
            "أنت (صوتك AI)، مساعد ذكي موسوعي تفاعلي، دقيق للغاية وعالمي. "
            "أجب على سؤال المستخدم مباشرة باللغة العربية الفصحى وبأسلوب رصين وموثوق.\n\n"
            "📋 تعليمات التشغيل الحازمة:\n"
            "1. إذا كان سؤال المستخدم عاماً (مثل: معلومات رياضية، سياسية، تاريخية، أو طبية عامة)، أجب بكل ثقة من خلال معارفك وحقائقك العالمية الحقيقية والواقعية 100%. وممنوع تماماً تأليف أو تخمين أسماء شخصيات وهمية.\n"
            "2. إذا كان السؤال يشير بوضوح إلى مستند أو ملف قام المستخدم برفعه, اعتمد هنا فقط على سياق الملفات المرفوعة الموفر لك بالأسفل.\n"
            "3. لا تكتب أبداً في بداية الرد مقدمات مكررة مثل 'الإجابة:' أو 'الرد:'. ابدأ صلب موضوع إجابتك فوراً.\n\n"
            "سياق الملفات المرفوعة:\n{pdf_context}"
        )),
        ("user", "سجل الحوار السابق للرجوع إليه عند الحاجة:\n{history}\n\nسؤال المستخدم الحالي الآن: {query}")
    ])
    
    formatted_prompt = prompt_template.format_messages(pdf_context=pdf_context if pdf_context else "لا توجد مستندات مرفوعة حالياً.", history=history_context, query=final_query)
    
    with chat_placeholder.container():
        display_chat()
        with st.chat_message("assistant", avatar=None):
            st.markdown("<style>.stChatMessage { background-color: transparent !important; border:none !important; }</style>", unsafe_allow_html=True)
            try:
                response_stream = llm.stream(formatted_prompt)
                ai_response = st.write_stream(response_stream)
                ai_response = ai_response.strip()
            except Exception:
                ai_response = "عذراً، حدث خطأ مؤقت في الاتصال، يرجى إعادة إرسال رسالتك."
                st.write(ai_response)
    
    save_user_message("ai", ai_response)
    st.session_state.chat_history.append({"role": "ai", "text": ai_response})
    
    # نطق الرد الصوتي تلقائياً فقط إن كان زر التحكم (enable_tts) مفعّلاً
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
    
    st.rerun()

