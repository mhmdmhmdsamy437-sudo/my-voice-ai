import os
import base64
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from groq import Groq
from supabase import create_client, Client

app = FastAPI(title="Sawtak AI Pro Backend")

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

class ChatRequest(BaseModel):
    message: str = ""
    image: str = None  
    dialect: str = "الفصحى"
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

# 🌐 الرابط الموحد المحدث المتوافق 100% مع الـ Frontend لمنع الـ undefined
@app.post("/api/chat")
async def chat_endpoint(request: ChatRequest):
    try:
        if request.image:
            if not check_pro_badge(request.user_id):
                return {"success": False, "reply": "⚠️ ميزة تحليل الصور مخصصة لباقة Pro."}
            
            img_data = request.image
            if "," in img_data:
                img_data = img_data.split(",")[1]

            system_msg = get_strict_system_prompt(request.dialect)
            completion = client.chat.completions.create(
                model="llama-3.2-11b-vision-instant",
                messages=[
                    {"role": "system", "content": system_msg},
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": request.message if request.message else "Analyze this image."},
                            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_data}"}}
                        ]
                    }
                ],
                temperature=0.3
            )
            return {"success": True, "reply": completion.choices[0].message.content.strip()}
        
        else:
            system_msg = get_strict_system_prompt(request.dialect)
            completion = client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[
                    {"role": "system", "content": system_msg},
                    {"role": "user", "content": request.message}
                ],
                temperature=0.4
            )
            return {"success": True, "reply": completion.choices[0].message.content.strip()}
    except Exception as e:
        return {"success": False, "error": str(e)}

# 🎙️ رابط معالجة الصوت المحدث ليفهمه الفرونتيند
class AudioRequest(BaseModel):
    audio: str

@app.post("/api/transcribe")
async def transcribe_audio(request: AudioRequest):
    try:
        audio_bytes = base64.b64decode(request.audio)
        temp_filename = "temp_audio.wav"
        with open(temp_filename, "wb") as f:
            f.write(audio_bytes)
           
        with open(temp_filename, "rb") as audio_file:
            transcription = client.audio.transcriptions.create(
                file=audio_file,
                model="whisper-large-v3",
                response_format="text",
                language="ar"
            )
        captured_text = str(transcription).strip()
        os.remove(temp_filename)
        return {"success": True, "text": captured_text}
    except Exception as e:
        if os.path.exists("temp_audio.wav"): os.remove("temp_audio.wav")
        return {"success": False, "error": str(e)}

@app.get("/")
def read_root():
    return {"status": "Live"}

