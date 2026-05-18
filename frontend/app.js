const API_BASE = "https://my-voice-ai.onrender.com/api";
let mediaRecorder;
let audioChunks = [];
let isRecording = false;
let selectedFile = null;

const messagesContainer = document.getElementById("messagesContainer");
const userInput = document.getElementById("userInput");
const sendBtn = document.getElementById("sendBtn");
const dialectSelect = document.getElementById("dialectSelect");
const imageUpload = document.getElementById("imageUpload");
const previewBox = document.getElementById("previewBox");
const previewName = document.getElementById("previewName");
const removeFileBtn = document.getElementById("removeFileBtn");
const audioRecordBtn = document.getElementById("audioRecordBtn");
const micIcon = document.getElementById("micIcon");
const clearChatBtn = document.getElementById("clearChatBtn");

function appendMessage(role, text) {
    const dir = /[\u0600-\u06FF]/.test(text) ? "rtl" : "ltr";
    const bubble = document.createElement("div");
    bubble.className = `bubble ${role}`;
    bubble.style.direction = dir;
    bubble.style.textAlign = dir === "rtl" ? "right" : "left";
    bubble.innerText = text;

    if (role === "ai") {
        const ttsBtn = document.createElement("button");
        ttsBtn.className = "tts-btn";
        ttsBtn.innerHTML = `<i class="fas fa-volume-up"></i> استمع`;
        ttsBtn.onclick = () => {
            window.speechSynthesis.cancel();
            const utterance = new SpeechSynthesisUtterance(text);
            utterance.lang = dir === "rtl" ? "ar-SA" : "en-US";
            window.speechSynthesis.speak(utterance);
        };
        bubble.appendChild(ttsBtn);
    }
    messagesContainer.appendChild(bubble);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

async function handleSend() {
    const text = userInput.value.trim();
    const dialect = dialectSelect.value;
    if (!text && !selectedFile) return;

    if (text) appendMessage("user", text);
    else if (selectedFile) appendMessage("user", `📸 [صورة]: ${selectedFile.name}`);
    userInput.value = "";
    
    try {
        let data;
        if (selectedFile) {
            const formData = new FormData();
            formData.append("text", text);
            formData.append("dialect", dialect);
            formData.append("file", selectedFile);
            const res = await fetch(`${API_BASE}/chat/vision`, { method: "POST", body: formData });
            data = await res.json();
            clearFile();
        } else {
            const res = await fetch(`${API_BASE}/chat/text`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ text, dialect })
            });
            data = await res.json();
        }
        if (data.status === "success") appendMessage("ai", data.response);
    } catch (err) { appendMessage("ai", "❌ خطأ في الاتصال بالخادم."); }
}

imageUpload.addEventListener("change", (e) => {
    if (e.target.files.length > 0) {
        selectedFile = e.target.files[0];
        previewName.innerText = selectedFile.name;
        previewBox.style.display = "flex";
    }
});
function clearFile() { selectedFile = null; previewBox.style.display = "none"; imageUpload.value = ""; }
removeFileBtn.onclick = clearFile;

audioRecordBtn.onclick = async () => {
    if (!isRecording) {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        mediaRecorder = new MediaRecorder(stream);
        audioChunks = [];
        mediaRecorder.ondataavailable = e => audioChunks.push(e.data);
        mediaRecorder.onstop = async () => {
            const audioBlob = new Blob(audioChunks, { type: "audio/wav" });
            const formData = new FormData();
            formData.append("dialect", dialectSelect.value);
            formData.append("file", audioBlob, "voice.wav");
            appendMessage("user", "🎙️ [جاري معالجة الصوت...]");
            try {
                const res = await fetch(`${API_BASE}/chat/audio`, { method: "POST", body: formData });
                const data = await res.json();
                if (data.status === "success") {
                    messagesContainer.lastChild.innerText = `🎙️ ${data.user_speech}`;
                    appendMessage("ai", data.response);
                }
            } catch (err) { appendMessage("ai", "❌ فشل معالجة الملف الصوتي."); }
        };
        mediaRecorder.start();
        isRecording = true;
        audioRecordBtn.classList.add("recording");
        micIcon.className = "fas fa-stop";
    } else {
        mediaRecorder.stop();
        isRecording = false;
        audioRecordBtn.classList.remove("recording");
        micIcon.className = "fas fa-microphone";
    }
};

sendBtn.onclick = handleSend;
userInput.onkeydown = e => { if (e.key === "Enter") handleSend(); };
clearChatBtn.onclick = () => messagesContainer.innerHTML = "";

