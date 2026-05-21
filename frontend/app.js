import { supabase } from './supabaseClient.js';

const BACKEND_URL = 'https://my-voice-ai.onrender.com';

// استدعاء عناصر الواجهة بدقة
const authNavBtn = document.getElementById('auth-nav-btn');
const authModal = document.getElementById('auth-modal');
const closeAuth = document.getElementById('closeAuth');
const authTitle = document.getElementById('auth-title');
const authEmail = document.getElementById('auth-email');
const authPassword = document.getElementById('auth-password');
const authSubmitBtn = document.getElementById('auth-submit-btn');
const authToggleText = document.getElementById('auth-toggle-text');
const userBadge = document.getElementById('user-badge');

const settingsBtn = document.getElementById('settingsBtn');
const settingsModal = document.getElementById('settingsModal');
const closeSettings = document.getElementById('closeSettings');
const clearChatBtn = document.getElementById('clearChatBtn');
const dialectSelect = document.getElementById('dialectSelect');

const upgradeModal = document.getElementById('upgrade-modal');
const closeUpgrade = document.getElementById('closeUpgrade');
const upgradeMessage = document.getElementById('upgrade-message');
const subscribeBtn = document.getElementById('subscribe-btn');

const userInput = document.getElementById('userInput');
const sendBtn = document.getElementById('sendBtn');
const imgBtn = document.getElementById('imgBtn');
const fileInput = document.getElementById('fileInput');
const micBtn = document.getElementById('micBtn');
const previewContainer = document.getElementById('previewContainer');
const waveAnimation = document.getElementById('waveAnimation');
const welcomeScreen = document.getElementById('welcomeScreen');
const chatMessages = document.getElementById('chatMessages');

let isSignUpMode = false;
let currentUser = null;
let userProfile = null;
let selectedImageFile = null; // الاحتفاظ بملف الصورة الفعلي لإرساله كـ Form Data
let selectedImageBase64 = null;
let mediaRecorder = null;
let audioChunks = [];

// الانتظار حتى تحميل الصفحة بالكامل لضمان قراءة الأزرار
window.addEventListener('DOMContentLoaded', () => {
   
    if(authNavBtn) {
        authNavBtn.onclick = () => handleAuthNavAction();
    }

    if(closeAuth) {
        closeAuth.onclick = () => { authModal.style.display = 'none'; };
    }

    if(settingsBtn) {
        settingsBtn.onclick = () => { settingsModal.style.display = 'flex'; };
    }

    if(closeSettings) {
        closeSettings.onclick = () => { settingsModal.style.display = 'none'; };
    }

    if(closeUpgrade) {
        closeUpgrade.onclick = () => { upgradeModal.style.display = 'none'; };
    }

    if(authToggleText) {
        authToggleText.onclick = () => {
            isSignUpMode = !isSignUpMode;
            if(isSignUpMode) {
                authTitle.innerText = "إنشاء حساب سيبراني جديد";
                authSubmitBtn.innerText = "إنشاء الحساب";
                authToggleText.innerHTML = 'لديك حساب بالفعل؟ <span style="color: var(--accent); font-weight: bold;">سجل دخولك</span>';
            } else {
                authTitle.innerText = "بوابة الوصول الموحدة";
                authSubmitBtn.innerText = "تسجيل الدخول";
                authToggleText.innerHTML = 'ليس لديك حساب سيبراني؟ <span style="color: var(--accent); font-weight: bold;">أنشئ حسابك الآن</span>';
            }
        };
    }

    if(authSubmitBtn) {
        authSubmitBtn.onclick = async () => {
            const email = authEmail.value.trim();
            const password = authPassword.value;
            if(!email || !password) return alert("الرجاء ملء كافة الحقول المتاحة.");

            try {
                if(isSignUpMode) {
                    const { data, error } = await supabase.auth.signUp({ email, password });
                    if(error) throw error;
                    alert("تم إنشاء حسابك بنجاح! يرجى مراجعة بريدك الإلكتروني لتأكيد الحساب.");
                } else {
                    const { data, error } = await supabase.auth.signInWithPassword({ email, password });
                    if(error) throw error;
                    authModal.style.display = 'none';
                }
            } catch (err) {
                alert("خطأ في العملية: " + err.message);
            }
        };
    }

    if(subscribeBtn) {
        subscribeBtn.onclick = async () => {
            if(!currentUser) {
                alert("يرجى تسجيل الدخول أولاً لتتمكن من الاشتراك.");
                upgradeModal.style.display = 'none';
                authModal.style.display = 'flex';
                return;
            }
            const { error } = await supabase.from('profiles').upsert({ id: currentUser.id, subscription_tier: 'pro' });
            if(!error) {
                alert("🎉 مبروك! تم تفعيل باقة Pro بنجاح!");
                upgradeModal.style.display = 'none';
                await fetchUserProfile();
            } else {
                alert("فشل التحديث: " + error.message);
            }
        };
    }

    if(imgBtn) imgBtn.onclick = () => fileInput.click();

    if(fileInput) {
        fileInput.onchange = (e) => {
            const file = e.target.files[0];
            if(!file) return;
            selectedImageFile = file;
            const reader = new FileReader();
            reader.onload = (event) => {
                selectedImageBase64 = event.target.result;
                previewContainer.innerHTML = `
                    <div class="preview-box">
                        <img src="${selectedImageBase64}">
                        <button class="remove-preview" id="clearPreviewBtn">&times;</button>
                    </div>
                `;
                document.getElementById('clearPreviewBtn').onclick = () => {
                    selectedImageBase64 = null;
                    selectedImageFile = null;
                    previewContainer.innerHTML = '';
                    fileInput.value = '';
                };
            };
            reader.readAsDataURL(file);
        };
    }

    if(sendBtn) sendBtn.onclick = handleSendMessage;
    if(userInput) {
        userInput.onkeypress = (e) => {
            if(e.key === 'Enter') handleSendMessage();
        };
    }

    if(clearChatBtn) {
        clearChatBtn.onclick = () => {
            chatMessages.innerHTML = '';
            if(welcomeScreen) welcomeScreen.style.display = 'flex';
            settingsModal.style.display = 'none';
        };
    }

    if(micBtn) {
        micBtn.onclick = async () => {
            if (mediaRecorder && mediaRecorder.state === "recording") {
                mediaRecorder.stop();
                waveAnimation.style.display = 'none';
                micBtn.style.color = 'var(--text-muted)';
            } else {
                try {
                    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
                    mediaRecorder = new MediaRecorder(stream);
                    audioChunks = [];
                   
                    mediaRecorder.ondataavailable = e => audioChunks.push(e.data);
                    mediaRecorder.onstop = async () => {
                        const audioBlob = new Blob(audioChunks, { type: 'audio/wav' });
                        if(welcomeScreen) welcomeScreen.style.display = 'none';
                        const aiMsg = appendMessage('ai', 'جاري تحليل صوتك العذب وبناء الإجابة...');
                       
                        try {
                            const dialect = dialectSelect ? dialectSelect.value : 'الفصحى';
                            const userId = currentUser ? currentUser.id : 'guest';

                            const formData = new FormData();
                            formData.append("file", audioBlob, "audio.wav");
                            formData.append("dialect", dialect);
                            formData.append("user_id", userId);

                            const res = await fetch(`${BACKEND_URL}/api/chat/audio`, {
                                method: 'POST',
                                body: formData
                            });
                            const data = await res.json();
                           
                            aiMsg.remove();
                            if(data.status === "success") {
                                appendMessage('user', data.user_speech);
                                const replyDiv = appendMessage('ai', data.response);
                                addTTSButton(replyDiv, data.response, dialect);
                            } else {
                                appendMessage('ai', "تعذر معالجة الصوت: " + (data.detail || "خطأ مجهول"));
                            }
                        } catch {
                            aiMsg.innerText = "فشل الاتصال بسيرفر الصوت المباشر.";
                        }
                    };
                   
                    mediaRecorder.start();
                    waveAnimation.style.display = 'flex';
                    micBtn.style.color = '#ef4444';
                } catch {
                    alert("يرجى إعطاء صلاحية الوصول للمايكروفون.");
                }
            }
        };
    }
});

if (supabase && supabase.auth) {
    supabase.auth.onAuthStateChange(async (event, session) => {
        currentUser = session ? session.user : null;
        if (currentUser) {
            await fetchUserProfile();
        } else {
            userProfile = null;
            if(authNavBtn) {
                authNavBtn.innerHTML = '<i class="fa-solid fa-user-gear"></i> تسجيل الدخول';
                authNavBtn.classList.remove('pro-user');
            }
            if(userBadge) userBadge.style.display = 'none';
        }
    });
}

function handleAuthNavAction() {
    if (currentUser) {
        if(confirm("هل ترغب في تسجيل الخروج من النظام؟")) {
            supabase.auth.signOut();
        }
    } else {
        authModal.style.display = 'flex';
    }
}

async function fetchUserProfile() {
    if(!currentUser) return;
    const { data, error } = await supabase.from('profiles').select('*').eq('id', currentUser.id).single();
    if(!error && data) {
        userProfile = data;
        const tier = userProfile.subscription_tier || userProfile.subscription;
        if(authNavBtn) {
            if(tier === 'pro') {
                authNavBtn.innerHTML = '<i class="fa-solid fa-crown"></i> حساب Pro (خروج)';
                authNavBtn.classList.add('pro-user');
                if(userBadge) userBadge.style.display = 'inline-block';
            } else {
                authNavBtn.innerHTML = '<i class="fa-solid fa-user-astronaut"></i> حساب مجاني (خروج)';
                authNavBtn.classList.remove('pro-user');
                if(userBadge) userBadge.style.display = 'none';
            }
        }
    }
}

async function handleSendMessage() {
    const tempText = userInput.value.trim();
    if(!tempText && !selectedImageBase64) return;

    const dialect = dialectSelect ? dialectSelect.value : 'الفصحى';
    const userId = currentUser ? currentUser.id : 'guest';

    if(welcomeScreen) welcomeScreen.style.display = 'none';

    appendMessage('user', tempText, selectedImageBase64);
    userInput.value = '';
   
    const tempImageFile = selectedImageFile;

    if(previewContainer) previewContainer.innerHTML = '';
    selectedImageBase64 = null;
    selectedImageFile = null;

    const aiMessageDiv = appendMessage('ai', 'جاري التفكير المالي والسيبراني...');

    try {
        let response;
        if(tempImageFile) {
            const formData = new FormData();
            formData.append("text", tempText);
            formData.append("dialect", dialect);
            formData.append("user_id", userId);
            formData.append("file", tempImageFile);

            response = await fetch(`${BACKEND_URL}/api/chat/vision`, {
                method: 'POST',
                body: formData
            });
        }
        else {
            response = await fetch(`${BACKEND_URL}/api/chat/text`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ text: tempText, dialect: dialect, user_id: userId })
            });
        }

        const result = await response.json();
       
        if(result.status === "success") {
            // إرسال النص الصافي للمكتبة لمعالجته بشكل سليم داخل العنصر الفرعي
            const containerSpan = aiMessageDiv.querySelector('.markdown-body');
            if(containerSpan && typeof marked !== 'undefined') {
                marked.setOptions({ breaks: true, gfm: true });
                containerSpan.innerHTML = marked.parse(result.response);
            } else if (containerSpan) {
                containerSpan.innerText = result.response;
            }
            addTTSButton(aiMessageDiv, result.response, dialect);
        } else if (result.status === "upgrade_required") {
            const containerSpan = aiMessageDiv.querySelector('.markdown-body');
            if(containerSpan) containerSpan.innerText = result.response;
            upgradeMessage.innerText = result.response;
            upgradeModal.style.display = 'flex';
        } else {
            const containerSpan = aiMessageDiv.querySelector('.markdown-body');
            if(containerSpan) containerSpan.innerText = "تنبيه: " + (result.detail || "تعذر إرجاع رد صالح.");
        }
    } catch (err) {
        const containerSpan = aiMessageDiv.querySelector('.markdown-body');
        if(containerSpan) containerSpan.innerText = "عذراً، تعذر الاتصال بالسيرفر السحابي الحالي.";
    }
}

function appendMessage(sender, text, imageSrc = null) {
    const msgDiv = document.createElement('div');
    msgDiv.classList.add('message', sender);
   
    if(imageSrc) {
        const img = document.createElement('img');
        img.src = imageSrc;
        img.style.maxWidth = '200px';
        img.style.borderRadius = '8px';
        img.style.marginBottom = '5px';
        img.style.display = 'block';
        msgDiv.appendChild(img);
    }
   
    if(text) {
        const textSpan = document.createElement('span');
        textSpan.classList.add('markdown-body');
        
        // التحويل المباشر للرسائل الفورية والذكاء الاصطناعي
        if (sender === 'ai' && typeof marked !== 'undefined' && text !== 'جاري التفكير المالي والسيبراني...') {
            marked.setOptions({ breaks: true, gfm: true });
            textSpan.innerHTML = marked.parse(text);
        } else {
            textSpan.innerText = text;
        }
        msgDiv.appendChild(textSpan);
    }

    chatMessages.appendChild(msgDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
    return msgDiv;
}

function addTTSButton(container, text, dialect) {
    const btn = document.createElement('button');
    btn.classList.add('tts-inline-btn');
    btn.innerHTML = '<i class="fa-solid fa-volume-high"></i> استمع للرد';
    btn.onclick = async () => {
        btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> جاري التوليد...';
        try {
            const res = await fetch(`${BACKEND_URL}/api/tts`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ text, dialect })
            });
            const audioBlob = await res.blob();
            const audioUrl = URL.createObjectURL(audioBlob);
            const audio = new Audio(audioUrl);
            audio.play();
            btn.innerHTML = '<i class="fa-solid fa-volume-high"></i> استمع للرد';
        } catch {
            btn.innerHTML = '<i class="fa-solid fa-circle-exclamation"></i> خطأ في الصوت';
        }
    };
    container.appendChild(btn);
}

