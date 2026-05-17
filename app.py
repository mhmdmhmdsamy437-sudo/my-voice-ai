import os
import sqlite3
import uuid
import streamlit as st
import time
import io
import urllib.request
import urllib.parse
from bs4 import BeautifulSoup
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from groq import Groq 

# 1. تهيئة وإعداد واجهة المستخدم الذكية
st.set_page_config(page_title="صوتك | Sawtak AI", page_icon="🎙️", layout="wide")

if "user_id" not in st.session_state:
    st.session_state.user_id = str(uuid.uuid4())

if "audio_session_key" not in st.session_state:
    st.session_state.audio_session_key = str(uuid.uuid4())[:8]

USER_DIR = f"user_data/{st.session_state.user_id}"
USER_DOCS_DIR = os.path.join(USER_DIR, "temp_docs")
USER_DB_DIR = os.path.join(USER_DIR, "chroma_db")

for path in [USER_DOCS_DIR, USER_DB_DIR]:
    if not os.path.exists(path):
        os.makedirs(path)

# تنسيق واجهة العرض لمنع التداخل على الهواتف
st.markdown("""
    <style>
    .stApp { background-color: #111827 !important; color: #f3f4f6 !important; }
    .chat-container { display: flex; flex-direction: column; gap: 16px; padding: 5px; margin-bottom: 20px; }
    .chat-bubble-user {
        background: linear-gradient(135deg, #2563eb, #1d4ed8);
        color: #ffffff !important; padding: 12px 18px; border-radius: 16px 16px 4px 16px;
        align-self: flex-end; max-width: 85%; margin-left: auto; text-align: right;
    }
    .chat-bubble-ai {
        background-color: #1f2937; color: #f3f4f6 !important; padding: 14px 20px;
        border-radius: 16px 16px 16px 4px; align-self: flex-start; max-width: 85%;
        margin-right: auto; text-align: right; border: 1px solid #374151;
    }
    h1, h2, h3, p, span, label { color: #f3f4f6 !important; }
    </style>
""", unsafe_allow_html=True)

st.title("🎙️ صوتك | Sawtak AI")
st.caption("النسخة النهائية المستقرة: اتصال مباشر بالإنترنت + دعم كامل للهجات")

# دالة برمجية للبحث المباشر في الويب دون حظر لضمان جلب حقائق اليوم
def fetch_live_web_data(query):
    try:
        encoded_query = urllib.parse.quote(query)
        url = f"https://html.duckduckgo.com/html/?q={encoded_query}"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
        with urllib.request.urlopen(req, timeout=6) as response:
            soup = BeautifulSoup(response.read().decode('utf-8'), 'html.parser')
            snippets = [snippets.get_text() for snippets in soup.find_all('a', class_='result__snippet')[:3]]
            if snippets:
                return "\n".join(snippets)
    except Exception:
        pass
    return "لا توجد نتائج بحث مباشرة متوفرة."

# 2. لوحة التحكم
with st.expander("⚙️ لوحة التحكم وإدارة المستندات"):
    enable_tts = st.toggle("تفعيل الرد الصوتي التلقائي 🔊", value=True)
    st.markdown("---")
    uploaded_files = st.file_uploader("ارفع ملفات الـ PDF هنا:", type=["pdf"], accept_multiple_files=True)
    process_button = st.button("تحديث وفهرسة البيانات الذكية 🔄", use_container_width=True)
    
    if process_button and uploaded_files:
        with st.spinner("جاري قراءة وتأصيل البيانات..."):
            all_docs = []
            for uploaded_file in uploaded_files:
                file_path = os.path.join(USER_DOCS_DIR, uploaded_file.name)
                with open(file_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())
                loader = PyPDFLoader(file_path)
                all_docs.extend(loader.load())
                
            text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=80)
            final_chunks = text_splitter.split_documents(all_docs)
            Chroma.from_documents(documents=final_chunks, embedding=None, persist_directory=USER_DB_DIR)
            st.success("✅ تم حفظ وفهرسة مستنداتك بنجاح!")

st.markdown("---")

# 3. إدارة رسائل قاعدة البيانات المحلية
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

# 4. أدوات الإدخال المحمية ضد الكلمات العشوائية الفارغة
st.markdown("### 🎙️ أدوات الإدخال")
audio_file = st.audio_input("تحدث الآن بلهجتك الدارجة المعتادة:", key=f"audio_input_{st.session_state.audio_session_key}")
user_text_input = st.chat_input("أو اكتب سؤالك هنا يدوياً...")

final_query = ""

if user_text_input:
    final_query = user_text_input
elif audio_file:
    try:
        audio_bytes = audio_file.read()
        audio_size = len(audio_bytes)
        
        # تجاهل الصوت القصير جداً أو المتكرر لمنع أخطاء التخريف الإملائي
        if audio_size > 7000 and audio_size != st.session_state.last_processed_audio_size:
            st.session_state.last_processed_audio_size = audio_size
            with st.spinner("🎙️ جاري تصفية نبرة الصوت وتفسير اللهجة المحكية..."):
                GROQ_API_KEY = st.secrets.get("GROQ_API_KEY", os.environ.get("GROQ_API_KEY", ""))
                client = Groq(api_key=GROQ_API_KEY)
                
                audio_buffer = io.BytesIO(audio_bytes)
                audio_buffer.name = "input_audio.wav"
                
                transcription = client.audio.transcriptions.create(
                    file=audio_buffer,
                    model="whisper-large-v3",
                    language="ar",
                    prompt="مساء الخير، أين يلعب ميسي، كيف الحال، وش أخبارك، شو عامل. المتحدث ينطق بلهجة عربية عامية مفهومة.",
                    response_format="text"
                )
                captured_text = str(transcription).strip()
                # فلترة الكلمات الوهمية الناتجة عن الهواء أو التقطيع
                if len(captured_text) > 2 and "زار غير" not in captured_text and "نساء الخير" not in captured_text:
                    final_query = captured_text
                    
            st.session_state.audio_session_key = str(uuid.uuid4())[:8]
    except Exception:
        pass

# 5. معالجة وتوليد الرد بالاتصال الحقيقي المباشر بالإنترنت
if final_query != "":
    save_user_message("user", final_query)
    st.session_state.chat_history.append({"role": "user", "text": final_query})
    display_chat()
    
    # استدعاء دالة البحث الحي عبر الويب غصباً عن ذاكرة الموديل القديمة
    with st.spinner("🌐 جاري البحث في شبكة الإنترنت لجلب الحقائق الحالية..."):
        live_web_context = fetch_live_web_data(final_query)

    pdf_context = ""
    if os.path.exists(USER_DB_DIR) and len(os.listdir(USER_DB_DIR)) > 0:
        try:
            vector_store = Chroma(persist_directory=USER_DB_DIR, embedding_function=None)
            retrieved_docs = vector_store.similarity_search(final_query, k=2)
            if retrieved_docs:
                pdf_context = "\n".join([doc.page_content for doc in retrieved_docs])
        except Exception:
            pass

    history_context = ""
    for msg in st.session_state.chat_history[-2:-1]:
        history_context += f"{msg['role']}: {msg['text']}\n"

    # بناء ملقن نظام صارم يجبر الموديل على تجاهل معلوماته القديمة والاعتماد على بحث الويب
    prompt_template = ChatPromptTemplate.from_messages([
        ("system", (
            "أنت مساعد ذكي وموسوعي متصل مباشرة بالإنترنت.\n"
            "مهمتك القصوى هي الإجابة بدقة بالاعتماد الكامل على معلومات الويب الحية المرفقة لتحديث بياناتك وتصحيح أي معلومات قديمة فوراً (مثل الانتقالات الحالية للاعبين، الرؤساء الحاليين للبلدان، إلخ).\n\n"
            "معلومات الويب الحية المحدثة حالياً:\n{live_web_context}\n\n"
            "سياق المستندات المرفوعة:\n{pdf_context}"
        )),
        ("user", "الحوار السابق:\n{history}\n\nالسؤال المطلوب الإجابة عليه الآن بدقة: {query}")
    ])
    
    GROQ_API_KEY = st.secrets.get("GROQ_API_KEY", os.environ.get("GROQ_API_KEY", ""))
    llm = ChatGroq(temperature=0.2, groq_api_key=GROQ_API_KEY, model_name="llama-3.3-70b-versatile")
    
    formatted_prompt = prompt_template.format_messages(
        live_web_context=live_web_context,
        pdf_context=pdf_context if pdf_context else "لا توجد ملفات مستندات.",
        history=history_context,
        query=final_query
    )
    
    with chat_placeholder.container():
        display_chat()
        with st.chat_message("assistant"):
            try:
                response_stream = llm.stream(formatted_prompt)
                ai_response = st.write_stream(response_stream)
                ai_response = ai_response.strip()
            except Exception:
                ai_response = "حصل خطأ في معالجة الطلب، يرجى إعادة المحاولة."
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

