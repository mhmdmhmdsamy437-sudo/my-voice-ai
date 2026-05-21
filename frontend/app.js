import { supabase } from './supabaseClient.js';

// رابط الباكيند المباشر الخاص بك على ريندر
const API_BASE = "https://my-voice-ai.onrender.com/api"; 

// متغيرات عامة لحفظ حالة المستخدم الحالي والاشتراك
let currentUser = null;
let userSubscriptionTier = 'free';

// عناصر واجهة المستخدم الرئيسية القديمة
const settingsBtn = document.getElementById("settingsBtn");
const settingsModal = document.getElementById("settingsModal");
const closeSettings = document.getElementById("closeSettings");
const welcomeScreen = document.getElementById("welcomeScreen");
const chatMessages = document.getElementById("chatMessages");
const userInput = document.getElementById("userInput");
const sendBtn = document.getElementById("sendBtn");
const dialectSelect = document.getElementById("dialectSelect");
const clearChatBtn = document.getElementById("clearChatBtn");

// عناصر الصوت والصورة المدمجة
const micBtn = document.getElementById("micBtn");
const imgBtn = document.getElementById("imgBtn");
const fileInput = document.getElementById("fileInput");
const waveAnimation = document.getElementById("waveAnimation");
const previewContainer = document.getElementById("previewContainer");

let mediaRecorder;
let audioChunks = [];
let isRecording = false;

// --- 🌟 تحديث: تشغيل وفحص الجلسة عند تحميل الصفحة أول مرة ---
document.addEventListener("DOMContentLoaded", () => {
    // 1. حقن وتجهيز شاشات الحسابات والترقية ديناميكياً داخل الكود
    injectAuthUI();
    
    // 2. التحقق الفوري من حالة تسجيل الدخول الحالية للمستخدم
    checkCurrentUser();

    // 3. إعداد مستمعي الأحداث لنوافذ الحسابات والترقية
    setupAuthEventListeners();
});

// دالة فحص المستخدم الحالي من Supabase وجلب باقة اشتراكه
async function checkCurrentUser() {
    const { data: { session } } = await supabase.auth.getSession();
    if (session && session.user) {
        currentUser = session.user;
        
        // جلب تفاصيل الاشتراك من جدول البروفايل
        const { data: profile } = await supabase
            .table('profiles')
            .select('subscription_tier')
            .eq('id', currentUser.id)
            .single();
            
        if (profile) {
            userSubscriptionTier = profile.subscription_tier;
        }
        updateUIForLoggedInUser();
    } else {
        currentUser = null;
        userSubscriptionTier = 'free';
        updateUIForGuestUser();
    }
}

// --- 1️⃣ تشغيل نافذة الإعدادات المنبثقة (Modal) الأهلية ---
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
   
    if (sender === "ai") {
        msgDiv.innerHTML = `<div>${text}</div><button class="tts-inline-btn" onclick="speakText(this, '${text.replace(/'/g, "\\'")}')"><i class="fa-solid fa-volume-high"></i> استمع</button>`;
    } else {
        msgDiv.innerText = text;
    }
   
    chatMessages.appendChild(msgDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

// --- 4️⃣ ميزة نطق النصوص الذكية لجميع اللغات ---
window.speakText = function(btn, text) {
    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(text);
    const voices = window.speechSynthesis.getVoices();
   
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
if (sendBtn) {
    sendBtn.onclick = async () => {
        const text = userInput.value.trim();
        if (!text && previewContainer.innerHTML === "") return;
       
        // إذا كان هناك صورة مرفوعة، نتوجه فوراً لقسم الفيجون المدفوع لحمايته
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
                body: JSON.stringify({ 
                    text: text, 
                    dialect: dialectSelect.value,
                    user_id: currentUser ? currentUser.id : "guest"
                })
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
}

// --- 6️⃣ إدارة وتشغيل مسجل الصوت المتقدم (المايك) المحدث وحل مشكلة اللغات ---
if (micBtn) {
    micBtn.onclick = async () => {
        if (!isRecording) {
            try {
                const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
               
                let options = { mimeType: 'audio/webm' };
                if (!MediaRecorder.isTypeSupported(options.mimeType)) {
                    options = { mimeType: 'audio/ogg' }; 
                }
               
                mediaRecorder = new MediaRecorder(stream, options);
                audioChunks = [];
               
                mediaRecorder.ondataavailable = (e) => {
                    if (e.data && e.data.size > 0) {
                        audioChunks.push(e.data);
                    }
                };
               
                mediaRecorder.onstop = async () => {
                    const audioBlob = new Blob(audioChunks, { type: mediaRecorder.mimeType });
                   
                    if (audioBlob.size > 1000) {
                        await sendAudioRequest(audioBlob);
                    }
                };
               
                mediaRecorder.start(1000);
                isRecording = true;
                micBtn.style.color = "#ef4444"; 
                if (waveAnimation) waveAnimation.style.display = "flex"; 
            } catch (err) {
                alert("يرجى إعطاء صلاحية الوصول للمايكروفون أولاً.");
            }
        } else {
            mediaRecorder.stop();
            mediaRecorder.stream.getTracks().forEach(track => track.stop());
            isRecording = false;
            micBtn.style.color = "";
            if (waveAnimation) waveAnimation.style.display = "none"; 
        }
    };
}

// دالة إرسال الملف الصوتي المعدلة للباكيند
async function sendAudioRequest(blob) {
    appendMessage("🎤 جاري معالجة وتفسير صوتك...", "user");
    const formData = new FormData();
   
    const fileExtension = mediaRecorder.mimeType.includes('ogg') ? 'ogg' : 'webm';
    formData.append("file", blob, `audio.${fileExtension}`);
    formData.append("dialect", dialectSelect.value);
    formData.append("user_id", currentUser ? currentUser.id : "guest");
   
    try {
        const res = await fetch(`${API_BASE}/chat/audio`, { method: "POST", body: formData });
        const data = await res.json();
        if (data.status === "success") {
            chatMessages.lastChild.innerText = `🎤 ${data.user_speech}`;
            appendMessage(data.response, "ai");
        } else {
            chatMessages.lastChild.innerText = "⚠️ لم أتمكن من سماع الصوت بوضوح، حاول مجدداً.";
        }
    } catch (err) {
        chatMessages.lastChild.innerText = "⚠️ خطأ في الاتصال أثناء رفع الملف الصوتي.";
    }
}

// --- 7️⃣ إدارة رفع وتحليل الصور (Vision) بالتأمين والباقات الجديدة ---
if (imgBtn && fileInput) {
    imgBtn.onclick = () => {
        // حماية مسبقة بالفرونتيند قبل فتح الاستوديو حتى
        if (!currentUser) {
            alert("⚠️ يرجى تسجيل الدخول أولاً لتتمكن من استخدام ميزة تحليل الصور ورؤيتها.");
            document.getElementById("auth-modal").style.display = "flex";
            return;
        }
        fileInput.click();
    };

    fileInput.onchange = () => {
        if (fileInput.files.length > 0) {
            const file = fileInput.files[0];
            previewContainer.innerHTML = `<div class="img-preview-box"><img src="${URL.createObjectURL(file)}"><button onclick="clearImagePreview()">&times;</button></div>`;
        }
    };
}

window.clearImagePreview = function() {
    fileInput.value = "";
    previewContainer.innerHTML = "";
}

async function sendVisionRequest(text) {
    // تأكيد إضافي للتأمين وحماية ميزة الـ Vision المدفوعة
    if (!currentUser) {
        alert("⚠️ يرجى تسجيل الدخول أولاً لتتمكن من استخدام ميزة تحليل الصور.");
        document.getElementById("auth-modal").style.display = "flex";
        return;
    }

    appendMessage(text ? text : "📸 تم رفع صورة للتحليل...", "user");
    const formData = new FormData();
    formData.append("file", fileInput.files[0]);
    formData.append("text", text);
    formData.append("dialect", dialectSelect.value);
    formData.append("user_id", currentUser.id); // تمرير الـ User ID الفعلي للفحص بالسيرفر
   
    clearImagePreview();
   
    try {
        const res = await fetch(`${API_BASE}/chat/vision`, { method: "POST", body: formData });
        const data = await res.json();
        
        // إذا كان الحساب مجاني وطلب الباكيند ترقية الحساب
        if (data.status === "upgrade_required") {
            // إزالة رسالة الانتظار الأخيرة
            if (chatMessages.lastChild) chatMessages.removeChild(chatMessages.lastChild);
            showUpgradeModal(data.response);
            return;
        }

        if (data.status === "success") {
            appendMessage(data.response, "ai");
        } else {
            appendMessage("فشل تحليل الصورة المرفوعة.", "ai");
        }
    } catch (err) {
        appendMessage("خطأ في الاتصال بسيرفر الرؤية الذكي.", "ai");
    }
}

// --- 8️⃣ زر مسح الحوار ---
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

// --- 🚀 9️⃣ وظائف حقن وإدارة واجهة الحسابات ديناميكياً ---
function injectAuthUI() {
    const authHtml = `
        <div id="nav-auth-container" style="position: absolute; top: 15px; left: 15px; z-index: 1000;">
            <button id="auth-nav-btn" style="background: #7c4dff; color: white; border: none; padding: 8px 16px; border-radius: 20px; cursor: pointer; font-family: sans-serif; font-weight: bold; box-shadow: 0 2px 5px rgba(0,0,0,0.2); transition: 0.3s;">تسجيل الدخول</button>
        </div>

        <div id="auth-modal" style="display: none; position: fixed; top:0; left:0; width:100%; height:100%; background: rgba(0,0,0,0.5); justify-content: center; align-items: center; z-index: 2000; font-family: sans-serif;">
            <div style="background: white; padding: 30px; border-radius: 12px; width: 340px; box-shadow: 0 4px 15px rgba(0,0,0,0.2); text-align: center; position: relative;">
                <span id="close-auth" style="position: absolute; top: 10px; right: 15px; font-size: 22px; cursor: pointer; color: #888;">&times;</span>
                <h3 id="auth-title" style="margin-bottom: 20px; color: #333; font-size: 18px;">تسجيل الدخول إلى صوتك AI</h3>
                
                <input type="email" id="auth-email" placeholder="البريد الإلكتروني" style="width: 100%; padding: 10px; margin-bottom: 12px; border: 1px solid #ddd; border-radius: 6px; box-sizing: border-box; text-align: right; outline: none;">
                <input type="password" id="auth-password" placeholder="كلمة المرور" style="width: 100%; padding: 10px; margin-bottom: 20px; border: 1px solid #ddd; border-radius: 6px; box-sizing: border-box; text-align: right; outline: none;">
                
                <button id="auth-submit-btn" style="width: 100%; background: #7c4dff; color: white; border: none; padding: 12px; border-radius: 6px; font-weight: bold; cursor: pointer; margin-bottom: 15px; font-size: 15px;">دخول</button>
                <p id="auth-toggle-text" style="font-size: 13px; color: #666; cursor: pointer; margin: 0;">ليس لديك حساب؟ <span style="color: #7c4dff; font-weight: bold;">سجل الآن</span></p>
            </div>
        </div>

        <div id="upgrade-modal" style="display: none; position: fixed; top:0; left:0; width:100%; height:100%; background: rgba(0,0,0,0.6); justify-content: center; align-items: center; z-index: 2500; font-family: sans-serif;">
            <div style="background: white; padding: 35px; border-radius: 16px; width: 380px; text-align: center; box-shadow: 0 10px 25px rgba(0,0,0,0.3); border-top: 5px solid #ffb300; position: relative;">
                <h2 style="color: #ffb300; margin-top: 0; font-size: 22px;">👑 باقة Pro المطلوبة</h2>
                <p id="upgrade-message" style="color: #444; font-size: 15px; line-height: 1.6; margin-bottom: 25px; text-align: center;"></p>
                <button id="subscribe-btn" style="background: linear-gradient(135deg, #ffb300, #ff6f00); color: white; border: none; padding: 12px 30px; border-radius: 25px; font-weight: bold; font-size: 16px; cursor: pointer; box-shadow: 0 4px 10px rgba(255,179,0,0.4); transition: 0.3s;">اشترك الآن بـ $9.99 فقط</button>
                <p id="close-upgrade" style="margin-top: 15px; font-size: 13px; color: #888; cursor: pointer; text-decoration: underline; margin-bottom: 0;">إغلاق مؤقت</p>
            </div>
        </div>
    `;
    
    const div = document.createElement('div');
    div.innerHTML = authHtml;
    document.body.appendChild(div);
}

function setupAuthEventListeners() {
    let isSignUpMode = false;

    const authModal = document.getElementById("auth-modal");
    const authNavBtn = document.getElementById("auth-nav-btn");
    const closeAuth = document.getElementById("close-auth");
    const authSubmitBtn = document.getElementById("auth-submit-btn");
    const authToggleText = document.getElementById("auth-toggle-text");
    const upgradeModal = document.getElementById("upgrade-modal");
    const closeUpgrade = document.getElementById("close-upgrade");
    const subscribeBtn = document.getElementById("subscribe-btn");

    authNavBtn.addEventListener("click", async () => {
        if (currentUser) {
            // تسجيل الخروج وإعادة تعيين الحالات محلياً
            await supabase.auth.signOut();
            currentUser = null;
            userSubscriptionTier = 'free';
            updateUIForGuestUser();
            alert("تم تسجيل الخروج بنجاح.");
        } else {
            authModal.style.display = "flex";
        }
    });

    closeAuth.addEventListener("click", () => authModal.style.display = "none");
    closeUpgrade.addEventListener("click", () => upgradeModal.style.display = "none");

    // التحويل بين وضع الدخول ووضع إنشاء الحساب الجديد
    authToggleText.addEventListener("click", () => {
        isSignUpMode = !isSignUpMode;
        document.getElementById("auth-title").innerText = isSignUpMode ? "إنشاء حساب جديد" : "تسجيل الدخول إلى صوتك AI";
        authSubmitBtn.innerText = isSignUpMode ? "إنشاء الحساب" : "دخول";
        authToggleText.innerHTML = isSignUpMode ? "لديك حساب بالفعل؟ <span style='color: #7c4dff; font-weight: bold;'>سجل دخول</span>" : "ليس لديك حساب؟ <span style='color: #7c4dff; font-weight: bold;'>سجل الآن</span>";
    });

    // إرسال طلبات التسجيل أو الدخول للـ Supabase
    authSubmitBtn.addEventListener("click", async () => {
        const email = document.getElementById("auth-email").value.trim();
        const password = document.getElementById("auth-password").value;

        if (!email || !password) {
            alert("الرجاء ملء جميع الحقول المطلوبة.");
            return;
        }

        if (isSignUpMode) {
            const { data, error } = await supabase.auth.signUp({ email, password });
            if (error) {
                alert("خطأ في إنشاء الحساب: " + error.message);
            } else {
                alert("تم إنشاء حسابك بنجاح! يرجى مراجعة بريدك لتأكيده وتفعيله.");
                authModal.style.display = "none";
            }
        } else {
            const { data, error } = await supabase.auth.signInWithPassword({ email, password });
            if (error) {
                alert("خطأ في تسجيل الدخول: " + error.message);
            } else {
                authModal.style.display = "none";
                await checkCurrentUser();
                alert("مرحباً بك مجدداً في تطبيق صوتك!");
            }
        }
    });

    // محاكاة الشراء والاشتراك الوهمي للترقية لـ Pro وحفظها بقاعدة البيانات
    subscribeBtn.addEventListener("click", async () => {
        if (!currentUser) return;
        
        const { error } = await supabase
            .table('profiles')
            .update({ subscription_tier: 'pro' })
            .eq('id', currentUser.id);

        if (!error) {
            alert("🎉 تهانينا الشديدة! تم تفعيل باقة 'صوتك AI Pro' لحسابك بنجاح. يمكنك الآن رفع وتحليل عدد لا نهائي من الصور!");
            userSubscriptionTier = 'pro';
            upgradeModal.style.display = "none";
            updateUIForLoggedInUser();
        } else {
            alert("واجهنا مشكلة في تفعيل الاشتراك، يرجى المحاولة لاحقاً.");
        }
    });
}

function updateUIForLoggedInUser() {
    const isPro = userSubscriptionTier === 'pro';
    const label = isPro ? '👑 صوتك Pro' : 'الحساب المجاني';
    const btn = document.getElementById("auth-nav-btn");
    if (btn) {
        btn.innerText = `خروج (${label})`;
        btn.style.background = isPro ? '#ffb300' : '#7c4dff';
    }
}

function updateUIForGuestUser() {
    const btn = document.getElementById("auth-nav-btn");
    if (btn) {
        btn.innerText = "تسجيل الدخول";
        btn.style.background = "#7c4dff";
    }
}

function showUpgradeModal(message) {
    const modal = document.getElementById("upgrade-modal");
    const msgPara = document.getElementById("upgrade-message");
    if (modal && msgPara) {
        msgPara.innerText = message;
        modal.style.display = "flex";
    }
}

