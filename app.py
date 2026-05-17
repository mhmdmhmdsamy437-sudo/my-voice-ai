import os
import sqlite3
import streamlit as st
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
import time

# 1. إعدادات الواجهة الاحترافية المتطورة (تتناسب مع الـ Cloud والـ Mobile)
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
st.markdown("<p style='text-align: center; color: #6e6e80; font-size: 0.95rem; margin-top:-10px;'>المحادثة الصوتية المستمرة والذكية المتكاملة مع الـ PDF</p>", unsafe_allow_html=True)
st.markdown("<hr/>", unsafe_allow_html=True)

if not os.path.exists("temp_docs"):
    os.makedirs("temp_docs")

# 2. إدارة قاعدة البيانات المحلية لحفظ الجلسات وتفادي تعارض الـ Cloud
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

# 3. تهيئة سحابة الموديلات وجلب مفاتيح الـ API الذكية
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

# 4. القائمة الجانبية لإدارة تحديث ملفات الـ PDF
with st.sidebar:
    st.markdown("<h3 style='color: #202123;'>📁 ملفات مشروعك (PDF)</h3>", unsafe_allow_html=True)
    uploaded_files = st.file_uploader("ارفع المستندات هنا:", type=["pdf"], accept_multiple_files=True)
    process_button = st.button("تحديث وقراءة الذاكرة 🔄", use_container_width=True)
    
    st.markdown("---")
    if st.button("مسح سجل المحادثة 🗑️", use_container_width=True):
        clear_db()
        st.session_state.chat_history = []
        st.session_state.speaking = False
        st.rerun()

if process_button and uploaded_files:
    with st.spinner("جاري فهرسة النصوص بدقة وبناء قاعدة البيانات السحابية..."):
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
        st.sidebar.success("✅ الذاكرة جاهزة ومحدثة الآن!")

# 5. عرض واجهة صندوق الرسائل والشات
chat_container = st.container()
with chat_container:
    for message in st.session_state.chat_history:
        if message["role"] == "user":
            st.markdown(f"<div class='chat-bubble-user' style='direction: rtl;'>{message['text']}</div>", unsafe_allow_html=True)
        else:
            st.markdown(f"<div class='chat-bubble-ai' style='direction: rtl;'>🤖 {message['text']}</div>", unsafe_allow_html=True)

st.markdown("<div style='clear: both; margin-bottom: 40px;'></div>", unsafe_allow_html=True)

# 6. 🎙️ محرك الاستماع الصوتي المستمر الذكي (Web Speech API)
# يستمع لك تلقائياً بمجرد صمت الروبوت ولا يحتاج لضغط أزرار
st.markdown("<p style='color:#6e6e80; font-size:0.9rem;'>🎙️ وضع الاستماع التلقائي والمحادثة المستمرة نشط الآن...</p>", unsafe_allow_html=True)

# نتحكم في تشغيل المايك عبر الجافا سكريبت بناء على حالة المتحدث الحالي
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

# دمج المحرك داخل الصفحة لاستقبال القيمة الصوتية المستمرة
audio_input_bridge = st.components.v1.html(js_speech_engine, height=0)
user_text_bridge = st.chat_input("أو اكتب رسالتك هنا يدوياً في أي وقت...")

final_input = ""
if user_text_bridge:
    final_input = user_text_bridge
elif audio_input_bridge:
    final_input = audio_input_bridge

# 7. معالجة الذكاء الاصطناعي وصنع الرد التلقائي الشامل والـ TTS النطقي
if final_input and not st.session_state.speaking:
    # حفظ وتحديث الواجهة برسالة المستخدم فوراً
    save_message("user", final_input)
    st.session_state.chat_history.append({"role": "user", "text": final_input})
    st.markdown(f"<div class='chat-bubble-user' style='direction: rtl;'>{final_input}</div>", unsafe_allow_html=True)
    
    # فحص محتويات ملفات الـ PDF إن وجدت
    pdf_context = "لا توجد ملفات مرفوعة حالياً. أجب من معرفتك العامة الموسوعية كذكاء اصطناعي."
    if os.path.exists("chroma_db") and len(os.listdir("chroma_db")) > 0:
        try:
            vector_store = Chroma(persist_directory="chroma_db", embedding_function=None)
            retrieved_docs = vector_store.similarity_search(final_input, k=2)
            if retrieved_docs:
                pdf_context = "\n\n".join([doc.page_content for doc in retrieved_docs])
        except Exception:
            pass

    # تجهيز سجل الذاكرة المؤقتة لضمان استمرار السياق الفكري
    history_context = ""
    for msg in st.session_state.chat_history[-5:-1]:
        history_context += f"{msg['role']}: {msg['text']}\n"

    prompt_template = ChatPromptTemplate.from_messages([
        ("system", (
            "أنت OmniSearch AI، مساعد صوتي محترف، ذكي، وموجز للغاية.\n"
            "أجب دائماً باللغة العربية الفصحى السلسة والسهلة.\n"
            "هام جداً: اجعل إجابتك قصيرة ومباشرة (سطر واحد أو سطرين فقط) لتناسب المحادثة الصوتية المستمرة سريعة الاستجابة.\n\n"
            "سياق ملفات الـ PDF للمشروع المرفوع:\n{pdf_context}"
        )),
        ("user", "سجل الجلسة السابقة:\n{history}\n\nالسؤال الجديد المطلوب الإجابة عليه بصوتك: {query}")
    ])
    
    full_prompt = prompt_template.format(pdf_context=pdf_context, history=history_context, query=final_input)
    
    # توليد الإجابة
    ai_response = llm.predict(full_prompt)
    
    # عرض الرد في الصندوق وتحديث السجل
    save_message("ai", ai_response)
    st.session_state.chat_history.append({"role": "ai", "text": ai_response})
    st.markdown(f"<div class='chat-bubble-ai' style='direction: rtl;'>🤖 {ai_response}</div>", unsafe_allow_html=True)
    
    # تحويل الرد إلى مقطع صوتي ناطق وإعادة تشغيل المايك تلقائياً فور انتهائه
    st.session_state.speaking = True
    clean_text = ai_response.replace("'", "\\'").replace("\n", " ")
    
    js_tts_engine = f"""
    <script>
    window.speechSynthesis.cancel();
    var msg = new SpeechSynthesisUtterance('{clean_text}');
    msg.lang = 'ar-SA';
    msg.rate = 1.1;
    
    msg.onend = function() {{
        // إبلاغ السيرفر بانتهاء النطق لإعادة فتح المايكروفون تلقائياً
        parent.postMessage({{type: 'streamlit:setComponentValue', value: 'SPEECH_DONE'}}, '*');
    }};
    
    window.speechSynthesis.speak(msg);
    </script>
    """
    st.components.v1.html(js_tts_engine, height=0)
    time.sleep(0.5)
    st.rerun()

# التحقق من إشارة انتهاء النطق لإعادة فتح المايك للاستماع مجدداً
if final_input == "SPEECH_DONE":
    st.session_state.speaking = False
    st.rerun()

