import { supabase } from './supabaseClient.js';

// رابط السيرفر السحابي الخاص بك على Render
const BACKEND_URL = 'https://my-voice-ai.onrender.com';

// استدعاء عناصر الواجهة بدقة متناهية متوافقة مع الـ HTML
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
let selectedImageBase64 = null;
let mediaRecorder = null;
let audioChunks = [];

// --- تشغيل وإدارة النوافذ المنبثقة بربط سريع ومباشر ---

if(authNavBtn) {
    authNavBtn.onclick = function() {
        handleAuthNavAction();
    };
}

if(closeAuth) {
    closeAuth.onclick = function() {
        authModal.style.display = 'none';
    };
}

if(settingsBtn) {
    settingsBtn.onclick = function() {
        settingsModal.style.display = 'flex';
    };
}

if(closeSettings) {
    closeSettings.onclick = function() {
        settingsModal.style.display = 'none';
    };
}

if(closeUpgrade) {
    closeUpgrade.onclick = function() {
        upgradeModal.style.display = 'none';
    };
}

// التبديل بين وضع تسجيل حساب جديد أو تسجيل الدخول
if(authToggleText) {
    authToggleText.onclick = function() {
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

// مراقبة حالة المستخدم الحالية عند فتح الموقع من سوبابيس
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

function handleAuthNavAction() {
    if (currentUser) {
        if(confirm("هل ترغب في تسجيل الخروج من النظام؟")) {
            supabase.auth.signOut();
        }
    } else {
        authModal.style.display = 'flex';
    }
}

// تنفيذ عمليات التسجيل والدخول في سوبابيس عند الضغط
if(authSubmitBtn) {
    authSubmitBtn.onclick = async function() {
        const email = authEmail.value.trim();
        const password = authPassword.value;
        if(!email || !password) return alert("الرجاء ملء كافة الحقول المتاحة.");

        try {
            if(isSignUpMode) {
                const { data, error } = await supabase.auth.signUp({ email, password });
                if(error) throw error;
                alert("تم إنشاء حسابك بنجاح! إذا كانت قاعدة بياناتك تتطلب تأكيد البريد، يرجى مراجعة صندوق الوارد.");
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

// جلب بيانات البروفايل ونوع الباقة (Free / Pro)
async function fetchUserProfile() {
    if(!currentUser) return;
    const { data, error } = await supabase.from('profiles').select('*').eq('id', currentUser.id).single();
    if(!error && data) {
        userProfile = data;
        if(authNavBtn) {
            if(userProfile.subscription === 'pro') {
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

// زر الترقية إلى باقة الـ Pro
if(subscribeBtn) {
    subscribeBtn.onclick = async function() {
        if(!currentUser) {
            alert("يرجى تسجيل الدخول أولاً لتتمكن من الاشتراك التلقائي.");
            upgradeModal.style.display = 'none';
            authModal.style.display = 'flex';
            return;
        }
        const { error } = await supabase.from('profiles').upsert({ id: currentUser.id, subscription: 'pro' });
        if(!error) {
            alert("🎉 مبروك! تم تفعيل اشتراكك في باقة صوتك Pro الذهبية بنجاح وانفتحت لك ميزة الرؤية الآن!");
            upgradeModal.style.display = 'none';
            await fetchUserProfile();
        } else {
            alert("فشل التحديث: " + error.message);
        }
    };
}

// --- التعامل مع رفع الصور ومعاينتها ---
if(imgBtn) imgBtn.onclick = () => fileInput.click();
if(fileInput) {
    fileInput.onchange = function(e) {
        const file = e.target.files[0];
        if(!file) return;
        const reader = new FileReader();
        reader.onload = function(event) {
            selectedImageBase64 = event.target.result;
            previewContainer.innerHTML = `
                <div class="preview-box">
                    <img src="${selectedImageBase64}">
                    <button class="remove-preview" id="clearPreviewBtn">&times;</button>
                </div>
            `;
            document.getElementById('clearPreviewBtn').onclick = function() {
                selectedImageBase64 = null;
                previewContainer.innerHTML = '';
                fileInput.value = '';
            };
        };
        reader.readAsDataURL(file);
    };
}

// --- التعامل مع إرسال الرسائل ---
if(sendBtn) sendBtn.onclick = handleSendMessage;
if(userInput) {
    userInput.onkeypress = function(e) {
        if(e.key === 'Enter') handleSendMessage();
    };
}

async function handleSendMessage() {
    const text = userInput.value.trim();
    if(!text && !selectedImageBase64) return;

    if(selectedImageBase64) {
        if(!currentUser) {
            upgradeMessage.innerText = "عذراً يا غالي! ميزة 'التحليل البصري الذكي وقراءة الصور' مخصصة فقط للمشتركين. يرجى تسجيل حسابك أولاً للترقية.";
            upgradeModal.style.display = 'flex';
            return;
        }
        if(!userProfile || userProfile.subscription !== 'pro') {
            upgradeMessage.innerText = "أنت على بعد خطوة واحدة! ميزة تحليل الصور وقراءتها تتطلب ترقية حسابك إلى باقة Pro الفاخرة.";
            upgradeModal.style.display = 'flex';
            return;
        }
    }

    if(welcomeScreen) welcomeScreen.style.display = 'none';

    appendMessage('user', text, selectedImageBase64);
    userInput.value = '';
    const tempImage = selectedImageBase64;
    if(previewContainer) previewContainer.innerHTML = '';
    selectedImageBase64 = null;

    const aiMessageDiv = appendMessage('ai', 'جاري التفكير وصياغة الرد السيبراني المذهل...');

    try {
        const dialect = dialectSelect ? dialectSelect.value : 'الفصحى';
        const response = await fetch(`${BACKEND_URL}/api/chat`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                message: text,
                image: tempImage,
                dialect: dialect
            })
        });

        const result = await response.json();
        if(result.success) {
            aiMessageDiv.innerHTML = `<div>${result.reply}</div>`;
            addTTSButton(aiMessageDiv, result.reply, dialect);
        } else {
            aiMessageDiv.innerText = "خطأ من السيرفر: " + result.error;
        }
    } catch (err) {
        aiMessageDiv.innerText = "عذراً، تعذر الاتصال بالسيرفر السحابي. تأكد من إعداد المفاتيح على Render.";
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
        textSpan.innerText = text;
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
    btn.onclick = async function() {
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

// --- التعامل مع مسجل الصوت (المايكروفون) ---
if(micBtn) {
    micBtn.onclick = async function() {
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
                    const reader = new FileReader();
                    reader.onloadend = async () => {
                        const base64Audio = reader.result.split(',')[1];
                        if(welcomeScreen) welcomeScreen.style.display = 'none';
                        const aiMsg = appendMessage('ai', 'جاري تحليل صوتك العذب وتحويله لنص رفيع...');
                        
                        try {
                            const res = await fetch(`${BACKEND_URL}/api/transcribe`, {
                                method: 'POST',
                                headers: { 'Content-Type': 'application/json' },
                                body: JSON.stringify({ audio: base64Audio })
                            });
                            const data = await res.json();
                            if(data.success) {
                                aiMsg.remove();
                                userInput.value = data.text;
                                handleSendMessage();
                            } else {
                                aiMsg.innerText = "تعذر تحويل الصوت: " + data.error;
                            }
                        } catch {
                            aiMsg.innerText = "فشل الاتصال بسيرفر الصوت الخاص بك.";
                        }
                    };
                    reader.readAsDataURL(audioBlob);
                };
                
                mediaRecorder.start();
                waveAnimation.style.display = 'flex';
                micBtn.style.color = '#ef4444';
            } catch {
                alert("يرجى إعطاء صلاحية الوصول للمايكروفون لبدء التسجيل.");
            }
        }
    };
}

if(clearChatBtn) {
    clearChatBtn.onclick = function() {
        chatMessages.innerHTML = '';
        if(welcomeScreen) welcomeScreen.style.display = 'flex';
        settingsModal.style.display = 'none';
    };
}

