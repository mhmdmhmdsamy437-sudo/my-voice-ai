import os
import sqlite3
import streamlit as st
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate

# 1. الإعدادات الأساسية للواجهة
st.set_page_config(page_title="OmniSearch Voice AI", page_icon="🎙️", layout="wide")

# تنسيق واجهة المستخدم وتأمين اتجاه النصوص (RTL)
st.markdown("""
    <style>
    .main { background-color: #ffffff; }
    .chat-container { display: flex; flex-direction: column; gap: 10px; margin-bottom: 40px; }
    .chat-bubble-user {
        background-color: #f0f2f6; color: #1d1d1d; padding: 12px 16px; 
        border-radius: 15px; align-self: flex-end; max-width: 75%;
        font-family: Arial, sans-serif; text-align: right; direction: rtl;
    }
    .chat-bubble-ai {
        background-color: #e8f0fe; color: #0d0d0d; padding: 12px 16px; 
        border-radius: 15px; align-self: flex-start; max-width: 75%;
        font-family: Arial, sans-serif; text-align: right; direction: rtl;
    }
    </style>
""", unsafe_allow_html=True)

st.title("🎙️ OmniSearch Voice AI")
st.caption("المساعد الذكي المتكامل للمحادثات وقراءة ملفات الـ PDF")
st.markdown("---")

if not os.path.exists("temp_docs"):
    os.makedirs("temp_docs")

# 2. إدارة قاعدة البيانات المحلية لجلسة المحادثة
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

# 3. تهيئة موديل Groq الاصطناعي
@st.cache_resource
def init_models():
    GROQ_API_KEY = st.secrets.get("GROQ_API_KEY", os.environ.get("GROQ_API_KEY", ""))
    llm = ChatGroq(
        temperature=0.3,
        groq_api_key=GROQ_API_KEY,
        model_name="llama-3.3-70b-versatile"
    )
    return llm

llm = init_models()

# 4. القائمة الجانبية لإدارة المستندات
with st.sidebar:
    st.markdown("### 📁 ملفات ومستندات الـ PDF")
    uploaded_files = st.file_uploader("ارفع ملفات الـ PDF الخاصة بك:", type=["pdf"], accept_multiple_files=True)
    process_button = st.button("تحديث وقراءة الذاكرة 🔄", use_container_width=True)
    
    st.markdown("---")
    if st.button("مسح سجل الذاكرة 🗑️", use_container_width=True):
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
            
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=80)
        final_chunks = text_splitter.split_documents(all_docs)
        Chroma.from_documents(documents=final_chunks, embedding=None, persist_directory="chroma_db")
        st.sidebar.success("✅ تم تحديث الذاكرة بنجاح!")

# 5. عرض صندوق الشات والمحادثات السابقة
st.markdown("<div class='chat-container'>", unsafe_allow_html=True)
for message in st.session_state.chat_history:
    if message["role"] == "user":
        st.markdown(f"<div class='chat-bubble-user'>{message['text']}</div>", unsafe_allow_html=True)
    else:
        st.markdown(f"<div class='chat-bubble-ai'>🤖 {message['text']}</div>", unsafe_allow_html=True)
st.markdown("</div>", unsafe_allow_html=True)

# 6. صندوق الإدخال الرئيسي والمستقر (مربع الشات الرسمي)
final_input = st.chat_input("اكتب رسالتك أو استفسارك هنا واضغط Enter...")

# 7. معالجة وتوليد الإجابات الفورية فور الإرسال
if final_input:
    # حفظ رسالة المستخدم وعرضها فوراً
    save_message("user", final_input)
    st.session_state.chat_history.append({"role": "user", "text": final_input})
    
    # جلب السياق من قاعدة بيانات المستندات
    pdf_context = "لا توجد ملفات مرفوعة حالياً. أجب مباشرة من معلوماتك العامة."
    if os.path.exists("chroma_db") and len(os.listdir("chroma_db")) > 0:
        try:
            vector_store = Chroma(persist_directory="chroma_db", embedding_function=None)
            retrieved_docs = vector_store.similarity_search(final_input, k=2)
            if retrieved_docs:
                pdf_context = "\n\n".join([doc.page_content for doc in retrieved_docs])
        except Exception:
            pass

    # تجهيز سياق الذاكرة لآخر رسائل
    history_context = ""
    for msg in st.session_state.chat_history[-4:-1]:
        history_context += f"{msg['role']}: {msg['text']}\n"

    prompt_template = ChatPromptTemplate.from_messages([
        ("system", (
            "أنت OmniSearch AI، مساعد ذكي وموجز.\n"
            "أجب دائماً باللغة العربية الفصحى وبشكل مختصر جداً (سطر أو سطرين فقط).\n\n"
            "سياق ملفات الـ PDF:\n{pdf_context}"
        )),
        ("user", "سجل الجلسة:\n{history}\n\nالسؤال: {query}")
    ])
    
    formatted_prompt = prompt_template.format_messages(pdf_context=pdf_context, history=history_context, query=final_input)
    
    # استدعاء الموديل وتوليد الرد
    with st.spinner("🤖 جاري صياغة الرد..."):
        response_object = llm.invoke(formatted_prompt)
        ai_response = response_object.content
    
    # حفظ رد الموديل في قاعدة البيانات والـ Session
    save_message("ai", ai_response)
    st.session_state.chat_history.append({"role": "ai", "text": ai_response})
    
    # نطق الرد برمجياً بمجرد ظهوره للمستخدم
    clean_text = ai_response.replace("'", "\\'").replace("\n", " ")
    js_tts = f"""
    <script>
    window.speechSynthesis.cancel();
    var msg = new SpeechSynthesisUtterance('{clean_text}');
    msg.lang = 'ar-SA';
    window.speechSynthesis.speak(msg);
    </script>
    """
    st.components.v1.html(js_tts, height=0)
    
    # إعادة تحميل الصفحة لعرض النتائج الجديدة بالكامل
    st.rerun()

