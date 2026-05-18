const API_BASE = "https://my-voice-ai.onrender.com/api"; // رابط الباكيند الخاص بك المباشر

// عناصر واجهة المستخدم
const settingsBtn = document.getElementById("settingsBtn");
const settingsModal = document.getElementById("settingsModal");
const closeSettings = document.getElementById("closeSettings");
const welcomeScreen = document.getElementById("welcomeScreen");
const chatMessages = document.getElementById("chatMessages");
const userInput = document.getElementById("userInput");
const sendBtn = document.getElementById("sendBtn");
const dialectSelect = document.getElementById("dialectSelect");
const clearChatBtn = document.getElementById("clearChatBtn");

// فتح وإغلاق إعدادات المودال الاحترافية
settingsBtn.onclick = () => settingsModal.style.display = "flex";
closeSettings.onclick = () => settingsModal.style.display = "none";
window.onclick = (e) => { if(e.target === settingsModal) settingsModal.style.display = "none"; }

// وضع سؤال جاهز من البطاقات المقترحة
function setPresetPrompt(promptText) {
    userInput.value = promptText;
    userInput.focus();
}

// دالة إضافة الرسائل وعرضها في الشات بشكل أنيق
function appendMessage(text, sender) {
    // إخفاء شاشة البطاقات الترحيبية عند أول رسالة فوراً
    if (welcomeScreen) welcomeScreen.style.display = "none";
    
    const msgDiv = document.createElement("div");
    msgDiv.classList.add("message", sender === "user" ? "user" : "ai");
    msgDiv.innerText = text;
    chatMessages.appendChild(msgDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

// إرسال النص الفوري للباكيند
sendBtn.onclick = async () => {
    const text = userInput.value.trim();
    if (!text) return;
    
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
            appendMessage("عذراً، حدث خطأ في معالجة الرد.", "ai");
        }
    } catch (err) {
        appendMessage("فشل الاتصال بالسيرفر الحي.", "ai");
    }
};

// مسح المحادثة بالكامل وإعادة الشاشة الترحيبية
clearChatBtn.onclick = () => {
    chatMessages.innerHTML = '';
    chatMessages.appendChild(welcomeScreen);
    welcomeScreen.style.display = "flex";
    settingsModal.style.display = "none";
};

