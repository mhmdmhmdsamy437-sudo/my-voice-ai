import os
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

def get_strict_system_prompt(dialect: str) -> str:
    return f"""
    You are 'Sawtak AI' (صوتك), a premium multi-lingual conversational assistant.
    
    CRITICAL INSTRUCTIONS:
    1. MATCH USER LANGUAGE: Detect the exact language the user is speaking or writing (Arabic, English, French, etc.) and respond ONLY in that same language.
    2. NO MIXING: Do not mix languages. If the user writes in Arabic, respond 100% in Arabic. If they write in English, respond 100% in English.
    3. DIALECT ADAPTATION: If the user communicates in Arabic, adapt your tone naturally to match their context or their preferred style/dialect: ({dialect}). Understand slang, local words, and general phrasing perfectly.
    4. Keep answers highly interactive, professional, and clear.
    """

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

@app.post("/api/chat/vision")
async def chat_vision(text: str = Form(""), dialect: str = Form(""), file: UploadFile = File(...)):
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
                        {"type": "text", "text": text if text else "Analyze and describe this image clearly."},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                    ]
                }
            ],
            temperature=0.3
        )
        return {"status": "success", "response": completion.choices[0].message.content.strip()}
    except Exception as e: 
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/chat/audio")
async def chat_audio(dialect: str = Form(...), file: UploadFile = File(...)):
    try:
        audio_bytes = await file.read()
        temp_filename = "temp_audio.wav"
        with open(temp_filename, "wb") as f: 
            f.write(audio_bytes)
            
        with open(temp_filename, "rb") as audio_file:
            transcription = client.audio.transcriptions.create(
                file=audio_file, 
                model="whisper-large-v3", 
                response_format="text"
            )
        captured_text = str(transcription).strip()
        os.remove(temp_filename)
        
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

