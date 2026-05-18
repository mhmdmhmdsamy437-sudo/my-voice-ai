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

def identify_text_language(text: str) -> str:
    clean = text.strip().lower()
    if re.search(r'[\u0600-\u06FF]', clean): return "ar"
    if re.search(r'[a-zA-Z]', clean): return "en"
    return "ar"

class TextPrompt(BaseModel):
    text: str
    dialect: str

@app.post("/api/chat/text")
async def chat_text(prompt: TextPrompt):
    try:
        user_lang = identify_text_language(prompt.text)
        system_msg = f"أنت مساعد ذكي متمكن. صغ ردك بالكامل باللهجة التالية: ({prompt.dialect})." if user_lang == "ar" else "You are an elite English AI. Reply ONLY in English."
        completion = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "system", "content": system_msg}, {"role": "user", "content": prompt.text}],
            temperature=0.3
        )
        return {"status": "success", "response": completion.choices[0].message.content.strip()}
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/chat/vision")
async def chat_vision(text: str = Form(""), dialect: str = Form(""), file: UploadFile = File(...)):
    try:
        image_bytes = await file.read()
        base64_image = base64.b64encode(image_bytes).decode('utf-8')
        user_lang = identify_text_language(text) if text else "ar"
        system_msg = f"أنت خبير تحليل صور. صغ شرحك بالكامل باللهجة: ({dialect})." if user_lang == "ar" else "You are an expert English Vision AI. Analyze and reply in English."
        completion = client.chat.completions.create(
            model="llama-3.2-11b-vision-instant",
            messages=[
                {"role": "system", "content": system_msg},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": text if text else "Analyze this image"},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                    ]
                }
            ],
            temperature=0.2
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
        user_lang = identify_text_language(captured_text)
        system_msg = f"أنت مساعد ذكي متمكن. صغ ردك بالكامل باللهجة التالية: ({dialect})." if user_lang == "ar" else "You are an elite English AI. Reply ONLY in English."
        completion = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "system", "content": system_msg}, {"role": "user", "content": captured_text}],
            temperature=0.3
        )
        return {"status": "success", "user_speech": captured_text, "response": completion.choices[0].message.content.strip()}
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

