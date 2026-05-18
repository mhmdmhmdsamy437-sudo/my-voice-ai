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

# --- 1. إعداد الصفحة والواجهة الصوتية المستوحاة من التطبيقات العالمية ---
st.set_page_config(page_title="صوتك | Sawtak Live AI", page_icon="🎙️", layout="centered")

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

# تصميم واجهة صوتية سينمائية ونظيفة جداً (تخفي صندوق الشات التقليدي وتظهر التموجات)
st.markdown("""
    <style>
    .stApp { background-color: #0b0f17 !important; color: #f3f4f6 !important; }
    
    /* حاوية الأوضاع الصوتية المركزية */
    .voice-status-container {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        text-align: center;
        padding: 40px 20px;
        margin-top: 20px;
    }
    
    /* النبضات الدائرية المتفاعلة أثناء الرد والتفكير */
    .listening-pulse {
        width: 110px;
        height: 110px;
        background: linear-gradient(135deg, #00f2fe, #4facfe);
        border-radius: 50%;
        box-shadow: 0 0 0 0 rgba(79, 172, 254, 0.7);
        animation: pulse-glow 1.6s infinite cubic-bezier(0.66, 0, 0, 1);
        display: flex;
        align-items: center;
        justify-content: center;
        margin-bottom: 25px;
    }
    
    .speaking-pulse {
        width: 110px;
        height: 110px;
        background: linear-gradient(135deg, #ea580c, #f97316);
        border-radius: 50%;
        box-shadow: 0 0 0 0 rgba(249, 115, 22, 0.7);
        animation: pulse-glow 1.2s infinite cubic-bezier(0.66, 0, 0, 1);
        display: flex;
        align-items: center;
        justify-content: center;
        margin-bottom: 25px;
    }

    @keyframes pulse-glow {
        to { box-shadow: 0 0 0 40px rgba(79, 172, 254, 0); }
    }
    
    /* ويدجيت كتابة النص السفلي المودرن */
    .modern-caption {
        font-size: 1.15rem !important;
        font-weight: 500;
        color: #9ca3af !important;
        margin-top: 10px;
        line-height: 1.6;
    }
    
    .user-transcript-box {
        background-color: #161b22;
        border: 1px solid #30363d;
        border-radius: 12px;
        padding: 15px;
        width: 100%;
        text-align: center;
        margin-top: 15px;
        color: #e5e7eb;
    }
    
    /* إخفاء القوائم غير الضرورية لتركيز عين المستخدم على التجربة الصوتية */
    h1, h2, h3, p, span, label { color: #f3f4f6 !important; text-align: center; }
    </style>
""", unsafe_allow_html=True)

# دالة الويب الحية الذكية لتغذية الإجابات بالمعلومات الفورية
def fetch_live_web_data(query):
    try:
        clean_query = re.sub(r'^(لا قصدي عن|لا قصدي|قصدي عن|قصدي|اسمع|اسمعني|تعديل|لا لا)\s*', '', query, flags=re.IGNORECASE).strip()
        clean_query = clean_query.replace("البوربون", "").replace("بوربون", "").strip()
        if not clean_query: clean_query = query
        encoded_query = urllib.parse.quote(clean_query)
        url = f"https://html.duckduckgo.com/html/?q={encoded_query}"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
        with urllib.request.urlopen(req, timeout=5) as response:
            html_content = response.read().decode('utf-8')
            snippets = re.findall(r'class="result__snippet"[^>]*>(.*?)<\/a>', html_content, re.DOTALL)
            if snippets: return "\n".join([re.sub(r'<[^>]+>', '', s).strip() for s in snippets[:3]])
    except Exception: pass
    return "لا توجد نتائج بحث مباشرة متوفرة حالياً."

# --- 2. التحكم والإعدادات الجانبية ---
with st.sidebar:
    st.title("🎙️ تخصيص Sawtak Live")
    dialect = st.selectbox(
        "لهجة استجابة الروبوت الصوتية:",
        ["العربية الفصحى بمصطلحات مبسطة", "اللهجة السودانية الدارجة", "اللهجة الخليجية", "اللهجة المصرية", "اللهجة الشامية"]
    )
    st.markdown("---")
    uploaded_files = st.file_uploader("تغذية الذاكرة بملفات PDF:", type=["pdf"], accept_multiple_files=True)
    if st.button("تحديث المستندات 🔄", use_container_width=True) and uploaded_files:
        with st.spinner("جاري قراءة البيانات..."):
            texts = []
            for f in uploaded_files:
                f_path = os.path.join(USER_DOCS_DIR, f.name)
                with open(f_path, "wb") as file: file.write(f.getbuffer())
                for page in PyPDFLoader(f_path).load(): texts.append(page.page_content)
            st.session_state.pdf_context_memory = "\n".join(texts)[:3500]
            st.success("✅ تذكرت مستنداتك بنجاح!")

# --- 3. إدارة الجلسة وقاعدة البيانات المحلية ---
def init_user_db():
    conn = sqlite3.connect(os.path.join(USER_DIR, "personal_chat.db"), check_same_thread=False)
    conn.cursor().execute("CREATE TABLE IF NOT EXISTS messages (id INTEGER PRIMARY KEY AUTOINCREMENT, role TEXT, text TEXT)")
    conn.commit()
    conn.close()

def load_user_chat():
    conn = sqlite3.connect(os.path.join(USER_DIR, "personal_chat.db"), check_same_thread=False)
    rows = conn.cursor().execute("SELECT role, text FROM messages ORDER BY id ASC").fetchall()
    conn.close()
    return [{"role": r[0], "text": r[1]} for r in rows]

def save_user_message(role, text):
    try:
        conn = sqlite3.connect(os.path.join(USER_DIR, "personal_chat.db"), check_same_thread=False)
        conn.cursor().execute("INSERT INTO messages (role, text) VALUES (?, ?)", (role, text))
        conn.commit()
        conn.close()
    except Exception: pass

init_user_db()
if "chat_history" not in st.session_state: st.session_state.chat_history = load_user_chat()
if "last_processed_audio_size" not in st.session_state: st.session_state.last_processed_audio_size = 0
if "current_ai_voice_response" not in st.session_state: st.session_state.current_ai_voice_response = ""

# عنوان التطبيق النظيف العلوي
st.markdown("<h2 style='text-align: center; font-weight: 700; margin-bottom: 5px;'>🎙️ صوتك | Sawtak Live</h2>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #6b7280; margin-bottom: 25px;'>الجيل الجديد للمحادثات الصوتية الفورية</p>", unsafe_allow_html=True)

# الـ Placeholder المركزي للأنيميشن والنبضات الصوتية المباشرة
status_placeholder = st.empty()

# الوضع الافتراضي: بانتظار استماع صوت المستخدم
with status_placeholder.container():
    st.markdown("""
        <div class='voice-status-container'>
            <div class='listening-pulse'><span style='font-size: 2.2rem;'>🎙️</span></div>
            <div class='modern-caption'>اضغط على زر التسجيل وتحدث فوراً، أنا أسمعك بذكاء...</div>
        </div>
    """, unsafe_allow_html=True)

# أدوات الإدخال المودرن المتمثلة في زر تسجيل ضخم أسفل الشاشة
audio_file = st.audio_input("", key=f"audio_live_input_{st.session_state.audio_session_key}")

final_query = ""

if audio_file:
    try:
        audio_bytes = audio_file.read()
        audio_size = len(audio_bytes)
        
        if audio_size > 7000 and audio_size != st.session_state.last_processed_audio_size:
            st.session_state.last_processed_audio_size = audio_size
            
            # تغيير الأنيميشن فوراً إلى "جاري المعالجة والتفكير"
            with status_placeholder.container():
                st.markdown("""
                    <div class='voice-status-container'>
                        <div class='listening-pulse' style='background: linear-gradient(135deg, #a855f7, #6366f1);'><span style='font-size: 2.2rem;'>🧠</span></div>
                        <div class='modern-caption'>جاري تفسير كلامك الدارج واستدعاء المعلومات الحية...</div>
                    </div>
                """, unsafe_allow_html=True)
            
            GROQ_API_KEY = st.secrets.get("GROQ_API_KEY", os.environ.get("GROQ_API_KEY", ""))
            client = Groq(api_key=GROQ_API_KEY)
            
            audio_buffer = io.BytesIO(audio_bytes)
            audio_buffer.name = "input_audio.wav"
            
            # معالجة نبرة الصوت وتحويلها بدقة لـ سياق مقروء
            transcription = client.audio.transcriptions.create(
                file=audio_buffer,
                model="whisper-large-v3",
                language="ar",
                prompt="لا قصدي، الدوري الفرنسي، الهدافين، التواريخ. المتحدث يتحدث بلهجته المحلية الطبيعية العفوية.",
                response_format="text"
            )
            captured_text = str(transcription).strip()
            if len(captured_text) > 2:
                final_query = captured_text
                st.session_state.audio_session_key = str(uuid.uuid4())[:8]
    except Exception: pass

# --- 4. توليد الرد الذكي المفتوح وتفعيل نمط النطق الحي (Live Response) ---
if final_query != "":
    save_user_message("user", final_query)
    st.session_state.chat_history.append({"role": "user", "text": final_query})
    
    # جلب السياق اللحظي من الإنترنت ومن الـ PDF
    live_web_context = fetch_live_web_data(final_query)
    pdf_context = st.session_state.pdf_context_memory if st.session_state.pdf_context_memory else "لا توجد مستندات."

    # صياغة الموجه الذكي بلغة حية مباشرة تخاطب الأذن لا العين
    system_instruction = (
        "أنت مساعد صوتي ذكي تفاعلي فوري لعام 2026.\n"
        "أجب على المستخدم بدقة بالاعتماد على سياق الويب المرفق.\n"
        f"يجب أن تتحدث بالكامل وبشكل مطلق مستخدماً: ({dialect}).\n"
        "قواعد الأداء الصوتي:\n"
        "1. لا تذكر مقدمات ترحيبية أو ديباجات، ادخل في صلب المعلومة فوراً بأسلوب مبسط وشيق مخصص للاستماع الفوري.\n"
        "2. إذا عدل المستخدم كلامه أو قال 'لا قصدي'، ركز على تصحيحه الأخير وتجاهل العبارات القديمة تماماً.\n\n"
        f"بيانات الويب المحدثة:\n{live_web_context}\n\n"
        f"بيانات الـ PDF:\n{pdf_context}"
    )

    messages_input = [("system", system_instruction)]
    for msg in st.session_state.chat_history[-4:-1]:
        messages_input.append((msg["role"], msg["text"]))
    messages_input.append(("user", final_query))

    prompt_template = ChatPromptTemplate.from_messages(messages_input)
    
    GROQ_API_KEY = st.secrets.get("GROQ_API_KEY", os.environ.get("GROQ_API_KEY", ""))
    # نستخدم الموديل السريع الفوري الخفيف 8B لضمان استجابة لحظية تحاكي التطبيقات العالمية وبدون سقف قيود
    llm = ChatGroq(temperature=0.2, groq_api_key=GROQ_API_KEY, model_name="llama-3.1-8b-instant")
    
    # تغيير حالة الواجهة إلى "الروبوت يتحدث الآن"
    with status_placeholder.container():
        st.markdown(f"""
            <div class='voice-status-container'>
                <div class='speaking-pulse'><span style='font-size: 2.2rem;'>🔊</span></div>
                <div class='user-transcript-box'>💬 <b>أنت قلت:</b> "{final_query}"</div>
                <div class='modern-caption' style='color:#f97316 !important; margin-top:15px;'>جاري التحدث والرد بلهجتك الطبيعية...</div>
            </div>
        """, unsafe_allow_html=True)
    
    try:
        # توليد النص كاملاً لدفعه مباشرة لمحرك الصوت السريع لمنع تقطيع الصوت
        response_data = llm.invoke(prompt_template.format_messages())
        ai_response = response_data.content.strip()
    except Exception as e:
        ai_response = "معذرةً، واجهت مشكلة اتصال سريعة بالسيرفر، يرجى التحدث مرة أخرى."
        
    save_user_message("ai", ai_response)
    st.session_state.chat_history.append({"role": "ai", "text": ai_response})
    st.session_state.current_ai_voice_response = ai_response
    
    # إطلاق الصوت فوراً باستخدام جافا سكريبت المتوافقة مع جميع المتصفحات والهواتف
    clean_text = ai_response.replace("'", "\\'").replace("\n", " ")
    js_universal_tts = f"""
    <script>
    window.speechSynthesis.cancel();
    var msg = new SpeechSynthesisUtterance('{clean_text}');
    msg.lang = 'ar-SA';
    msg.rate = 1.05; 
    window.speechSynthesis.speak(msg);
    </script>
    """
    st.components.v1.html(js_universal_tts, height=0)
    
    # إظهار النص المستجاب أسفل التموجات لزيادة الفائدة البصرية
    with status_placeholder.container():
        st.markdown(f"""
            <div class='voice-status-container'>
                <div class='speaking-pulse'><span style='font-size: 2.2rem;'>🔊</span></div>
                <div class='user-transcript-box' style='border-color: #f97316;'>🤖 <b>الرد الحالي:</b> {ai_response}</div>
                <div class='modern-caption' style='margin-top:10px;'>اضغط على الزر بالأسفل لتسجيل سؤال جديد في أي وقت...</div>
            </div>
        """, unsafe_allow_html=True)
    
    final_query = ""
    st.rerun()
