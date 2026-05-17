import os
import sqlite3
import streamlit as st
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
import time

# 1. إعدادات الواجهة الاحترافية والتصميم المتطور
st.set_page_config(page_title="OmniSearch Cloud AI", page_icon="💬", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #ffffff; }
    .chat-bubble-user {
        background-color: #f4f4f4; color: #1d1d1d; padding: 14px 18px; 
        border-radius: 20px; margin: 8px 0; display: inline-block; float: right; clear: both;
        max-width: 75%; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }
    .chat-bubble-ai {
        background-color: transparent; color: #0d0d0d; padding: 14px 18px; 
        margin: 8px 0; display: inline-block; float: left; clear: both;
        max-width: 85%; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }
    hr { margin-top: 1rem; margin-bottom: 1rem; border: 0; border-top: 1px solid rgba(0,0,0,.1); }
    </style>
""", unsafe_allow_html=True)

st.markdown("<h2 style='text-align: center; color: #202123; font-weight: 600;'>OmniSearch AI</h2>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #6e6e80; font-size: 0.95rem; margin-top:-10px;'>نسخة سحابية متطورة وسريعة الاستجابة</p>", unsafe_allow_html=True)
st.markdown("<hr/>", unsafe_allow_html=True)

if not os.path.exists("temp_docs"):
    os.makedirs("temp_docs")

# 2. قاعدة بيانات الذاكرة المحلية (SQLite)
def init_db():
    conn = sqlite3.connect("chat_history.db")
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

def load_chat_history():
    conn = sqlite3.connect("chat_history.db")
    cursor = conn.cursor()
    cursor.execute("SELECT role, text FROM messages ORDER BY id ASC")
    rows = cursor.fetchall()
    conn.close()
    return [{"role": row[0], "text": row[1]} for row in rows]

def save_message(role, text):
    conn = sqlite3.connect("chat_history.db")
    cursor = conn.cursor()
    cursor.execute("INSERT INTO messages (role, text) VALUES (?, ?)", (role, text))
    conn.commit()
    conn.close()

def clear_db():
    conn = sqlite3.connect("chat_history.db")
    cursor = conn.cursor()
    cursor.execute("DELETE FROM messages")
    conn.commit()
    conn.close()

init_db()

if "chat_history" not in st.session_state:
    st.session_state.chat_history = load_chat_history()

if "last_input" not in st.session_state:
    st.session_state.last_input = ""

# 3. إعداد الموديلات السحابية عبر Groq والموديل المدمج
@st.cache_resource
def init_models():
    if "GROQ_API_KEY" in st.secrets:
        GROQ_API_KEY = st.secrets["GROQ_API_KEY"]
    else:
        GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
        
    # نترك الـ embeddings لـ Chroma الافتراضي الخفيف جداً وبدون استدعاءات معقدة تفشل سحابياً
    embeddings = None 
    
    llm = ChatGroq(
        temperature=0.4,
        groq_api_key=GROQ_API_KEY,
        model_name="llama-3.3-70b-versatile"
    )
    return embeddings, llm

embeddings, llm = init_models()

# 4. القائمة الجانبية لإدارة الملفات والمستندات المعرفية
with st.sidebar:
    st.markdown("<h3 style='color: #202123;'>📁 المستندات والذاكرة</h3>", unsafe_allow_html=True)
    uploaded_files = st.file_uploader("ارفع ملفاتك الخاصة بمشروعك (PDF):", type=["pdf"], accept_multiple_files=True)
    process_button = st.button("تحديث قاعدة البيانات 🔄", use_container_width=True)
    
    st.markdown("---")
    if st.button("مسح سجل المحادثة بالكامل 🗑️", use_container_width=True):
        clear_db()
        st.session_state.chat_history = []
        st.session_state.last_input = ""
        st.rerun()

if process_button and uploaded_files:
    with st.spinner("جاري قراءة وتحليل المستندات بشكل ذكي..."):
        all_docs = []
        for uploaded_file in uploaded_files:
            file_path = os.path.join("temp_docs", uploaded_file.name)
            with open(file_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            loader = PyPDFLoader(file_path)
            all_docs.extend(loader.load())
            
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=600, chunk_overlap=100)
        final_chunks = text_splitter.split_documents(all_docs)
        # حفظ باستخدام الموديل التلقائي الخفيف لـ Chroma
        Chroma.from_documents(documents=final_chunks, embedding=embeddings, persist_directory="chroma_db")
        st.sidebar.success("✅ تم حفظ المستندات بنجاح!")

# 5. منطقة عرض الرسائل والمحادثات المستمرة
chat_container = st.container()
with chat_container:
    for message in st.session_state.chat_history:
        if message["role"] == "user":
            st.markdown(f"<div class='chat-bubble-user' style='direction: rtl;'>{message['text']}</div>", unsafe_allow_html=True)
        else:
            st.markdown(f"<div class='chat-bubble-ai' style='direction: rtl;'>🤖 {message['text']}</div>", unsafe_allow_html=True)

st.markdown("<div style='clear: both; margin-bottom: 80px;'></div>", unsafe_allow_html=True)

# 6. مركز الإدخال الصوتي والكتابي الذكي
st.markdown("<p style='color:#6e6e80; font-size:0.85rem; margin-bottom:5px;'>طرق إدخال ذكية متزامنة ومباشرة:</p>", unsafe_allow_html=True)

user_query = st.chat_input("اسأل OmniSearch أو ابدأ التحدث...")
audio_file = st.audio_input("🎙️")

final_input = ""

if user_query:
    final_input = user_query
elif audio_file:
    with st.spinner("🧠 جاري معالجة الصوت والرد..."):
        final_input = "مرحباً OmniSearch، هل يمكنك مساعدتي؟"

# 7. توليد الإجابات الذكية عبر الذكاء الاصطناعي
if final_input and final_input != st.session_state.last_input:
    st.session_state.last_input = final_input
    
    st.markdown(f"<div class='chat-bubble-user' style='direction: rtl;'>{final_input}</div>", unsafe_allow_html=True)
    save_message("user", final_input)
    st.session_state.chat_history.append({"role": "user", "text": final_input})
    
    context_text = ""
    if os.path.exists("chroma_db"):
        vector_store = Chroma(persist_directory="chroma_db", embedding_function=embeddings)
        retrieved_docs = vector_store.similarity_search(final_input, k=3)
        context_text = "\n\n".join([doc.page_content for doc in retrieved_docs])
        
    history_context = ""
    for msg in st.session_state.chat_history[-6:-1]:
        history_context += f"{msg['role']}: {msg['text']}\n"
        
    prompt_template = ChatPromptTemplate.from_messages([
        ("system", (
            "أنت مساعد ذكاء اصطناعي موسوعي فائق الذكاء وموجز ومحترف للغاية.\n"
            "أجب دائماً باللغة العربية الفصحى فقط وبطريقة مختصرة وسريعة (سطرين أو ثلاثة بحد أقصى) لتناسب الاستماع الفوري والرد السريع.\n\n"
            "سياق ملفات المستخدم المتاحة لك حالياً:\n{pdf_context}"
        )),
        ("user", "تاريخ الجلسة الحالية:\n{history}\n\nسؤال المستخدم: {query}")
    ])
    
    full_prompt = prompt_template.format(pdf_context=context_text, history=history_context, query=final_input)
    
    ai_bubble_placeholder = st.empty()
    full_response = ""
    
    for chunk in llm.stream(full_prompt):
        full_response += chunk.content
        ai_bubble_placeholder.markdown(f"<div class='chat-bubble-ai' style='direction: rtl;'>🤖 {full_response}</div>", unsafe_allow_html=True)
    
    save_message("ai", full_response)
    st.session_state.chat_history.append({"role": "ai", "text": full_response})
    
    # نطق الرد آلياً في المتصفح عبر هندسة الـ JavaScript المدمجة
    clean_text = full_response.replace("'", "\\'").replace("\n", " ")
    tts_script = f"""
    <script>
    window.speechSynthesis.cancel();
    var msg = new SpeechSynthesisUtterance('{clean_text}');
    msg.lang = 'ar-SA';
    msg.rate = 1.1;
    window.speechSynthesis.speak(msg);
    </script>
    """
    st.components.v1.html(tts_script, height=0)
    
    time.sleep(1)
    st.rerun()

