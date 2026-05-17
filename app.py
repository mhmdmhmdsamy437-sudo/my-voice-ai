import os
import sqlite3
import streamlit as st
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
import time

# 1. إعدادات الواجهة لتفادي مشاكل الحجم والتوافق
st.set_page_config(page_title="OmniSearch Voice AI", page_icon="🎙️", layout="wide")

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

st.markdown("<h2 style='text-align: center; color: #202123; font-weight: 600;'>OmniSearch Voice AI</h2>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #6e6e80; font-size: 0.95rem; margin-top:-10px;'>المحادثة الصوتية المستمرة الذكية المتكاملة مع الـ PDF</p>", unsafe_allow_html=True)
st.markdown("<hr/>", unsafe_allow_html=True)

if not os.path.exists("temp_docs"):
    os.makedirs("temp_docs")

# 2. إدارة قاعدة البيانات وسجل الذاكرة بشكل آمن
def init_db():
    conn = sqlite3.connect("chat_history.db", check_same_thread=False)
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
    conn = sqlite3.connect("chat_history.db", check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("SELECT role, text FROM messages ORDER BY id ASC")
    rows = cursor.fetchall()
    conn.close()
    return [{"role": row[0], "text": row[1]} for row in rows]

def save_message(role, text):
    try:
        conn = sqlite3.connect("chat_history.db", check_same_thread=False)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO messages (role, text) VALUES (?, ?)", (role, text))
        conn.commit()
        conn.close()
    except Exception:
        pass

def clear_db():
    conn = sqlite3.connect("chat_history.db", check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM messages")
    conn.commit()
    conn.close()

init_db()

if "chat_history" not in st.session_state:
    st.session_state.chat_history = load_chat_history()

if "speaking" not in st.session_state:
    st.session_state.speaking = False

# 3. تهيئة سحابة الموديلات (تعديل دالة استدعاء مفتاح Groq لتجنب الانهيار)
@st.cache_resource
def init_models():
    if "GROQ_API_KEY" in st.secrets:
        GROQ_API_KEY = st.secrets["GROQ_API_KEY"]
    else:
        GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
        
    llm = ChatGroq(
        temperature=0.5,
        groq_api_key=GROQ_API_KEY,
        model_name="llama-3.3-70b-versatile"
    )
    return llm

llm = init_models()

# 4. القائمة الجانبية المخصصة للمستندات والملفات
with st.sidebar:
    st.markdown("<h3 style='color: #202123;'>📁 ملفات الـ PDF</h3>", unsafe_allow_html=True)
    uploaded_files = st.file_uploader("ارفع ملفات الـ PDF لمشروعك:", type=["pdf"], accept_multiple_files=True)
    process_button = st.button("تحديث وقراءة الذاكرة 🔄", use_container_width=True)
    
    st.markdown("---")
    if st.button("مسح سجل الذاكرة 🗑️", use_container_width=True):
        clear_db()
        st.session_state.chat_history = []
        st.session_state.speaking = False
        st.rerun()

if process_button and uploaded_files:
    with st.spinner("جاري معالجة وفهرسة المستندات..."):
        all_docs = []
        for uploaded_file in uploaded_files:
            file_path = os.path.join("temp_docs", uploaded_file.name)
            with open(file_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            loader = PyPDFLoader(file_path)
            all_docs.extend(loader.load())
            
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=80)
        final_chunks = text_splitter.split_documents(all_docs)
        Chroma.from_documents(documents=final_chunks, embedding=None, persist_directory="chroma_db")
        st.sidebar.success("✅ تم تحديث وقراءة مستنداتك بنجاح!")

# 5. عرض محادثات الشات على الواجهة
chat_container = st.container()
with chat_container:
    for message in st.session_state.chat_history:
        if message["role"] == "user":
            st.markdown(f"<div class='chat-bubble-user' style='direction: rtl;'>{message['text']}</div>", unsafe_allow_html=True)
        else:
            st.markdown(f"<div class='chat-bubble-ai' style='direction: rtl;'>🤖 {message['text']}</div>", unsafe_allow_html=True)

st.markdown("<div style='clear: both; margin-bottom: 40px;'></div>", unsafe_allow_html=True)

# 6. 🎙️ محرك الاستماع الصوتي التلقائي والذكي بدون أزرار
st.markdown("<p style='color:#6e6e80; font-size:0.9rem;'>🎙️ وضع الاستماع الصوتي المستمر نشط الآن تلقائياً...</p>", unsafe_allow_html=True)

js_listen_state = "false" if st.session_state.speaking else "true"

js_speech_engine = f"""
<script>
if ({js_listen_state}) {{
    const recognition = new (window.SpeechRecognition || window.webkitSpeechRecognition)();
    recognition.lang = 'ar-SA';
    recognition.interimResults = false;
    recognition.maxAlternatives = 1;
    
    recognition.start();
    
    recognition.onresult = (event) => {{
        const speechResult = event.results[0][0].transcript;
        if(speechResult.trim() !== "") {{
            parent.postMessage({{type: 'streamlit:setComponentValue', value: speechResult}}, '*');
        }}
    }};
    
    recognition.onerror = (event) => {{
        setTimeout(() => {{ recognition.start(); }}, 1000);
    }};
}}
</script>
"""

audio_input_bridge = st.components.v1.html(js_speech_engine, height=0)
user_text_bridge = st.chat_input("أو اكتب رسالتك هنا يدوياً...")

final_input = ""
if user_text_bridge:
    final_input = user_text_bridge
elif audio_input_bridge:
    final_input = audio_input_bridge

# 7. توليد الإجابة البرمجية الذكية باستخدام دالة invoke الحديثة والتحديث النطقي
if final_input and not st.session_state.speaking:
    save_message("user", final_input)
    st.session_state.chat_history.append({"role": "user", "text": final_input})
    st.markdown(f"<div class='chat-bubble-user' style='direction: rtl;'>{final_input}</div>", unsafe_allow_html=True)
    
    # استخراج النصوص والبحث في الـ PDF
    pdf_context = "لا توجد ملفات مرفوعة حالياً. أجب مباشرة من معلوماتك العامة."
    if os.path.exists("chroma_db") and len(os.listdir("chroma_db")) > 0:
        try:
            vector_store = Chroma(persist_directory="chroma_db", embedding_function=None)
            retrieved_docs = vector_store.similarity_search(final_input, k=2)
            if retrieved_docs:
                pdf_context = "\n\n".join([doc.page_content for doc in retrieved_docs])
        except Exception:
            pass

    history_context = ""
    for msg in st.session_state.chat_history[-5:-1]:
        history_context += f"{msg['role']}: {msg['text']}\n"

    prompt_template = ChatPromptTemplate.from_messages([
        ("system", (
            "أنت OmniSearch AI، مساعد صوتي ذكي وموجز للغاية.\n"
            "أجب دائماً باللغة العربية الفصحى.\n"
            "هام جداً: يجب أن تكون إجابتك مختصرة وقصيرة جداً (سطر أو سطرين كحد أقصى) لتناسب النطق الصوتي السريع والمحادثة المستمرة.\n\n"
            "سياق ملفات الـ PDF للمشروع:\n{pdf_context}"
        )),
        ("user", "سجل الجلسة السابقة:\n{history}\n\nالسؤال الحالي المطلوب الإجابة عليه: {query}")
    ])
    
    # استخدام نظام الـ Prompt والـ invoke المحدث والمتوافق بنسبة 100%
    formatted_prompt = prompt_template.format_messages(pdf_context=pdf_context, history=history_context, query=final_input)
    
    # تم التحديث هنا من predict إلى invoke لحل خطأ الـ AttributeError نهائياً
    response_object = llm.invoke(formatted_prompt)
    ai_response = response_object.content
    
    save_message("ai", ai_response)
    st.session_state.chat_history.append({"role": "ai", "text": ai_response})
    st.markdown(f"<div class='chat-bubble-ai' style='direction: rtl;'>🤖 {ai_response}</div>", unsafe_allow_html=True)
    
    st.session_state.speaking = True
    clean_text = ai_response.replace("'", "\\'").replace("\n", " ")
    
    js_tts_engine = f"""
    <script>
    window.speechSynthesis.cancel();
    var msg = new SpeechSynthesisUtterance('{clean_text}');
    msg.lang = 'ar-SA';
    msg.rate = 1.1;
    
    msg.onend = function() {{
        parent.postMessage({{type: 'streamlit:setComponentValue', value: 'SPEECH_DONE'}}, '*');
    }};
    
    window.speechSynthesis.speak(msg);
    </script>
    """
    st.components.v1.html(js_tts_engine, height=0)
    time.sleep(0.5)
    st.rerun()

# إعادة فتح المايك مجدداً بمجرد صمت الروبوت لتستمر المحادثة تلقائياً
if final_input == "SPEECH_DONE":
    st.session_state.speaking = False
    st.rerun()

