import os
import re
import base64
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from groq import Groq

app = FastAPI(title="Sawtak AI Pro Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
client = Groq(api_key=GROQ_API_KEY)

class TextPrompt(BaseModel):
    text: str
    dialect: str

# دالة ذكية ومطورة لإنشاء توجيه النظام بناءً على لهجة ولغة المستخدم تلقائياً
def generate_system_prompt(preferred_dialect: str) -> str:
    return f"""
    You are 'Sawtak AI' (صوتك), an advanced multilingual and multi-dialect AI assistant.
    
    CRITICAL RULES FOR LANGUAGE AND UNDERSTANDING:
    1. AUTOMATIC LANGUAGE MATCHING: You must detect the language used by the user in their message (Arabic, English, French, etc.) and respond ONLY in that exact same language.
    2. DIALECT FLEXIBILITY: The user might speak or write in standard language, local dialects, or general slang (especially Arabic dialects like Sudanese, Egyptian, Gulf, etc.). You must understand their intent perfectly regardless of any slang, local words, or typos.
    3. TARGET STYLE: If the user writes in Arabic, try to craft your response using their preferred style/dialect if possible: ({preferred_dialect}). If they write in English, French, or any other language, reply naturally in that language.
    4. Never mix languages in your response unless translating or using necessary technical terms. Keep your answers clear, helpful, and natural.
    """

@app.post("/api/chat/text")
async def chat_text(prompt: TextPrompt):
    try:
        system_msg = generate_system_prompt(prompt.dialect)
        completion = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "system", "content": system_msg}, {"role": "user", "content": prompt.text}],
            temperature=0.4
        )
        return {"status": "success", "response": completion.choices[0].message.content.strip()}
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/chat/vision")
async def chat_vision(text: str = Form(""), dialect: str = Form(""), file: UploadFile = File(...)):
    try:
        image_bytes = await file.read()
        base64_image = base64.b64encode(image_bytes).decode('utf-8')
        
        system_msg = generate_system_prompt(dialect)
        user_content = []
        user_content.append({"type": "text", "text": text if text else "Analyze this image and describe it in the user's language."})
        user_content.append({"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}})
        
        completion = client.chat.completions.create(
            model="llama-3.2-11b-vision-instant",
            messages=[
                {"role": "system", "content": system_msg},
                {"role": "user", "content": user_content}
            ],
            temperature=0.3
        )
        return {"status": "success", "response": completion.choices[0].message.content.strip()}
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/chat/audio")
async def chat_audio(dialect: str = Form(...), file: UploadFile = File(...)):
    try:
        audio_bytes = await file.read()
        temp_filename = "temp_audio.wav"
        with open(temp_filename, "wb") as f: f.write(audio_bytes)
        with open(temp_filename, "rb") as audio_file:
            transcription = client.audio.transcriptions.create(file=audio_file, model="whisper-large-v3", response_format="text")
        captured_text = str(transcription).strip()
        os.remove(temp_filename)
        
        system_msg = generate_system_prompt(dialect)
        completion = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "system", "content": system_msg}, {"role": "user", "content": captured_text}],
            temperature=0.4
        )
        return {"status": "success", "user_speech": captured_text, "response": completion.choices[0].message.content.strip()}
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

