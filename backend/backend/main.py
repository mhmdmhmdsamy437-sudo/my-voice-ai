import os
import base64
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from groq import Groq
from supabase import create_client, Client

app = FastAPI(title="Sawtak AI Pro Backend")

# تفعيل الـ CORS لتوصيل الفرونتيند بالباكيند
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# إعدادات روابط ومفاتيح Supabase الخاصة بمشروعك بشكل آمن
SUPABASE_URL = "https://uciymzougmatinbqxdpq.supabase.co"
# قراءة المفتاح من البيئة لحمايته من الحظر
SUPABASE_KEY = os.environ.get("SUPABASE_SECRET_KEY", "") 

# التحقق من وجود المفتاح السري لتجنب توقف السيرفر عند التشغيل التجريبي
if SUPABASE_KEY:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
else:
    supabase = None

# مفتاح Groq
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
client = Groq(api_key=GROQ_API_KEY)

# دالة برمجية (Middleware) للفحص هل حساب المستخدم Pro أم لا
def check_pro_badge(user_id: str):
    if not supabase:
        # في بيئة التطوير المحلية إذا لم يتوفر المفتاح، نمرر الطلب مؤقتاً للتجربة
        return True
        
    if not user_id or user_id in ["null", "undefined", "guest"]:
         raise HTTPException(status_code=401, detail="يرجى تسجيل الدخول أولاً لاستخدام هذه الميزة.")
    try:
        response = supabase.table("profiles").select("subscription_tier").eq("id", user_id).single().execute()
        if response.data and response.data.get("subscription_tier") == "pro":
            return True
        return False
    except Exception:
        raise HTTPException(status_code=401, detail="فشل التحقق من حساب المستخدم.")

class TextPrompt(BaseModel):
    text: str
    dialect: str
    user_id: str = "guest"

def get_strict_system_prompt(dialect: str) -> str:
    return f"""
    You are 'Sawtak AI' (صوتك), a premium conversational assistant optimized ONLY for 3 languages: Arabic, English, and French.
   
    CRITICAL INSTRUCTIONS:
    1. STRICT LANGUAGE RESTRICTION: You are allowed to respond ONLY in one of these three languages: Arabic (العربية), English, or French (Français). NEVER respond in any other language under any circumstances.
    2. MATCH USER LANGUAGE: Detect which of the 3 allowed languages the user is speaking or writing, and respond 100% in that exact language. No language mixing.
    3. DIALECT ADAPTATION: If the user communicates in Arabic, adapt your tone naturally to match their context or their preferred style/dialect: ({dialect}). Understand local phrasing, slang, and common expressions perfectly.
    4. Keep answers highly interactive, professional, and clear.
    """

# 🔓 ميزة مجانية: الشات النصي (متاحة للجميع)
@app.post("/api/chat/text")
async def chat_text(prompt: TextPrompt):
    try:
        system_msg = get_strict_system_prompt(prompt.dialect)
        completion = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": system_msg},
                {"role": "user", "content": prompt.text}
            ],
            temperature=0.4
        )
        return {"status": "success", "response": completion.choices[0].message.content.strip()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# 🔓 ميزة مجانية: الشات الصوتي (متاحة للجميع)
@app.post("/api/chat/audio")
async def chat_audio(dialect: str = Form(...), user_id: str = Form("guest"), file: UploadFile = File(...)):
    try:
        audio_bytes = await file.read()
        temp_filename = "temp_audio.wav"
        with open(temp_filename, "wb") as f:
            f.write(audio_bytes)
           
        with open(temp_filename, "rb") as audio_file:
            transcription = client.audio.transcriptions.create(
                file=audio_file,
                model="whisper-large-v3",
                response_format="text",
                language="ar",
                prompt="السلام عليكم، كيف حالك؟ أهلاً بك. من هو ليونيل ميسي؟ كيف الطقس اليوم?"
            )
        captured_text = str(transcription).strip()
        os.remove(temp_filename)
       
        if not captured_text or captured_text.isspace():
            return {"status": "success", "user_speech": "...", "response": "لم أتمكن من سماع أي صوت بوضوح، أرجو المحاولة مرة أخرى بقرب المايك."}
       
        system_msg = get_strict_system_prompt(dialect)
        completion = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": system_msg},
                {"role": "user", "content": captured_text}
            ],
            temperature=0.4
        )
        return {
            "status": "success",
            "user_speech": captured_text,
            "response": completion.choices[0].message.content.strip()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# 🔒 ميزة مدفوعة: رؤية وتحليل الصور (تطلب باقة Pro)
@app.post("/api/chat/vision")
async def chat_vision(text: str = Form(""), dialect: str = Form(""), user_id: str = Form(...), file: UploadFile = File(...)):
    # خطوة التحقق من باقة المستخدم
    is_pro = check_pro_badge(user_id)
    if not is_pro:
        return {
            "status": "upgrade_required",
            "response": "⚠️ ميزة تحليل ورؤية الصور مخصصة حصرياً للمشتركين في باقة 'صوتك AI Pro'. يرجى ترقية حسابك لفتح هذه الميزة وميزات توليد الصور القادمة!"
        }
        
    try:
        image_bytes = await file.read()
        base64_image = base64.b64encode(image_bytes).decode('utf-8')
       
        system_msg = get_strict_system_prompt(dialect)
        completion = client.chat.completions.create(
            model="llama-3.2-11b-vision-instant",
            messages=[
                {"role": "system", "content": system_msg},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": text if text else "Analyze and describe this image clearly using one of the allowed languages (Arabic, English, French)."},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                    ]
                }
            ],
            temperature=0.3
        )
        return {"status": "success", "response": completion.choices[0].message.content.strip()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

