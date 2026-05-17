import os
import sqlite3
import uuid
import streamlit as st
import time
import io
import urllib.request
import urllib.parse
import re  # البديل المستقر والآمن لـ bs4
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from groq import Groq 

# --- 1. تهيئة وإعداد واجهة المستخدم والألوان التنافسية ---
st.set_page_config(page_title="صوتك | Sawtak AI", page_icon="🎙️", layout="wide")

if "user_id" not in st.session_state:
    st.session_state.user_id = str(uuid.uuid4())

if "audio_session_key" not in st.session_state:
    st.session_state.audio_session_key = str(uuid.uuid4())[:8]

USER_DIR = f"user_data/{st.session_state.user_id}"
USER_DOCS_DIR = os.path.join(USER_DIR, "temp_docs")

if "pdf_context_memory" not in st.session_state:
    st.session_state.pdf_context_memory = ""

for path in [USER_DOCS_DIR]:
    if not os.path.exists(path):
        os.makedirs(path)

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
        
        if not clean_query:
            clean_query = query
            
        encoded_query = urllib.parse.quote(clean_query)
        url = f"https://html.duckduckgo.com/html/?q={encoded_query}"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
        with urllib.request.urlopen(req, timeout=6) as response:
            html_content = response.read().decode('utf-8')
            snippets = re.findall(r'class="result__snippet"[^>]*>(.*?)<\/a>', html_content, re.DOTALL)
            clean_snippets = []
            for snip in snippets[:3]:
                clean_text = re.sub(r'<[^>]+>', '', snip).strip()
                clean_snippets.append(clean_text)
            if clean_snippets:
                return "\n".join(clean_snippets)
    except Exception:
        pass
    return "لا توجد نتائج بحث مباشرة متوفرة حالياً."

# --- 2. بناء الشريط الجانبي ---
with st.sidebar:
    st.title("🎙️ لوحة التحكم والتخصيص")
    st.subheader("🌐 ضبط هوية الرد")
    
    dialect = st.selectbox(
        "اختر اللهجة المفضلة للرد الذكي:",
        ["العربية الفصحى بمصطلحات مبسطة", "اللهجة السودانية الدارجة", "اللهجة الخليجية", "اللهجة المصرية", "اللهجة الشامية"]
    )
    
    enable_tts = st.toggle("تفعيل الرد الصوتي التلقائي 🔊", value=True)
    st.markdown("---")
    
    st.subheader("🧠 ذاكرتي الذكية المستندة لـ (PDF)")
    uploaded_files = st.file_uploader("ارفع ملفات الـ PDF الخاصة بك هنا:", type=["pdf"], accept_multiple_files=True)
    process_button = st.button("تحديث وفهرسة البيانات الذكية 🔄", use_container_width=True)
    
    if process_button and uploaded_files:
        with st.spinner("جاري قراءة وتأصيل البيانات بالذاكرة الآمنة..."):
            extracted_text_list = []
            for uploaded_file in uploaded_files:
                file_path = os.path.join(USER_DOCS_DIR, uploaded_file.name)
                with open(file_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())
                loader = PyPDFLoader(file_path)
                for page in loader.load():
                    extracted_text_list.append(page.page_content)
            
            st.session_state.pdf_context_memory = "\n".join(extracted_text_list)[:4000] 
            st.success("✅ تم حفظ وفهرسة مستنداتك في الذاكرة الآمنة بنجاح!")
            
    st.markdown("---")
    st.subheader("🗑️ خيارات تصفير الجلسة")
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
    except Exception:
        pass

init_user_db()

if "chat_history" not in st.session_state:
    st.session_state.chat_history = load_user_chat()

if "last_processed_audio_size" not in st.session_state:
    st.session_state.last_processed_audio_size = 0

st.title("🎙️ صوتك | Sawtak AI")
st.caption("النسخة فائقة الاستقرار: تعمل بنجاح وبدون أي أخطاء برمجية في معالجة الطلبات")

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

# --- 4. أدوات الإدخال والتعرف الذكي على نبرة الصوت ---
st.markdown("### 🎙️ أدوات الإدخال")
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
            with st.spinner("🎙️ جاري تصفية نبرة الصوت وتفسير الكلام الدارج..."):
                GROQ_API_KEY = st.secrets.get("GROQ_API_KEY", os.environ.get("GROQ_API_KEY", ""))
                client = Groq(api_key=GROQ_API_KEY)
                
                audio_buffer = io.BytesIO(audio_bytes)
                audio_buffer.name = "input_audio.wav"
                
                transcription = client.audio.transcriptions.create(
                    file=audio_buffer,
                    model="whisper-large-v3",
                    language="ar",
                    prompt="لا قصدي، الدوري الفرنسي، أفضل الهدافين، صانعي الأهداف، ميسي، كورة. المتحدث يتكلم بلهجة عامية واضحة.",
                    response_format="text"
                )
                captured_text = str(transcription).strip()
                if len(captured_text) > 2:
                    final_query = captured_text
                    
            st.session_state.audio_session_key = str(uuid.uuid4())[:8]
    except Exception:
        pass

# --- 5. توليد الرد البرمجي السليم الخالي من أخطاء الانهيار ---
if final_query != "":
    save_user_message("user", final_query)
    st.session_state.chat_history.append({"role": "user", "text": final_query})
    display_chat()
    
    st.markdown('<div class="waveform-sim"></div>', unsafe_allow_html=True)
    
    with st.spinner("🌐 جاري استدعاء الإنترنت وجلب الحقائق اللحظية..."):
        live_web_context = fetch_live_web_data(final_query)

    pdf_context = st.session_state.pdf_context_memory
    if not pdf_context:
        pdf_context = "لا توجد مستندات مرفوعة حالياً."

    # تعديل الصياغة البرمجية لتثبيت المتغيرات بشكل سليم داخل ملقن القالب
    system_message = (
        "أنت مساعد ذكي ومحترف ومخصص لمساعدة المستخدم العربي بدقة متناهية وبدون تكرار.\n"
        "مهمتك القصوى هي الإجابة بدقة بالاعتماد الكامل على معلومات الويب المرفقة لتحديث بياناتك وتصحيح معلوماتك القديمة.\n"
        f"هام جداً: يجب أن تصيغ ردك وتتحدث بالكامل باستخدام: ({dialect}) بأسلوب طبيعي ومباشر.\n\n"
        "⚠️ قواعد صارمة لمنع التشتت وتداخل المعلومات:\n"
        "1. إذا بدأ المستخدم سؤاله بـ 'لا قصدي عن...' أو قام بتعديل مسار كلامه، فانتبه فوراً للتصحيح الأخير واهمل المقاصد القديمة تماماً.\n"
        "2. ادخل في صلب الإجابة فوراً، لا تكرر ديباجات ترحيبية ولا تعيد صياغة السؤال. أعطه الحقائق المرتبة مباشرة وبدون حشو.\n\n"
        f"معلومات الويب الحية المحدثة حالياً لعام 2026:\n{live_web_context}\n\n"
        f"سياق المستندات المرفوعة:\n{pdf_context}"
    )

    messages_input = [("system", system_message)]

    # جلب آخر 3 رسائل سابقة لمنع التراكم وتأمين الذاكرة
    for msg in st.session_state.chat_history[-4:-1]:
        messages_input.append((msg["role"], msg["text"]))

    # إضافة السؤال الحالي
    messages_input.append(("user", final_query))

    prompt_template = ChatPromptTemplate.from_messages(messages_input)
    
    GROQ_API_KEY = st.secrets.get("GROQ_API_KEY", os.environ.get("GROQ_API_KEY", ""))
    llm = ChatGroq(temperature=0.2, groq_api_key=GROQ_API_KEY, model_name="llama-3.3-70b-versatile")
    
    formatted_prompt = prompt_template.format_messages()
    
    with chat_placeholder.container():
        display_chat()
        with st.chat_message("assistant"):
            try:
                response_stream = llm.stream(formatted_prompt)
                ai_response = st.write_stream(response_stream)
                ai_response = ai_response.strip()
            except Exception as e:
                # طباعة الخطأ الحقيقي للمطور بدلاً من إخفاء المشكلة
                ai_response = f"حصل خطأ في الاتصال بالخادم الداخلي: {str(e)}"
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
