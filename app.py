import os
import sqlite3
import uuid
import streamlit as st
import time
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from groq import Groq 

# 1. إعدادات الواجهة الفخمة والتهيئة الآمنة (Sawtak AI)
st.set_page_config(page_title="صوتك | Sawtak AI", page_icon="🎙️", layout="wide")

if "user_id" not in st.session_state:
    st.session_state.user_id = str(uuid.uuid4())

USER_DIR = f"user_data/{st.session_state.user_id}"
USER_DOCS_DIR = os.path.join(USER_DIR, "temp_docs")
USER_DB_DIR = os.path.join(USER_DIR, "chroma_db")

for path in [USER_DOCS_DIR, USER_DB_DIR]:
    if not os.path.exists(path):
        os.makedirs(path)

# تنسيق واجهة مستخدم (UI/UX) سينمائي فاخر يشبه ChatGPT تماماً
st.markdown("""
    <style>
    .main { background-color: #0b0f19; color: #ffffff; }
    .stApp { background-color: #0b0f19; }
    .chat-container { display: flex; flex-direction: column; gap: 16px; margin-bottom: 30px; }
    .chat-bubble-user {
        background: linear-gradient(135deg, #007bff, #0056b3); color: white; padding: 14px 20px; 
        border-radius: 20px 20px 4px 20px; align-self: flex-end; max-width: 75%;
        font-family: system-ui, -apple-system, sans-serif; text-align: right;
        box-shadow: 0 4px 15px rgba(0,123,255,0.2);
    }
    .chat-bubble-ai {
        background-color: #1e293b; color: #f8fafc; padding: 14px 20px; 
        border-radius: 20px 20px 20px 4px; align-self: flex-start; max-width: 75%;
        font-family: system-ui, -apple-system, sans-serif; 
        box-shadow: 0 4px 15px rgba(0,0,0,0.3); border: 1px solid #334155;
    }
    .stTextInput input { background-color: #1e293b !important; color: white !important; border: 1px solid #475569 !important; }
    h1, p, span, label { color: white !important; }
    </style>
""", unsafe_allow_html=True)

st.title("🎙️ صوتك | Sawtak AI")
st.caption("الجيل القادم من المساعدات الذكية الفورية - مدعوم بمصحح السياق العبقري")
st.markdown("---")

# 2. إدارة قاعدة البيانات المحفوظة للمستخدم
def init_user_db():
    db_path = os.path.join(USER_DIR, "personal_chat.db")
    conn = sqlite3.connect(db_path, check_same_thread=False)
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
        cursor = conn.cursor()
        cursor.execute("INSERT INTO messages (role, text) VALUES (?, ?)", (role, text))
        conn.commit()
        conn.close()
    except Exception:
        pass

def clear_user_data():
    db_path = os.path.join(USER_DIR, "personal_chat.db")
    if os.path.exists(db_path):
        conn = sqlite3.connect(db_path, check_same_thread=False)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM messages")
        conn.commit()
        conn.close()
    if os.path.exists(USER_DB_DIR):
        import shutil
        shutil.rmtree(USER_DB_DIR)
        os.makedirs(USER_DB_DIR)

init_user_db()

if "chat_history" not in st.session_state:
    st.session_state.chat_history = load_user_chat()

if "last_processed_audio_size" not in st.session_state:
    st.session_state.last_processed_audio_size = 0

# 3. تهيئة مفتاح ونموذج الذكاء الاصطناعي الرئيسي ومصحح النصوص
GROQ_API_KEY = st.secrets.get("GROQ_API_KEY", os.environ.get("GROQ_API_KEY", ""))

@st.cache_resource
def init_groq_llm():
    return ChatGroq(
        temperature=0.1,  # جعل الموديل حاسماً ودقيقاً جداً لتجنب التخريف
        groq_api_key=GROQ_API_KEY,
        model_name="llama-3.1-8b-instant"
    )

llm = init_groq_llm()

# 4. لوحة التحكم الجانبية لإدارة المستندات
with st.sidebar:
    st.markdown("### 📁 المستندات والملفات الذكية")
    st.info(f"المستخدم النشط: `Sawtak-{st.session_state.user_id[:6].upper()}`")
    
    uploaded_files = st.file_uploader("قم بسحب وإفلات ملفات الـ PDF هنا:", type=["pdf"], accept_multiple_files=True)
    process_button = st.button("تحديث قاعدة البيانات السحابية 🔄", use_container_width=True)
    
    st.markdown("---")
    if st.button("🗑️ تصفير المحادثة وحذف المستندات", use_container_width=True):
        clear_user_data()
        st.session_state.chat_history = []
        st.session_state.last_processed_audio_size = 0
        st.success("تم تنظيف البيئة تماماً!")
        time.sleep(1)
        st.rerun()

if process_button and uploaded_files:
    with st.spinner("جاري قراءة الملفات وبناء الفهرس الذكي..."):
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
        st.sidebar.success("✅ تم تحديث المستندات بنجاح!")

# 5. عرض ساحة الشات بتصميم راقي جداً
st.markdown("<div class='chat-container'>", unsafe_allow_html=True)
for message in st.session_state.chat_history:
    if message["role"] == "user":
        st.markdown(f"<div class='chat-bubble-user'>{message['text']}</div>", unsafe_allow_html=True)
    else:
        st.markdown(f"<div class='chat-bubble-ai'>🤖 {message['text']}</div>", unsafe_allow_html=True)
st.markdown("</div>", unsafe_allow_html=True)

# 6. قسم أدوات الإدخال فائقة الحساسية والذكاء
st.markdown("### 🎙️ تحدث أو اكتب سؤالك")
col_audio, col_space = st.columns([1, 2])

raw_query = ""

with col_audio:
    audio_file = st.audio_input("اضغط على المايك للتحدث")

user_text_input = st.chat_input("اكتب سؤالك هنا يدوياً إذا كنت تفضل ذلك...")

# التقاط الصوت وتحويله بدقة بالغة
if user_text_input:
    raw_query = user_text_input
elif audio_file:
    if audio_file.size > 1000 and audio_file.size != st.session_state.last_processed_audio_size:
        st.session_state.last_processed_audio_size = audio_file.size
        with st.spinner("🎙️ جاري الاستماع وتصحيح الكلمات إملائياً..."):
            try:
                client = Groq(api_key=GROQ_API_KEY)
                temp_audio_path = os.path.join(USER_DIR, "temp_voice.wav")
                with open(temp_audio_path, "wb") as f:
                    f.write(audio_file.getbuffer())
                
                with open(temp_audio_path, "rb") as file:
                    transcription = client.audio.transcriptions.create(
                        file=(temp_audio_path, file.read()),
                        model="whisper-large-v3",
                        language="ar",
                        prompt="المتحدث يتحدث بلهجة عربية عامية ممزوجة، يرجى كتابة الكلمات بشكل صحيح وتجنب الأخطاء الإملائية.",
                        response_format="text"
                    )
                captured_text = str(transcription).strip()
                if len(captured_text) > 1:
                    raw_query = captured_text
                
                if os.path.exists(temp_audio_path):
                    os.remove(temp_audio_path)
            except Exception:
                st.error("تنبيه: عذراً، المايك لم يلتقط الصوت بوضوح كامل، أعد المحاولة ثانية.")

# 🧠 الفلتر الخفي والمصحح الذكي لضمان فهم السؤال بنسبة 100% مثل شات جي بي تي
final_query = ""
if raw_query != "":
    with st.spinner("🧠 جاري تحليل سياق وفهم السؤال بشكل احترافي..."):
        try:
            correction_prompt = f"""
            أنت خبير لغوي ومحلل سياق ذكي جداً لمدخلات المستخدمين الصوتية.
            أمامك نص تم تحويله من تسجيل صوتی، قد يحتوي على أخطاء إملائية، نقص في الكلمات، أو صياغة عامية ركيكة.
            مهمتك الوحيدة: فهم "نية المستخدم الحقيقية" وإعادة صياغة النص إلى سؤال واضح، صحيح إملائياً وبليغ باللغة العربية دون تعديل في جوهر المعنى.
            
            النص الخام المراد تصحيحه وفهمه: "{raw_query}"
            
            أخرج فقط السؤال المصحح النهائي مباشرة بدون أي مقدمات أو تحيات أو شرح.
            """
            correction_res = llm.invoke(correction_prompt)
            final_query = correction_res.content.strip()
        except Exception:
            final_query = raw_query  # في حال حدوث أي خطأ نعتمد النص الأصلي كحماية

# 7. إرسال الطلب النهائي المصحح وتوليد الإجابة السينمائية
if final_query != "":
    save_user_message("user", final_query)
    st.session_state.chat_history.append({"role": "user", "text": final_query})
    
    # البحث بذكاء في الـ PDF
    pdf_context = "لا توجد مستندات مرفوعة حالياً في مساحة المستخدم الشخصية. أجب بناءً على معلوماتك العامة القوية بدقة واحترافية وبشكل مفصل ومقنع."
    if os.path.exists(USER_DB_DIR) and len(os.listdir(USER_DB_DIR)) > 0:
        try:
            vector_store = Chroma(persist_directory=USER_DB_DIR, embedding_function=None)
            retrieved_docs = vector_store.similarity_search(final_query, k=3)
            if retrieved_docs:
                pdf_context = "\n\n".join([doc.page_content for doc in retrieved_docs])
        except Exception:
            pass

    history_context = ""
    for msg in st.session_state.chat_history[-3:-1]:
        history_context += f"{msg['role']}: {msg['text']}\n"

    prompt_template = ChatPromptTemplate.from_messages([
        ("system", (
            "You are Sawtak AI, an elite and highly professional artificial intelligence assistant, built to match ChatGPT's standard.\n"
            "Respond to the user in fluent, eloquent, and flawless Arabic.\n"
            "Be highly informative, professional, and helpful. Maintain a polite and structured response layout.\n"
            "If context from uploaded PDFs is relevant, prioritize it carefully:\n{pdf_context}"
        )),
        ("user", "Conversation History:\n{history}\n\nUser Question: {query}")
    ])
    
    formatted_prompt = prompt_template.format_messages(pdf_context=pdf_context, history=history_context, query=final_query)
    
    with st.spinner("🤖 صوتك يفكر في الإجابة الأكثر احترافية..."):
        try:
            response_object = llm.invoke(formatted_prompt)
            ai_response = response_object.content
        except Exception:
            ai_response = "عذراً يا فندم، واجه الخادم طلباً مكثفاً للغاية الآن، يرجى إعادة المحاولة بعد ثانية واحدة."
    
    save_user_message("ai", ai_response)
    st.session_state.chat_history.append({"role": "ai", "text": ai_response})
    
    # 🔊 توليد النطق التلقائي فائق الجودة والنقاء بلغة الضاد
    clean_text = ai_response.replace("'", "\\'").replace("\n", " ")
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
    
    st.rerun()

