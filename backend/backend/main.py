import os
import base64
import json
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from groq import Groq
from supabase import create_client, Client

app = FastAPI(title="Sawtak AI Pro Backend")

# السماح بجميع الاتصالات (CORS) لتجنب الحظر
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

SUPABASE_URL = "https://uciymzougmatinbqxdpq.supabase.co"
SUPABASE_KEY = os.environ.get("SUPABASE_SECRET_KEY", "")

if SUPABASE_KEY:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
else:
    supabase = None

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
client = Groq(api_key=GROQ_API_KEY)

def check_pro_badge(user_id: str):
    if not supabase:
        return True
    if not user_id or user_id in ["null", "undefined", "guest"]:
         return False
    try:
        response = supabase.table("profiles").select("*").eq("id", user_id).single().execute()
        if response.data:
            tier = response.data.get("subscription_tier") or response.data.get("subscription")
            if tier == "pro":
                return True
        return False
    except Exception:
        return False

def get_strict_system_prompt(dialect: str) -> str:
    return f"""
    You are 'Sawtak AI' (صوتك), a premium conversational assistant optimized ONLY for 3 languages: Arabic, English, and French.
    CRITICAL INSTRUCTIONS:
    1. STRICT LANGUAGE RESTRICTION: Respond ONLY in Arabic (العربية), English, or French (Français). NEVER use any other language.
    2. MATCH USER LANGUAGE: Answer 100% in the exact language the user used in the immediate last message. Do not mix languages.
    3. DIALECT ADAPTATION: If the user communicates in Arabic, adapt your tone naturally to match their preferred style/dialect: ({dialect}). Understand local phrasing and slang perfectly.
    4. Provide focused, clear, and interactive answers. Never reply to multiple historical questions if they are bundled incorrectly.
    """

# نموذج استقبال الشات النصي العادي المحدث لدعم الذاكرة المستمرة
class TextChatRequest(BaseModel):
    text: str
    dialect: str = "الفصحى"
    user_id: str = "guest"
    history: list = []  # مصفوفة الذاكرة المضافة لاستقبال تاريخ المحادثة

@app.post("/api/chat/text")
async def chat_text_endpoint(request: TextChatRequest):
    try:
        clean_message = request.text.strip()
        if not clean_message:
            return {"status": "success", "response": "لم أستلم أي نص واضح."}

        # بناء حزمة الرسائل وتغذيتها بالـ System Prompt
        api_messages = [{"role": "system", "content": get_strict_system_prompt(request.dialect)}]
        
        # دمج الذاكرة القديمة القادمة من الفرونتيند
        for msg in request.history:
            api_messages.append({"role": msg.get("role", "user"), "content": msg.get("content", "")})
            
        # إضافة الرسالة الحالية الجديدة في نهاية المصفوفة
        api_messages.append({"role": "user", "content": clean_message})
        
        completion = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=api_messages,
            temperature=0.4
        )
        return {"status": "success", "response": completion.choices[0].message.content.strip()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# رابط معالجة وتحليل الصور (Vision) المحدث بالذاكرة المستمرة
@app.post("/api/chat/vision")
async def chat_vision_endpoint(
    text: str = Form(""),
    dialect: str = Form("الفصحى"),
    user_id: str = Form("guest"),
    history: str = Form("[]"),  # استقبال الذاكرة كـ نص هنا ليناسب صيغة الـ Form Data
    file: UploadFile = File(...)
):
    try:
        if not check_pro_badge(user_id):
            return {"status": "upgrade_required", "response": "⚠️ ميزة تحليل الصور مخصصة وحصرية لباقة Pro الفاخرة."}
        
        image_bytes = await file.read()
        base64_image = base64.b64encode(image_bytes).decode("utf-8")
        
        # بناء الرسائل وتغذيتها بالذاكرة المستمرة
        api_messages = [{"role": "system", "content": get_strict_system_prompt(dialect)}]
        
        try:
            parsed_history = json.loads(history)
            for msg in parsed_history:
                api_messages.append({"role": msg.get("role", "user"), "content": msg.get("content", "")})
        except Exception:
            pass

        user_prompt = text.strip() if text.strip() else "Analyze this image."
        
        # إضافة رسالة الصورة الحالية مع النص المرفق بها
        api_messages.append({
            "role": "user",
            "content": [
                {"type": "text", "text": user_prompt},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
            ]
        })

        completion = client.chat.completions.create(
            model="llama-3.2-11b-vision-instant",
            messages=api_messages,
            temperature=0.3
        )
        return {"status": "success", "response": completion.choices[0].message.content.strip()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# رابط الشات الصوتي (Audio) المحدث بالذاكرة المستمرة
@app.post("/api/chat/audio")
async def chat_audio_endpoint(
    dialect: str = Form("الفصحى"),
    user_id: str = Form("guest"),
    history: str = Form("[]"),  # استقبال الذاكرة كـ نص هنا أيضاً
    file: UploadFile = File(...)
):
    temp_filename = "temp_voice_input.wav"
    try:
        # حفظ الملف الصوتي المرسل مؤقتاً لتقديمه للـ Whisper API
        audio_content = await file.read()
        with open(temp_filename, "wb") as f:
            f.write(audio_content)
        
        # تحويل الصوت إلى نص (Transcription)
        with open(temp_filename, "rb") as audio_file:
            transcription = client.audio.transcriptions.create(
                file=audio_file,
                model="whisper-large-v3",
                response_format="text",
                language="ar"
            )
        
        captured_text = str(transcription).strip()
        os.remove(temp_filename)

        if not captured_text:
            return {"status": "success", "user_speech": "", "response": "عذراً، لم أتمكن من سماع صوتك بشكل واضح."}

        # بناء الرسائل وتضمين التاريخ المستمر لتذكر سياق الكلام السابق
        api_messages = [{"role": "system", "content": get_strict_system_prompt(dialect)}]
        
        try:
            parsed_history = json.loads(history)
            for msg in parsed_history:
                api_messages.append({"role": msg.get("role", "user"), "content": msg.get("content", "")})
        except Exception:
            pass

        # إضافة النص الصوتي الجديد المستخرج من الفويس الحالي
        api_messages.append({"role": "user", "content": captured_text})

        completion = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=api_messages,
            temperature=0.4
        )
        
        return {
            "status": "success",
            "user_speech": captured_text,
            "response": completion.choices[0].message.content.strip()
        }
    except Exception as e:
        if os.path.exists(temp_filename):
            os.remove(temp_filename)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
def read_root():
    return {"status": "Live", "message": "Sawtak AI Pro Backend is Fully Synchronized."}
