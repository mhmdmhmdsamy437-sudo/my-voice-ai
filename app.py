import os
import sqlite3
import uuid
import streamlit as st
import time
import io
import urllib.request
import urllib.parse
import re  
from langchain_community.document_loaders import PyPDFLoader
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from groq import Groq 

# --- 1. تهيئة وإعداد واجهة المستخدم الكاملة والمستقرة ---
st.set_page_config(page_title="صوتك | Sawtak AI", page_icon="🎙️", layout="wide")

if "user_id" not in st.session_state:
    st.session_state.user_id = str(uuid.uuid4())

if "audio_session_key" not in st.session_state:
    st.session_state.audio_session_key = str(uuid.uuid4())[:8]

USER_DIR = f"user_data/{st.session_state.user_id}"
USER_DOCS_DIR = os.path.join(USER_DIR, "temp_docs")

if "pdf_context_memory" not in st.session_state:
    st.session_state.pdf_context_memory = ""

if "play_audio_text" not in st.session_state:
    st.session_state.play_audio_text = ""

if not os.path.exists(USER_DOCS_DIR):
    os.makedirs(USER_DOCS_DIR)

# الألوان والتنسيقات لفقاعات الشات التقليدية الفخمة
st.markdown("""
    <style>
    .stApp { background-color: #0d1117 !important; color: #f3f4f6 !important; }
    .chat-container { display: flex; flex-direction: column; gap: 16px; padding: 5px; margin-bottom: 20px; }
    .chat-bubble-user {
        background: linear-gradient(135deg, #2563eb, #1d4ed8);
        color: #ffffff !important; padding: 12px 18px; border-radius: 16px 16px 4px 16px;
        align-self: flex-end; max-width: 85%; margin-left: auto; text-align: right;
    }
    .chat-bubble-ai {
        background-color: #161b22; color: #f3f4f6 !important; padding: 14px 20px;
        border-radius: 16px 16px 16px 4px; align-self: flex-start; max-width: 85%;
        margin-right: auto; text-align: right; border: 1px solid #30363d;
        margin-bottom: 2px;
    }
    .waveform-sim { 
        height: 4px; 
        background: linear-gradient(90deg, #00f2fe, #4facfe, #00f2fe); 
        border-radius: 2px; 
        margin-bottom: 15px;
    }
    h1, h2, h3, p, span, label { color: #f3f4f6 !important; }
    </style>
""", unsafe_allow_html=True)

# دالة البحث المباشر المستقرة
def fetch_live_web_data(query):
    try:
        clean_query = re.sub(r'^(لا قصدي عن|لا قصدي|قصدي عن|قصدي|اسمع|اسمعني|تعديل|لا لا)\s*', '', query, flags=re.IGNORECASE).strip()
        clean_query = clean_query.replace("البوربون", "").replace("بوربون", "").strip()
        if not clean_query: clean_query = query
        encoded_query = urllib.parse.quote(clean_query)
        url = f"https://html.duckduckgo.com/html/?q={encoded_query}"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
        with urllib.request.urlopen(req, timeout=6) as response:
            html_content = response.read().decode('utf-8')
            snippets = re.findall(r'class="result__snippet"[^>]*>(.*?)<\/a>', html_content, re.DOTALL)
            if snippets: return "\n".join([re.sub(r'<[^>]+>', '', s).strip() for s in snippets[:3]])
    except Exception: pass
    return "لا توجد نتائج بحث مباشرة متوفرة حالياً."

# --- 2. بناء الشريط الجانبي ---
with st.sidebar:
    st.title("🎙️ لوحة التحكم والتخصيص")
    dialect = st.selectbox(
        "اختر اللهجة المفضلة للرد الذكي:",
        ["العربية الفصحى بمصطلحات مبسطة", "اللهجة السودانية الدارجة", "اللهجة الخليجية", "اللهجة المصرية", "اللهجة الشامية"]
    )
    st.markdown("---")
    st.subheader("🧠 ذاكرة الـ (PDF)")
    uploaded_files = st.file_uploader("ارفع ملفات الـ PDF الخاصة بك هنا:", type=["pdf"], accept_multiple_files=True)
    if st.button("تحديث وفهرسة البيانات الذكية 🔄", use_container_width=True) and uploaded_files:
        with st.spinner("جاري قراءة وتأصيل البيانات..."):
            extracted_text_list = []
            for uploaded_file in uploaded_files:
                file_path = os.path.join(USER_DOCS_DIR, uploaded_file.name)
                with open(file_path, "wb") as f: f.write(uploaded_file.getbuffer())
                for page in PyPDFLoader(file_path).load(): extracted_text_list.append(page.page_content)
            st.session_state.pdf_context_memory = "\n".join(extracted_text_list)[:4000] 
            st.success("✅ تم حفظ وفهرسة مستنداتك بنجاح!")
            
    st.markdown("---")
    if st.button("تفريغ ومسح سجل الحوار بالكامل", use_container_width=True):
        db_path = os.path.join(USER_DIR, "personal_chat.db")
        if os.path.exists(db_path):
            conn = sqlite3.connect(db_path, check_same_thread=False)
            conn.cursor().execute("DELETE FROM messages")
            conn.commit()
            conn.close()
        st.session_state.chat_history = []
        st.session_state.last_processed_audio_size = 0
        st.session_state.pdf_context_memory = ""
        st.success("تم تصفير التطبيق بنجاح!")
        time.sleep(0.5)
        st.rerun()

# --- 3. إدارة رسائل قاعدة البيانات المحلية ---
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
    except Exception: pass

init_user_db()
if "chat_history" not in st.session_state: st.session_state.chat_history = load_user_chat()
if "last_processed_audio_size" not in st.session_state: st.session_state.last_processed_audio_size = 0

st.title("🎙️ صوتك | Sawtak AI")
st.caption("النسخة المتطورة: أزرار نطق اختيارية مدمجة أسفل كل إجابة لمحاكاة ChatGPT")

# حاوية عرض الشات مع أزرار التحكم الصوتي أسفل إجابة الـ AI
chat_placeholder = st.container()

with chat_placeholder:
    st.markdown("<div class='chat-container'>", unsafe_allow_html=True)
    for index, message in enumerate(st.session_state.chat_history):
        if message["role"] == "user":
            st.markdown(f"<div class='chat-bubble-user'>{message['text']}</div>", unsafe_allow_html=True)
        else:
            st.markdown(f"<div class='chat-bubble-ai'>{message['text']}</div>", unsafe_allow_html=True)
            # زر قراءة مخصص أسفل رد الـ AI ومحاذاته لليمين تماماً زي ChatGPT
            col1, col2 = st.columns([1, 15])
            with col1:
                if st.button("🔊", key=f"tts_btn_{index}", help="اضغط للاستماع إلى هذه الإجابة"):
                    st.session_state.play_audio_text = message['text']
    st.markdown("</div>", unsafe_allow_html=True)

# --- 4. أدوات الإدخال الكاملة (صوت + نص) دون اختفاء ---
st.markdown("### 🎙 snuff أدوات الإدخال")
audio_file = st.audio_input("تحدث الآن بلهجتك الطبيعية المعتادة:", key=f"audio_input_{st.session_state.audio_session_key}")
user_text_input = st.chat_input("أو اكتب سؤالك هنا يدوياً...")

final_query = ""

if user_text_input:
    final_query = user_text_input
elif audio_file:
    try:
        audio_bytes = audio_file.read()
        audio_size = len(audio_bytes)
        
        if audio_size > 7000 and audio_size != st.session_state.last_processed_audio_size:
            st.session_state.last_processed_audio_size = audio_size
            with st.spinner("🎙️ جاري تفسير الكلام الدارج..."):
                GROQ_API_KEY = st.secrets.get("GROQ_API_KEY", os.environ.get("GROQ_API_KEY", ""))
                client = Groq(api_key=GROQ_API_KEY)
                
                audio_buffer = io.BytesIO(audio_bytes)
                audio_buffer.name = "input_audio.wav"
                
                transcription = client.audio.transcriptions.create(
                    file=audio_buffer,
                    model="whisper-large-v3",
                    language="ar",
                    prompt="لا قصدي، المتحدث يتكلم بلهجة عامية وعفوية.",
                    response_format="text"
                )
                captured_text = str(transcription).strip()
                if len(captured_text) > 2:
                    final_query = captured_text
            st.session_state.audio_session_key = str(uuid.uuid4())[:8]
    except Exception: pass

# --- 5. توليد الرد البرمجي السليم وضخه في الواجهة المكتوبة ---
if final_query != "":
    save_user_message("user", final_query)
    st.session_state.chat_history.append({"role": "user", "text": final_query})
    st.rerun()

# تشغيل الـ AI عند وجود سؤال جديد
if st.session_state.chat_history and st.session_state.chat_history[-1]["role"] == "user":
    latest_query = st.session_state.chat_history[-1]["text"]
    
    st.markdown('<div class="waveform-sim"></div>', unsafe_allow_html=True)
    with st.spinner("🌐 جاري جلب الحقائق اللحظية..."):
        live_web_context = fetch_live_web_data(latest_query)

    pdf_context = st.session_state.pdf_context_memory if st.session_state.pdf_context_memory else "لا توجد مستندات."

    system_message = (
        "أنت مساعد ذكي ومحترف ومخصص لمساعدة المستخدم العربي بدقة.\n"
        f"هام جداً: يجب أن تصيغ ردك وتتحدث بالكامل باستخدام: ({dialect}) بأسلوب مباشر.\n"
        "1. ادخل في صلب الإجابة فوراً بدون ديباجات ترحيبية.\n"
        f"معلومات الويب الحية لعام 2026:\n{live_web_context}\n\n"
        f"سياق المستندات:\n{pdf_context}"
    )

    messages_input = [("system", system_message)]
    for msg in st.session_state.chat_history[-4:-1]:
        messages_input.append((msg["role"], msg["text"]))
    messages_input.append(("user", latest_query))

    prompt_template = ChatPromptTemplate.from_messages(messages_input)
    GROQ_API_KEY = st.secrets.get("GROQ_API_KEY", os.environ.get("GROQ_API_KEY", ""))
    llm = ChatGroq(temperature=0.2, groq_api_key=GROQ_API_KEY, model_name="llama-3.3-70b-versatile")
    
    with chat_placeholder:
        with st.chat_message("assistant"):
            try:
                response_stream = llm.stream(prompt_template.format_messages())
                ai_response = st.write_stream(response_stream).strip()
            except Exception as e:
                ai_response = f"حصل خطأ في الاتصال بالخادم: {str(e)}"
                st.write(ai_response)
                
    save_user_message("ai", ai_response)
    st.session_state.chat_history.append({"role": "ai", "text": ai_response})
    st.rerun()

# --- 6. تنفيذ النطق الصوتي عند ضغط الزر فقط (طريقة ChatGPT) ---
if st.session_state.play_audio_text != "":
    clean_text = st.session_state.play_audio_text.replace("'", "\\'").replace("\n", " ")
    js_universal_tts = f"""
    <script>
    window.speechSynthesis.cancel();
    var msg = new SpeechSynthesisUtterance('{clean_text}');
    msg.lang = 'ar-SA';
    msg.rate = 1.0;
    window.speechSynthesis.speak(msg);
    </script>
    """
    st.components.v1.html(js_universal_tts, height=0)
    # تصفير المتغير حتى لا يتكرر النطق تلقائياً عند إعادة تحميل الصفحة
    st.session_state.play_audio_text = ""
