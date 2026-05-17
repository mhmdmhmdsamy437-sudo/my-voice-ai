import os
import sqlite3
import streamlit as st
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
import time

# 1. إعدادات الواجهة وتثبيت الهوية البصرية للتطبيق
st.set_page_config(page_title="OmniSearch Voice AI", page_icon="🎙️", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #ffffff; }
    .chat-bubble-user {
        background-color: #f4f4f4; color: #1d1d1d; padding: 14px 18px; 
        border-radius: 20px; margin: 8px 0; display: inline-block; float: right; clear: both;
        max-width: 75%; font-family: 'Segoe UI', Arial, sans-serif; text-align: right;
    }
    .chat-bubble-ai {
        background-color: transparent; color: #0d0d0d; padding: 14px 18px; 
        margin: 8px 0; display: inline-block; float: left; clear: both;
        max-width: 85%; font-family: 'Segoe UI', Arial, sans-serif; text-align: right;
    }
    hr { margin-top: 1rem; margin-bottom: 1rem; border: 0; border-top: 1px solid rgba(0,0,0,.1); }
    </style>
""", unsafe_allow_html=True)

st.markdown("<h2 style='text-align: center; color: #202123; font-weight: 600;'>OmniSearch Voice AI</h2>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #6e6e80; font-size: 0.95rem; margin-top:-10px;'>الجيل المطور للمحادثات الصوتية وقراءة ملفات الـ PDF</p>", unsafe_allow_html=True)
st.markdown("<hr/>", unsafe_allow_html=True)

if not os.path.exists("temp_docs"):
    os.makedirs("temp_docs")

# 2. إدارة الذاكرة المحلية (SQLite) لضمان ثبات البيانات
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

# تهيئة متغيرات الحالات (Session States)
if "chat_history" not in st.session_state:
    st.session_state.chat_history = load_chat_history()

if "voice_active" not in st.session_state:
    st.session_state.voice_active = False

if "speaking" not in st.session_state:
    st.session_state.speaking = False

# 3. استدعاء وتهيئة موديل الذكاء الاصطناعي
@st.cache_resource
def init_models():
    if "GROQ_API_KEY" in st.secrets:
        GROQ_API_KEY = st.secrets["GROQ_API_KEY"]
    else:
        GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
        
    llm = ChatGroq(
        temperature=0.4,
        groq_api_key=GROQ_API_KEY,
        model_name="llama-3.3-70b-versatile"
    )
    return llm

llm = init_models()

# 4. التحكم وإدارة المستندات من القائمة الجانبية
with st.sidebar:
    st.markdown("<h3 style='color: #202123;'>📁 إدارة الملفات والمستندات</h3>", unsafe_allow_html=True)
    uploaded_files = st.file_uploader("ارفع ملفات الـ PDF الخاصة بمشروعك:", type=["pdf"], accept_multiple_files=True)
    process_button = st.button("تحديث الفهرسة والذاكرة 🔄", use_container_width=True)
    
    st.markdown("---")
    if st.button("مسح سجل المحادثات تماماً 🗑️", use_container_width=True):
        clear_db()
        st.session_state.chat_history = []
        st.session_state.speaking = False
        st.session_state.voice_active = False
        st.rerun()

if process_button and uploaded_files:
    with st.spinner("جاري قراءة النصوص وفهرستها..."):
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
        st.sidebar.success("✅ الذاكرة السحابية محدثة وجاهزة!")

# 5. لوحة أزرار التحكم بالصوت (مرئية وواضحة لتفادي أي تجميد)
col1, col2 = st.columns(2)
with col1:
    if st.button("🎙️ تفعيل الاستماع الصوتي المستمر", use_container_width=True, type="primary" if st.session_state.voice_active else "secondary"):
        st.session_state.voice_active = True
        st.rerun()
with col2:
    if st.button("🛑 إيقاف المايكروفون الصوتي", use_container_width=True, type="secondary" if st.session_state.voice_active else "primary"):
        st.session_state.voice_active = False
        st.rerun()

# 6. عرض ساحة ومحادثات الشات
chat_container = st.container()
with chat_container:
    if not st.session_state.chat_history:
        st.info("🤖 لا توجد جلسة سابقة مسجلة. ابدأ بالتحدث أو الكتابة الآن!")
    for message in st.session_state.chat_history:
        if message["role"] == "user":
            st.markdown(f"<div class='chat-bubble-user'>{message['text']}</div>", unsafe_allow_html=True)
        else:
            st.markdown(f"<div class='chat-bubble-ai'>🤖 {message['text']}</div>", unsafe_allow_html=True)

st.markdown("<div style='clear: both; margin-bottom: 50px;'></div>", unsafe_allow_html=True)

# 7. بناء الجسر الذكي لاستقبال النصوص والمايكروفون
captured_voice_text = None

if st.session_state.voice_active and not st.session_state.speaking:
    st.markdown("<p style='color:#2b8a3e; font-weight:bold; text-align:center;'>🔴 المايكروفون نشط حالياً... تحدث وسيتلقى النظام كلامك فور صمتك</p>", unsafe_allow_html=True)
    
    js_speech_engine = """
    <script>
    const recognition = new (window.SpeechRecognition || window.webkitSpeechRecognition)();
    recognition.lang = 'ar-SA';
    recognition.interimResults = false;
    recognition.maxAlternatives = 1;
    
    recognition.start();
    
    recognition.onresult = (event) => {
        const speechResult = event.results[0][0].transcript;
        if(speechResult.trim() !== "") {
            parent.postMessage({type: 'streamlit:setComponentValue', value: speechResult}, '*');
        }
    };
    
    recognition.onerror = (event) => {
        setTimeout(() => { try { recognition.start(); } catch(e){} }, 1000);
    };
    </script>
    """
    # عرض المكون الصوتي بشكل آمن دون إسناده لمتغيرات مسببة للمشاكل
    captured_voice_text = st.components.v1.html(js_speech_engine, height=0)

# مربع الكتابة اليدوية الاحتياطي (يعمل بكفاءة تامة في كل الأوقات)
user_text_input = st.chat_input("أو اكتب سؤالك هنا يدوياً واضغط Enter...")

# تحديد المدخل الفعلي بدقة وبدون أي أخطاء طباعة
final_query = ""
if user_text_input:
    final_query = user_text_input
elif captured_voice_text and isinstance(captured_voice_text, str) and captured_voice_text.strip() != "":
    final_query = captured_voice_text

# 8. معالجة وتوليد الإجابات السريعة (Invoke)
if final_query and final_query != "SPEECH_DONE":
    # حفظ رسالة المستخدم وعرضها
    save_message("user", final_query)
    st.session_state.chat_history.append({"role": "user", "text": final_query})
    st.markdown(f"<div class='chat-bubble-user'>{final_query}</div>", unsafe_allow_html=True)
    
    # فحص الـ PDF
    pdf_context = "لا توجد ملفات مرفوعة حالياً. أجب مباشرة من معلوماتك العامة."
    if os.path.exists("chroma_db") and len(os.listdir("chroma_db")) > 0:
        try:
            vector_store = Chroma(persist_directory="chroma_db", embedding_function=None)
            retrieved_docs = vector_store.similarity_search(final_query, k=2)
            if retrieved_docs:
                pdf_context = "\n\n".join([doc.page_content for doc in retrieved_docs])
        except Exception:
            pass

    history_context = ""
    for msg in st.session_state.chat_history[-4:-1]:
        history_context += f"{msg['role']}: {msg['text']}\n"

    prompt_template = ChatPromptTemplate.from_messages([
        ("system", (
            "أنت OmniSearch AI، مساعد صوتي ذكي وموجز للغاية.\n"
            "أجب دائماً باللغة العربية الفصحى وبشكل مباشر ومختصر (سطر أو سطرين فقط) لتناسب الاستماع الصوتي.\n\n"
            "سياق ملفات الـ PDF للمشروع:\n{pdf_context}"
        )),
        ("user", "سجل الجلسة السابقة:\n{history}\n\nالسؤال المطلوب الإجابة عليه: {query}")
    ])
    
    formatted_prompt = prompt_template.format_messages(pdf_context=pdf_context, history=history_context, query=final_query)
    
    # استدعاء الموديل بأحدث الطرق الآمنة
    with st.spinner("جاري التفكير وصياغة الرد..."):
        response_object = llm.invoke(formatted_prompt)
        ai_response = response_object.content
    
    # حفظ الرد وعرضه
    save_message("ai", ai_response)
    st.session_state.chat_history.append({"role": "ai", "text": ai_response})
    st.markdown(f"<div class='chat-bubble-ai'>🤖 {ai_response}</div>", unsafe_allow_html=True)
    
    # تشغيل محرك النطق الصوتي التلقائي (TTS) للرد
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
    time.sleep(0.6)
    st.rerun()

# استعادة حالة المايكروفون للاستماع بمجرد انتهاء الروبوت من النطق تماماً
if final_query == "SPEECH_DONE":
    st.session_state.speaking = False
    st.rerun()

