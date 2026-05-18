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

# --- 1. تهيئة وإعداد الجلسة واللغات المتعددة ---
st.set_page_config(page_title="🎙️ Sawtak AI", page_icon="🎙️", layout="wide")

if "user_id" not in st.session_state:
    st.session_state.user_id = str(uuid.uuid4())

if "audio_session_key" not in st.session_state:
    st.session_state.audio_session_key = str(uuid.uuid4())[:8]

USER_DIR = f"user_data/{st.session_state.user_id}"
USER_DOCS_DIR = os.path.join(USER_DIR, "temp_docs")

if "pdf_context_memory" not in st.session_state:
    st.session_state.pdf_context_memory = ""

if not os.path.exists(USER_DOCS_DIR):
    os.makedirs(USER_DOCS_DIR)

# قاموس الترجمة الكامل لواجهة التطبيق ليدعم جميع المستخدمين
LANG_DICT = {
    "ar": {
        "title": "🎙️ صوتك | Sawtak AI",
        "caption": "الجيل الجديد للمساعدات الذكية المتعددة اللغات",
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
        "input_section": "🎙️ أدوات الإدخال والحديث",
        "audio_label": "تحدث الآن بلهجتك الطبيعية:",
        "chat_placeholder": "أو اكتب سؤالك هنا يدوياً...",
        "spinner_web": "🌐 جاري جلب الحقائق اللحظية...",
        "spinner_whisper": "🎙️ جاري تفسير الكلام...",
        "error_server": "حصل خطأ في الاتصال بالخادم الداخلي.",
        "pdf_empty": "لا توجد مستندات مرفوعة حالياً."
    },
    "en": {
        "title": "🎙️ Sawtak AI",
        "caption": "The next generation of multilingual AI assistants",
        "sidebar_settings": "⚙️ Settings & Language",
        "app_lang": "App Interface Language:",
        "ai_dialect": "AI Arabic Dialect Response:",
        "pdf_section": "🧠 Document Memory (PDF)",
        "pdf_upload": "Upload your PDF files:",
        "pdf_btn": "Update & Index Memory 🔄",
        "pdf_success": "✅ Documents indexed successfully!",
        "reset_section": "🗑️ Session Management",
        "reset_btn": "Clear Entire Chat History",
        "reset_success": "Application reset successfully!",
        "input_section": "🎙️ Input Tools",
        "audio_label": "Speak now in your natural language:",
        "chat_placeholder": "Or type your question here manually...",
        "spinner_web": "🌐 Fetching live facts from the web...",
        "spinner_whisper": "🎙️ Translating and processing voice...",
        "error_server": "An error occurred while connecting to the server.",
        "pdf_empty": "No documents uploaded yet."
    },
    "fr": {
        "title": "🎙️ Sawtak AI",
        "caption": "La nouvelle génération d'assistants IA multilingues",
        "sidebar_settings": "⚙️ Paramètres et Langue",
        "app_lang": "Langue de l'interface:",
        "ai_dialect": "Dialecte arabe de l'IA:",
        "pdf_section": "🧠 Mémoire de Documents (PDF)",
        "pdf_upload": "Déposez vos fichiers PDF ici:",
        "pdf_btn": "Mettre à jour la mémoire 🔄",
        "pdf_success": "✅ Documents indexés avec succès!",
        "reset_section": "🗑️ Gestion de Session",
        "reset_btn": "Effacer tout l'historique",
        "reset_success": "Application réinitialisée avec succès!",
        "input_section": "🎙️ Outils d'entrée",
        "audio_label": "Parlez maintenant naturellement:",
        "chat_placeholder": "Ou tapez votre question ici manuellement...",
        "spinner_web": "🌐 Recherche d'informations en direct...",
        "spinner_whisper": "🎙️ Traitement de la voix en cours...",
        "error_server": "Une erreur est survenue lors de la connexion au serveur.",
        "pdf_empty": "Aucun document téléchargé pour le moment."
    }
}

# --- 2. تصميم الواجهة بـ CSS فخم يطابق روح الأناقة في ChatGPT ---
st.markdown("""
    <style>
    .stApp { background-color: #0d1117 !important; color: #f3f4f6 !important; }
    .chat-container { display: flex; flex-direction: column; gap: 20px; padding: 10px; margin-bottom: 20px; }
    
    /* فقاعات الحوار المودرن */
    .chat-bubble-user {
        background: linear-gradient(135deg, #2563eb, #1d4ed8);
        color: #ffffff !important; padding: 14px 20px; border-radius: 18px 18px 4px 18px;
        align-self: flex-end; max-width: 80%; margin-left: auto; box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    }
    .chat-bubble-ai {
        background-color: #161b22; color: #f3f4f6 !important; padding: 16px 22px;
        border-radius: 18px 18px 18px 4px; align-self: flex-start; max-width: 80%;
        margin-right: auto; border: 1px solid #30363d; position: relative;
        box-shadow: 0 4px 12px rgba(0,0,0,0.1);
    }
    
    /* تصميم الزر الصوتي المخفي الذكي ليوضع داخل الفقاعة مثل التطبيقات العالمية */
    .tts-player-btn {
        background: #21262d; border: 1px solid #30363d; color: #58a6ff !important;
        padding: 4px 10px; border-radius: 6px; font-size: 0.85rem; cursor: pointer;
        display: inline-flex; align-items: center; gap: 5px; margin-top: 8px; transition: 0.2s;
    }
    .tts-player-btn:hover { background: #30363d; color: #58a6ff !important; }
    
    .waveform-sim { 
        height: 4px; background: linear-gradient(90deg, #00f2fe, #4facfe, #00f2fe); 
        border-radius: 2px; margin-bottom: 15px;
    }
    h1, h2, h3, p, span, label { color: #f3f4f6 !important; }
    </style>
""", unsafe_allow_html=True)

# دالة البحث المباشر المستقرة
def fetch_live_web_data(query):
    try:
        clean_query = re.sub(r'^(لا قصدي عن|لا قصدي|قصدي عن|قصدي|اسمع|اسمعني|تعديل|لا لا)\s*', '', query, flags=re.IGNORECASE).strip()
        if not clean_query: clean_query = query
        encoded_query = urllib.parse.quote(clean_query)
        url = f"https://html.duckduckgo.com/html/?q={encoded_query}"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
        with urllib.request.urlopen(req, timeout=5) as response:
            html_content = response.read().decode('utf-8')
            snippets = re.findall(r'class="result__snippet"[^>]*>(.*?)<\/a>', html_content, re.DOTALL)
            if snippets: return "\n".join([re.sub(r'<[^>]+>', '', s).strip() for s in snippets[:3]])
    except Exception: pass
    return "No live web results available."

# دالة كشف لغة النص برمجياً لتحديد نطق الـ TTS المناسب تلقائياً
def detect_lang_code(text):
    # إذا كان النص يحتوي على حروف فرنسية مميزة
    if re.search(r'[àâçéèêëîïôûùüÿæœ]', text, re.IGNORECASE):
        return "fr-FR"
    # إذا كان النص يحتوي على حروف إنجليزية وليس به حروف عربية
    elif re.search(r'[a-zA-Z]', text) and not re.search(r'[\u0600-\u06FF]', text):
        return "en-US"
    return "ar-SA"

# --- 3. بناء التحكم الجانبي ودعم اللغات الدولي ---
with st.sidebar:
    st.title("⚙️ Control Panel")
    
    # اختيار لغة واجهة التطبيق
    app_lang = st.selectbox("🌐 App Language / لغة التطبيق:", ["ar", "en", "fr"])
    T = LANG_DICT[app_lang] # جلب نصوص الواجهة المختارة
    
    st.subheader(T["sidebar_settings"])
    dialect = st.selectbox(
        T["ai_dialect"],
        ["العربية الفصحى بمصطلحات مبسطة", "اللهجة السودانية الدارجة", "اللهجة الخليجية", "اللهجة المصرية", "اللهجة الشامية"]
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

# --- 4. إدارة قاعدة البيانات وسجل الرسائل ---
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

# عنوان التطبيق الرئيسي
st.title(T["title"])
st.caption(T["caption"])

# عرض فقاعات الحوار مع زر الصوت المدمج بداخل الـ HTML بشكل احترافي رائع
chat_placeholder = st.container()
with chat_placeholder:
    st.markdown("<div class='chat-container'>", unsafe_allow_html=True)
    for index, message in enumerate(st.session_state.chat_history):
        if message["role"] == "user":
            st.markdown(f"<div class='chat-bubble-user'>{message['text']}</div>", unsafe_allow_html=True)
        else:
            # تنظيف النص وتجهيزه للجافا سكريبت لمنع أي توقف
            clean_msg = message['text'].replace("'", "\\'").replace("\n", " ").replace('"', '\\"')
            lang_code = detect_lang_code(message['text'])
            
            # بناء كود الـ HTML المخصص لدمج زر الصوت الصغير الأنيق أسفل نص الرد مباشرة
            ai_html = f"""
            <div class='chat-bubble-ai'>
                <div>{message['text']}</div>
                <button class='tts-player-btn' onclick="
                    window.speechSynthesis.cancel();
                    var msg = new SpeechSynthesisUtterance('{clean_msg}');
                    msg.lang = '{lang_code}';
                    msg.rate = 1.0;
                    window.speechSynthesis.speak(msg);
                ">🔊 Listen / استمع</button>
            </div>
            """
            st.markdown(ai_html, unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

# --- 5. استقبال مدخلات المستخدم العفوية (نص وصوت) ---
st.markdown(f"### {T['input_section']}")
audio_file = st.audio_input(T["audio_label"], key=f"audio_input_{st.session_state.audio_session_key}")
user_text_input = st.chat_input(T["chat_placeholder"])

final_query = ""

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
                    file=audio_buffer,
                    model="whisper-large-v3",
                    language=None,  # جعل الأداة تتعرف تلقائياً على لغة المتحدث (عربي، فرنسي، إنجليزي)
                    prompt="The speaker can switch between Arabic, English, or French naturally.",
                    response_format="text"
                )
                captured_text = str(transcription).strip()
                if len(captured_text) > 2:
                    final_query = captured_text
            st.session_state.audio_session_key = str(uuid.uuid4())[:8]
    except Exception: pass

# حفظ الرسالة الجديدة وإعادة تحميل الصفحة لضمان ظهور فقاعتها فوراً
if final_query != "":
    save_user_message("user", final_query)
    st.session_state.chat_history.append({"role": "user", "text": final_query})
    st.rerun()

# --- 6. توليد واستقبال رد الـ AI المستقر ---
if st.session_state.chat_history and st.session_state.chat_history[-1]["role"] == "user":
    latest_query = st.session_state.chat_history[-1]["text"]
    
    st.markdown('<div class="waveform-sim"></div>', unsafe_allow_html=True)
    with st.spinner(T["spinner_web"]):
        live_web_context = fetch_live_web_data(latest_query)

    pdf_context = st.session_state.pdf_context_memory if st.session_state.pdf_context_memory else T["pdf_empty"]

    # صياغة توجيه احترافي عالمي يدعم اللغات الثلاث بطلاقة تامة
    system_message = (
        "You are an advanced, elite multilingual AI assistant. You must detect the language of the user's question and reply perfectly in the exact same language (Arabic, English, or French).\n"
        f"If the response language is Arabic, you must strictly formulate your output using the following dialect: ({dialect}).\n"
        "Do not include any greeting phrases or preambles, answer the core of the question directly with clear formatting.\n\n"
        f"Live Web Context (Year 2026):\n{live_web_context}\n\n"
        f"Uploaded PDF Documents Context:\n{pdf_context}"
    )

    messages_input = [("system", system_message)]
    # جلب الحوار السابق لمنع التشتت
    for msg in st.session_state.chat_history[-4:-1]:
        messages_input.append((msg["role"], msg["text"]))
    messages_input.append(("user", latest_query))

    prompt_template = ChatPromptTemplate.from_messages(messages_input)
    GROQ_API_KEY = st.secrets.get("GROQ_API_KEY", os.environ.get("GROQ_API_KEY", ""))
    
    # نستخدم الموديل المستقر الذكي لتفادي مشاكل الحظر المؤقت والبطء
    llm = ChatGroq(temperature=0.2, groq_api_key=GROQ_API_KEY, model_name="llama-3.1-8b-instant")
    
    with chat_placeholder:
        with st.chat_message("assistant"):
            try:
                response_stream = llm.stream(prompt_template.format_messages())
                ai_response = st.write_stream(response_stream).strip()
            except Exception as e:
                ai_response = f"{T['error_server']}: {str(e)}"
                st.write(ai_response)
                
    save_user_message("ai", ai_response)
    st.session_state.chat_history.append({"role": "ai", "text": ai_response})
    st.rerun()
