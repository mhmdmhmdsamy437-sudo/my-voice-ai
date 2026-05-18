const API_BASE = "https://my-voice-ai.onrender.com/api"; // رابط الباكيند المباشر الخاص بك

// عناصر واجهة المستخدم الرئيسية
const settingsBtn = document.getElementById("settingsBtn");
const settingsModal = document.getElementById("settingsModal");
const closeSettings = document.getElementById("closeSettings");
const welcomeScreen = document.getElementById("welcomeScreen");
const chatMessages = document.getElementById("chatMessages");
const userInput = document.getElementById("userInput");
const sendBtn = document.getElementById("sendBtn");
const dialectSelect = document.getElementById("dialectSelect");
const clearChatBtn = document.getElementById("clearChatBtn");

// عناصر الصوت والصورة المدمجة الجديدة
const micBtn = document.getElementById("micBtn");
const imgBtn = document.getElementById("imgBtn");
const fileInput = document.getElementById("fileInput");
const waveAnimation = document.getElementById("waveAnimation");
const previewContainer = document.getElementById("previewContainer");

let mediaRecorder;
let audioChunks = [];
let isRecording = false;

// --- 1️⃣ تشغيل نافذة الإعدادات المنبثقة (Modal) ---
if (settingsBtn && settingsModal && closeSettings) {
    settingsBtn.onclick = () => { settingsModal.style.display = "flex"; };
    closeSettings.onclick = () => { settingsModal.style.display = "none"; };
    window.addEventListener("click", (e) => {
        if (e.target === settingsModal) {
            settingsModal.style.display = "none";
        }
    });
}

// --- 2️⃣ دالة وضع نص جاهز من بطاقات الاقتراحات ---
function setPresetPrompt(promptText) {
    if (userInput) {
        userInput.value = promptText;
        userInput.focus();
    }
}

// --- 3️⃣ دالة إضافة الرسائل في الشات ---
function appendMessage(text, sender) {
    if (welcomeScreen) welcomeScreen.style.display = "none";
   
    const msgDiv = document.createElement("div");
    msgDiv.classList.add("message", sender === "user" ? "user" : "ai");
   
    // إضافة زر الاستماع للنطق التلقائي إذا كان الرد من الذكاء الاصطناعي
    if (sender === "ai") {
        msgDiv.innerHTML = `<div>${text}</div><button class="tts-inline-btn" onclick="speakText(this, '${text.replace(/'/g, "\\'")}')"><i class="fa-solid fa-volume-high"></i> استمع</button>`;
    } else {
        msgDiv.innerText = text;
    }
   
    chatMessages.appendChild(msgDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

// --- 4️⃣ ميزة نطق النصوص الذكية لجميع اللغات ---
function speakText(btn, text) {
    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(text);
    const voices = window.speechSynthesis.getVoices();
   
    // البحث عن صوت عربي إذا كان النص يحتوي على حروف عربية
    if (/[\u0600-\u06FF]/.test(text)) {
        const arabicVoice = voices.find(v => v.lang.startsWith("ar"));
        if (arabicVoice) utterance.voice = arabicVoice;
        utterance.lang = "ar-EG";
    } else {
        utterance.lang = "en-US";
    }
    window.speechSynthesis.speak(utterance);
}

// --- 5️⃣ إرسال الرسائل النصية ---
sendBtn.onclick = async () => {
    const text = userInput.value.trim();
    if (!text && previewContainer.innerHTML === "") return;
   
    // إذا كان هناك صورة مرفوعة، نتوجه لقسم الفيجون
    if (fileInput.files.length > 0) {
        await sendVisionRequest(text);
        return;
    }
   
    appendMessage(text, "user");
    userInput.value = "";
   
    try {
        const res = await fetch(`${API_BASE}/chat/text`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ text: text, dialect: dialectSelect.value })
        });
        const data = await res.json();
        if (data.status === "success") {
            appendMessage(data.response, "ai");
        } else {
            appendMessage("عذراً، واجهت مشكلة في معالجة النص.", "ai");
        }
    } catch (err) {
        appendMessage("تعذر الاتصال بالسيرفر السحابي.", "ai");
    }
};

// --- 6️⃣ إدارة وتشغيل مسجل الصوت المتقدم (المايك) المحدث وحل مشكلة اللغات ---
if (micBtn) {
    micBtn.onclick = async () => {
        if (!isRecording) {
            try {
                const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
                
                // تحديد نوع المايم الأكثر استقراراً ودعماً في متصفحات الجوال والكمبيوتر وهو audio/webm
                let options = { mimeType: 'audio/webm' };
                if (!MediaRecorder.isTypeSupported(options.mimeType)) {
                    options = { mimeType: 'audio/ogg' }; // كخيار احتياطي لمتصفحات أخرى كـ Safari القديم
                }
                
                mediaRecorder = new MediaRecorder(stream, options);
                audioChunks = [];
               
                mediaRecorder.ondataavailable = (e) => { 
                    if (e.data && e.data.size > 0) {
                        audioChunks.push(e.data); 
                    }
                };
               
                mediaRecorder.onstop = async () => {
                    // تجميع الصوت بالصيغة الصحيحة الحقيقية المسجل بها لمنع التلف والوشيش
                    const audioBlob = new Blob(audioChunks, { type: mediaRecorder.mimeType });
                    
                    // للتأكد أن المستخدم نطق بالفعل وليس مجرد نقرة خاطئة
                    if (audioBlob.size > 1000) {
                        await sendAudioRequest(audioBlob);
                    }
                };
               
                // تجميع البيانات الصوتية بانتظام كل ثانية لضمان الثبات
                mediaRecorder.start(1000);
                isRecording = true;
                micBtn.style.color = "#ef4444"; // تغيير لون المايك للأحمر
                if (waveAnimation) waveAnimation.style.display = "flex"; // إظهار أنيميشن الموجات
            } catch (err) {
                alert("يرجى إعطاء صلاحية الوصول للمايكروفون أولاً.");
            }
        } else {
            // إيقاف التسجيل
            mediaRecorder.stop();
            // تحرير قنوات المايكروفون في الهاتف أو الكمبيوتر فوراً لإنهاء الإشارة وبث الملف بالكامل
            mediaRecorder.stream.getTracks().forEach(track => track.stop());
            isRecording = false;
            micBtn.style.color = "";
            if (waveAnimation) waveAnimation.style.display = "none"; // إخفاء الموجات
        }
    };
}

// دالة إرسال الملف الصوتي المعدلة للباكيند
async function sendAudioRequest(blob) {
    appendMessage("🎤 جاري معالجة وتفسير صوتك...", "user");
    const formData = new FormData();
    
    // إرسال الملف بالامتداد الفعلي الصحيح المتوافق مع سرفرات Whisper الكبيرة لعدم الخلط اللغوي
    const fileExtension = mediaRecorder.mimeType.includes('ogg') ? 'ogg' : 'webm';
    formData.append("file", blob, `audio.${fileExtension}`);
    formData.append("dialect", dialectSelect.value);
   
    try {
        const res = await fetch(`${API_BASE}/chat/audio`, { method: "POST", body: formData });
        const data = await res.json();
        if (data.status === "success") {
            // تحديث رسالة المستخدم بالنص الحقيقي المسموع بدقة
            chatMessages.lastChild.innerText = `🎤 ${data.user_speech}`;
            appendMessage(data.response, "ai");
        } else {
            chatMessages.lastChild.innerText = "⚠️ لم أتمكن من سماع الصوت بوضوح، حاول مجدداً.";
        }
    } catch (err) {
        chatMessages.lastChild.innerText = "⚠️ خطأ في الاتصال أثناء رفع الملف الصوتي.";
    }
}

// --- 7️⃣ إدارة رفع وتحليل الصور (Vision) ---
if (imgBtn && fileInput) {
    imgBtn.onclick = () => fileInput.click();
    fileInput.onchange = () => {
        if (fileInput.files.length > 0) {
            const file = fileInput.files[0];
            previewContainer.innerHTML = `<div class="img-preview-box"><img src="${URL.createObjectURL(file)}"><button onclick="clearImagePreview()">&times;</button></div>`;
        }
    };
}

function clearImagePreview() {
    fileInput.value = "";
    previewContainer.innerHTML = "";
}

async function sendVisionRequest(text) {
    appendMessage(text ? text : "📸 تم رفع صورة للتحليل...", "user");
    const formData = new FormData();
    formData.append("file", fileInput.files[0]);
    formData.append("text", text);
    formData.append("dialect", dialectSelect.value);
   
    clearImagePreview();
   
    try {
        const res = await fetch(`${API_BASE}/chat/vision`, { method: "POST", body: formData });
        const data = await res.json();
        if (data.status === "success") {
            appendMessage(data.response, "ai");
        } else {
            appendMessage("فشل تحليل الصورة المرفوعة.", "ai");
        }
    } catch (err) {
        appendMessage("خطأ في الاتصال بسيرفر الرؤية الذكي.", "ai");
    }
}

// --- 8️⃣ زر مساح الحوار ---
if (clearChatBtn) {
    clearChatBtn.onclick = () => {
        chatMessages.innerHTML = '';
        if (welcomeScreen) {
            chatMessages.appendChild(welcomeScreen);
            welcomeScreen.style.display = "flex";
        }
        if (settingsModal) settingsModal.style.display = "none";
    };
}

