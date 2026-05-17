import os
import sqlite3
import streamlit as st
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
import time

# 1. إعدادات الواجهة وتصميم الـ Chatbot المتطور
st.set_page_config(page_title="OmniSearch Cloud AI", page_icon="🎙️", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #ffffff; }
    .chat-bubble-user {
        background-color: #f4f4f4; color: #1d1d1d; padding: 14px 18px; 
        border-radius: 20px; margin: 8px 0; display: inline-block; float: right; clear: both;
        max-width: 75%; font-family: 'Segoe UI', sans-serif;
    }
    .chat-bubble-ai {
        background-color: transparent; color: #0d0d0d; padding: 14px 18px; 
        margin: 8px 0; display: inline-block; float: left; clear: both;
        max-width: 85%; font-family: 'Segoe UI', sans-serif;
    }
    hr { margin-top: 1rem; margin-bottom: 1rem; border: 0; border-top: 1px solid rgba(0,0,0,.1); }
    </style>
""", unsafe_allow_html=True)

st.markdown("<h2 style='text-align: center; color: #202123; font-weight: 600;'>OmniSearch Voice AI</h2>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #6e6e80; font-size: 0.95rem; margin-top:-10px;'>نظام المحادثة الصوتية المستمرة وقراءة الـ PDF</p>", unsafe_allow_html=True)
st.markdown("<hr/>", unsafe_allow_html=True)

if not os.path.exists("temp_docs"):
    os.makedirs("temp_docs")

# 2. إدارة قاعدة البيانات وسجل المحادثات
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

# 3. تهيئة الموديلات (تعديل لتجنب أخطاء Embeddings عند عدم وجود ملفات)
@st.cache_resource
def init_models():
    if "GROQ_API_KEY" in st.secrets:
        GROQ_API_KEY = st.secrets["GROQ_API_KEY"]
    else:
        GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
        
    llm = ChatGroq(
        temperature=0.6,
        groq_api_key=GROQ_API_KEY,
        model_name="llama-3.3-70b-versatile"
    )
    return llm

llm = init_models()

# 4. شريط التحكم الجانبي برفع الملفات
with st.sidebar:
    st.markdown("<h3 style='color: #202123;'>📁 إدارة مستندات PDF</h3>", unsafe_allow_html=True)
    uploaded_files = st.file_uploader("ارفع ملفات الـ PDF الخاصة بك هنا:", type=["pdf"], accept_multiple_files=True)
    process_button = st.button("تحديث وتحليل الملفات 🔄", use_container_width=True)
    
    st.markdown("---")
    if st.button("مسح سجل الذاكرة والمحادثة 🗑️", use_container_width=True):
        clear_db()
        st.session_state.chat_history = []
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
            
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=600, chunk_overlap=100)
        final_chunks = text_splitter.split_documents(all_docs)
        # حفظ النصوص مباشرة لتسهيل البحث السحابي بدون أخطاء الموديل المفقود
        Chroma.from_documents(documents=final_chunks, embedding=None, persist_directory="chroma_db")
        st.sidebar.success("✅ جاهز! تم دمج الملفات في ذاكرة المساعد.")

# 5. عرض صندوق الشات
chat_container = st.container()
with chat_container:
    for message in st.session_state.chat_history:
        if message["role"] == "user":
            st.markdown(f"<div class='chat-bubble-user' style='direction: rtl;'>{message['text']}</div>", unsafe_allow_html=True)
        else:
            st.markdown(f"<div class='chat-bubble-ai' style='direction: rtl;'>🤖 {message['text']}</div>", unsafe_allow_html=True)

st.markdown("<div style='clear: both; margin-bottom: 50px;'></div>", unsafe_allow_html=True)

# 6. 🎙️ هندسة الصوت المستمر التلقائي (Web Speech API)
# هذا الكود البرمجي الذكي يفتح المايك تلقائياً في المتصفح ويستمع إليك باستمرار
st.markdown("### 🎙️ وضع المحادثة الصوتية المستمرة نشط")

js_speech_trigger = """
<script>
const recognition = new (window.SpeechRecognition || window.webkitSpeechRecognition)();
recognition.lang = 'ar-SA';
recognition.interimResults = false;
recognition.maxAlternatives = 1;

// تشغيل المايك تلقائياً عند فتح الصفحة أو انتهاء الرد
if (!window.speechActive) {
    recognition.start();
    window.speechActive = true;
}

recognition.onresult = (event) => {
    const speechResult = event.results[0][0].transcript;
    // إرسال النص المستمع مباشرة إلى Streamlit بدون تدخل المستخدم
    parent.postMessage({type: 'streamlit:setComponentValue', value: speechResult}, '*');
    window.speechActive = false;
};

recognition.onerror = (event) => {
    window.speechActive = false;
    setTimeout(() => { recognition.start(); window.speechActive = true; }, 1000);
};

recognition.onend = () => {
    window.speechActive = false;
};
</script>
"""

# تضمين الواجهة الصوتية التلقائية في التطبيق
audio_input_value = st.components.v1.html(js_speech_trigger, height=0)

# مربع نصي اختياري في حال رغبت في الكتابة بدلاً من الصوت
user_text_input = st.chat_input("أو اكتب رسالتك هنا يدوياً...")

final_input = ""
if user_text_input:
    final_input = user_text_input
elif audio_input_value:
    final_input = audio_input_value

# 7. معالجة المدخلات والرد الصوتي والكتابي الذكي ومراجعة الـ PDF
if final_input:
    # حفظ رسالة المستخدم
    st.markdown(f"<div class='chat-bubble-user' style='direction: rtl;'>{final_input}</div>", unsafe_allow_html=True)
    save_message("user", final_input)
    st.session_state.chat_history.append({"role": "user", "text": final_input})
    
    # جلب معلومات الـ PDF إذا كانت متوفرة
    pdf_context = "لا توجد ملفات مرفوعة. أجب بذكاء من معلوماتك العامة."
    if os.path.exists("chroma_db") and len(os.listdir("chroma_db")) > 0:
        try:
            vector_store = Chroma(persist_directory="chroma_db", embedding_function=None)
            retrieved_docs = vector_store.similarity_search(final_input, k=2)
            if retrieved_docs:
                pdf_context = "\n\n".join([doc.page_content for doc in retrieved_docs])
        except Exception:
            pass

    # إعداد سياق المحادثة السابقة (History)
    history_context = ""
    for msg in st.session_state.chat_history[-5:-1]:
        history_context += f"{msg['role']}: {msg['text']}\n"

    prompt_template = ChatPromptTemplate.from_messages([
        ("system", (
            "أنت OmniSearch AI، مساعد صوتي ذكي وموجز ومحترف للغاية.\n"
            "أجب دائماً باللغة العربية الفصحى. يجب أن تكون إجابتك مختصرة جداً (سطر أو سطرين فقط) لتناسب النطق الصوتي السريع والمحادثة المستمرة المستقرة.\n\n"
            "سياق ملفات الـ PDF المرفوعة:\n{pdf_context}"
        )),
        ("user", "سجل المحادثة السابقة:\n{history}\n\nالسؤال الحالي: {query}")
    ])
    
    full_prompt = prompt_template.format(pdf_context=pdf_context, history=history_context, query=final_input)
    
    # توليد الرد من Llama 3.3
    ai_response = llm.predict(full_prompt)
    
    # عرض الرد في الواجهة
    st.markdown(f"<div class='chat-bubble-ai' style='direction: rtl;'>🤖 {ai_response}</div>", unsafe_allow_html=True)
    save_message("ai", ai_response)
    st.session_state.chat_history.append({"role": "ai", "text": ai_response})
    
    # 🔊 تحويل النص إلى صوت ونطقه تلقائياً ثم إعادة تشغيل المايك فوراً
    clean_text = ai_response.replace("'", "\\'").replace("\n", " ")
    tts_and_restart_script = f"""
    <script>
    window.speechSynthesis.cancel();
    var msg = new SpeechSynthesisUtterance('{clean_text}');
    msg.lang = 'ar-SA';
    msg.rate = 1.1;
    
    // عند انتهاء الذكاء الاصطناعي من الكلام، يتم تحديث الصفحة لفتح المايك من جديد والاستماع للمستخدم تلقائياً
    msg.onend = function() {{
        setTimeout(() => {{
            window.location.reload();
        }}, 500);
    }};
    
    window.speechSynthesis.speak(msg);
    </script>
    """
    st.components.v1.html(tts_and_restart_script, height=0)
    
    time.sleep(1)
    st.rerun()

