import os
import sqlite3
import uuid
import streamlit as st
import time
import io
import base64
import urllib.request
import urllib.parse
import re  
from langchain_community.document_loaders import PyPDFLoader
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from groq import Groq 

# --- 1. تهيئة وإعداد الجلسة واللغات المتعددة ---
st.set_page_config(page_title="🎙️ Sawtak AI Pro", page_icon="🎙️", layout="wide")

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

LANG_DICT = {
    "ar": {
        "title": "🎙️ صوتك | Sawtak AI Pro",
        "caption": "الجيل الجديد للمساعدات الذكية واجهة المحترفين الفائقة",
        "sidebar_settings": "⚙️ الإعدادات واللغة",
        "app_lang": "لغة واجهة التطبيق:",
        "ai_dialect": "لهجة رد الذكاء الاصطناعي (للعربية):",
        "pdf_section": "🧠 ذاكرة المستندات (PDF)",
        "pdf_upload": "ارفع ملفات الـ PDF الخاصة بك:",
        "pdf_btn": "تحديث وفهرسة الذاكرة 🔄",
        "pdf_success": "✅ تم حفظ وفهرسة مستنداتك بنجاح!",
        "reset_section": "🗑️ إدارة الجلسة",
        "reset_btn": "مسح سجل الحوار بالكامل",
        "reset_success": "تم تصفير التطبيق بنجاح!",
        "input_section": "💻 منصة التحكم الذكية بالمدخلات",
        "audio_label": "🎙️ تحدث الآن بلهجتك الطبيعية مباشرة:",
        "image_label": "📸 ارفع أو صوّر صورة (لتحليلها أو حلها):",
        "chat_placeholder": "اكتب سؤالك هنا يدوياً حول الصورة أو النص...",
        "spinner_web": "🌐 جاري معالجة البيانات والتحقق منها...",
        "spinner_whisper": "🎙️ جاري تفسير الكلام وتحويله لنص...",
        "error_server": "حصل خطأ في الاتصال بالخادم الداخلي أو تجاوز الحد المسموح.",
        "pdf_empty": "لا توجد مستندات مرفوعة حالياً."
    }
}

T = LANG_DICT["ar"] # الاعتماد على الواجهة العربية المحدثة

# --- 2. هندسة الواجهة الفائقة للمحترفين بتصميم الـ Full-Stack (CSS) ---
st.markdown("""
    <style>
    /* تهيئة الخلفية العامة وتثبيت نمط المنصات العالمية */
    .stApp { background-color: #0b0f19 !important; color: #f3f4f6 !important; }
    
    /* تصميم حاوية الشات الفاخرة */
    .chat-container { display: flex; flex-direction: column; gap: 20px; padding: 15px; margin-bottom: 100px; }
    
    /* فقاعات مستخدم احترافية بنقوش انسيابية */
    .chat-bubble-user {
        background: linear-gradient(135deg, #2563eb, #1d4ed8);
        color: #ffffff !important; padding: 14px 20px; border-radius: 20px 20px 4px 20px;
        align-self: flex-end; max-width: 75%; margin-left: auto; 
        box-shadow: 0 4px 15px rgba(37, 99, 235, 0.2); font-size: 1.05rem; line-height: 1.5;
    }
    
    /* فقاعات الرد الذكي العميقة مع إطار دقيق */
    .chat-bubble-ai {
        background-color: #161b26; color: #f3f4f6 !important; padding: 16px 22px;
        border-radius: 20px 20px 20px 4px; align-self: flex-start; max-width: 75%;
        margin-right: auto; border: 1px solid #2d3748; 
        box-shadow: 0 4px 12px rgba(0,0,0,0.3); font-size: 1.05rem; line-height: 1.5;
    }
    
    /* خط موجة النطق الصوتي */
    .waveform-sim { 
        height: 4px; background: linear-gradient(90deg, #00f2fe, #4facfe, #00f2fe); 
        border-radius: 2px; margin-bottom: 15px; animation: pulse 2s infinite;
    }
    
    /* تحسين شكل الأزرار الجانبية */
    div.stButton > button {
        background-color: #1e293b !important; border: 1px solid #334155 !important;
        color: #38bdf8 !important; padding: 6px 16px !important; border-radius: 8px !important;
        font-weight: 600; transition: 0.2s all;
    }
    div.stButton > button:hover { background-color: #334155 !important; border-color: #38bdf8 !important; color: #fff !important; }
    
    /* تعديل عناصر الإدخال لتبدو مدمجة */
    .stChatInput { border-top: 1px solid #2d3748 !important; background-color: #0f172a !important; }
    
    h1, h2, h3, p, span, label { color: #f3f4f6 !important; font-family: 'Segoe UI', system-ui, sans-serif; }
    </style>
""", unsafe_allow_html=True)

def identify_text_language(text):
    clean = text.strip().lower()
    if re.search(r'[\u0600-\u06FF]', clean): return "ar"
    if re.search(r'[a-zA-Z]', clean): return "en"
    return "ar"

# --- 3. بناء التحكم الجانبي المحترف ---
with st.sidebar:
    st.title("⚙️ الإعدادات المتقدمة")
    dialect = st.selectbox(
        T["ai_dialect"],
        ["اللهجة السودانية الدارجة", "العربية الفصحى بمصطلحات مبسطة", "اللهجة المصرية", "اللهجة الخليجية", "اللهجة الشامية"]
    )
    
    st.markdown("---")
    st.subheader(T["pdf_section"])
    uploaded_files = st.file_uploader(T["pdf_upload"], type=["pdf"], accept_multiple_files=True)
    if st.button(T["pdf_btn"], use_container_width=True) and uploaded_files:
        with st.spinner("Processing..."):
            extracted_text_list = []
            for uploaded_file in uploaded_files:
                file_path = os.path.join(USER_DOCS_DIR, uploaded_file.name)
                with open(file_path, "wb") as f: f.write(uploaded_file.getbuffer())
                for page in PyPDFLoader(file_path).load(): extracted_text_list.append(page.page_content)
            st.session_state.pdf_context_memory = "\n".join(extracted_text_list)[:4000] 
            st.success(T["pdf_success"])
            
    st.markdown("---")
    if st.button(T["reset_btn"], use_container_width=True):
        db_path = os.path.join(USER_DIR, "personal_chat.db")
        if os.path.exists(db_path):
            conn = sqlite3.connect(db_path, check_same_thread=False)
            conn.cursor().execute("DELETE FROM messages")
            conn.commit()
            conn.close()
        st.session_state.chat_history = []
        st.session_state.last_processed_audio_size = 0
        st.session_state.pdf_context_memory = ""
        st.success(T["reset_success"])
        time.sleep(0.5)
        st.rerun()

# --- 4. إدارة سجل الرسائل وقاعدة البيانات ---
def init_user_db():
    db_path = os.path.join(USER_DIR, "personal_chat.db")
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.cursor().execute("CREATE TABLE IF NOT EXISTS messages (id INTEGER PRIMARY KEY AUTOINCREMENT, role TEXT, text TEXT)")
    conn.commit()
    conn.close()

def load_user_chat():
    db_path = os.path.join(USER_DIR, "personal_chat.db")
    conn = sqlite3.connect(db_path, check_same_thread=False)
    rows = conn.cursor().execute("SELECT role, text FROM messages ORDER BY id ASC").fetchall()
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

st.title(T["title"])
st.caption(T["caption"])

# عرض فقاعات الحوار بالتصميم المحترف الجديد
chat_placeholder = st.container()
with chat_placeholder:
    st.markdown('<div class="chat-container">', unsafe_allow_html=True)
    for index, message in enumerate(st.session_state.chat_history):
        detected_lang = identify_text_language(message["text"])
        text_align = "right" if detected_lang == "ar" else "left"
        direction = "rtl" if detected_lang == "ar" else "ltr"
        
        if message["role"] == "user":
            st.markdown(f"<div class='chat-bubble-user' style='text-align: {text_align}; direction: {direction};'>{message['text']}</div>", unsafe_allow_html=True)
        else:
            st.markdown(f"<div class='chat-bubble-ai' style='text-align: {text_align}; direction: {direction};'>{message['text']}</div>", unsafe_allow_html=True)
            col1, col2 = st.columns([2, 10])
            with col1:
                if st.button("🔊 استمع", key=f"btn_audio_{index}"):
                    st.session_state.play_audio_text = message['text']
    st.markdown('</div>', unsafe_allow_html=True)

# --- 5. أدوات إدخال الوسائط المتعددة (الـ Full-Stack المدمج) ---
st.markdown(f"#### {T['input_section']}")
col_media1, col_media2 = st.columns(2)

with col_media1:
    audio_file = st.audio_input(T["audio_label"], key=f"audio_input_{st.session_state.audio_session_key}")
with col_media2:
    user_image = st.file_uploader(T["image_label"], type=["png", "jpg", "jpeg"])

user_text_input = st.chat_input(T["chat_placeholder"])

final_query = ""

# منطق معالجة الصوت والـ Transcription عبر Whisper
if user_text_input:
    final_query = user_text_input
elif audio_file:
    try:
        audio_bytes = audio_file.read()
        audio_size = len(audio_bytes)
        if audio_size > 7000 and audio_size != st.session_state.last_processed_audio_size:
            st.session_state.last_processed_audio_size = audio_size
            with st.spinner(T["spinner_whisper"]):
                GROQ_API_KEY = st.secrets.get("GROQ_API_KEY", os.environ.get("GROQ_API_KEY", ""))
                client = Groq(api_key=GROQ_API_KEY)
                audio_buffer = io.BytesIO(audio_bytes)
                audio_buffer.name = "input_audio.wav"
                transcription = client.audio.transcriptions.create(
                    file=audio_buffer, model="whisper-large-v3", language=None, response_format="text"
                )
                captured_text = str(transcription).strip()
                if len(captured_text) > 2: final_query = captured_text
            st.session_state.audio_session_key = str(uuid.uuid4())[:8]
    except Exception: pass

if final_query != "":
    save_user_message("user", final_query)
    st.session_state.chat_history.append({"role": "user", "text": final_query})
    st.rerun()

# --- 6. معالجة وتوليد الرد باستخدام موديل الرؤية النشط والمستقر ---
if st.session_state.chat_history and st.session_state.chat_history[-1]["role"] == "user":
    latest_query = st.session_state.chat_history[-1]["text"]
    user_lang = identify_text_language(latest_query)
    GROQ_API_KEY = st.secrets.get("GROQ_API_KEY", os.environ.get("GROQ_API_KEY", ""))
    client = Groq(api_key=GROQ_API_KEY)

    if user_lang == "en":
        system_message = "You are an expert English Vision/Text AI. Analyze the prompt and any uploaded images. Reply ONLY and strictly in English fluidly."
    else:
        system_message = f"أنت خبير ذكاء اصطناعي متمكن. قم بتحليل المدخلات والصور المرفقة إن وجدت، وصغ ردك بالكامل وبشكل طبيعي جداً وبطريقة تفاعلية مبهرة باللهجة التالية: ({dialect})."

    st.markdown('<div class="waveform-sim"></div>', unsafe_allow_html=True)
    
    with chat_placeholder:
        with st.chat_message("assistant"):
            with st.spinner(T["spinner_web"]):
                try:
                    # حالة معالجة وجود صورة مرفوعة (Vision Mode)
                    if user_image is not None:
                        image_bytes = user_image.read()
                        base64_image = base64.b64encode(image_bytes).decode('utf-8')
                        
                        # 🚀 استخدام الموديل الفوري النشط والمستقر وتفادي الخطأ 400 تماماً:
                        chat_completion = client.chat.completions.create(
                            model="llama-3.2-11b-vision-instant",
                            messages=[
                                {"role": "system", "content": system_message},
                                {
                                    "role": "user",
                                    "content": [
                                        {"type": "text", "text": latest_query if latest_query else "Analyze this image and reply in user language"},
                                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                                    ]
                                }
                            ],
                            temperature=0.2
                        )
                        ai_response = chat_completion.choices[0].message.content.strip()
                        st.write(ai_response)
                    
                    # حالة النص أو الصوت فقط
                    else:
                        messages_input = [("system", system_message)]
                        if len(latest_query.strip()) > 15:
                            for msg in st.session_state.chat_history[-3:-1]:
                                messages_input.append((msg["role"], msg["text"]))
                        messages_input.append(("user", latest_query))
                        
                        prompt_template = ChatPromptTemplate.from_messages(messages_input)
                        llm = ChatGroq(temperature=0.3, groq_api_key=GROQ_API_KEY, model_name="llama-3.1-8b-instant")
                        response_stream = llm.stream(prompt_template.format_messages())
                        ai_response = st.write_stream(response_stream).strip()
                        
                except Exception as e:
                    ai_response = f"{T['error_server']}: {str(e)}"
                    st.write(ai_response)
                    
    save_user_message("ai", ai_response)
    st.session_state.chat_history.append({"role": "ai", "text": ai_response})
    st.rerun()

# --- 7. تشغيل النطق الصوتي التلقائي الفوري وعالي الجودة ---
if st.session_state.play_audio_text != "":
    clean_text = st.session_state.play_audio_text.replace("'", "\\'").replace("\n", " ").replace('"', '\\"')
    text_lang = identify_text_language(st.session_state.play_audio_text)
    lang_code = "en-US" if text_lang == "en" else "ar-SA"
    
    js_universal_tts = f"""
    <script>
    window.speechSynthesis.cancel();
    var msg = new SpeechSynthesisUtterance('{clean_text}');
    msg.lang = '{lang_code}';
    msg.rate = 1.0;
    window.speechSynthesis.speak(msg);
    </script>
    """
    st.components.v1.html(js_universal_tts, height=0)
    st.session_state.play_audio_text = ""

