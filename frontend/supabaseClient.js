// استيراد النسخة المتوافقة مع المتصفحات مباشرة بدون برامج تجميع (Bundlers)
import { createClient } from 'https://esm.sh/@supabase/supabase-js@2';

// ضع هنا رابط مشروعك (Project URL) ومفتاح الـ Anon Key الخاص بك من حساب Supabase
const supabaseUrl = 'https://uciymzougmatingbqxdpq.supabase.co'; // تم جلبه بدقة من صورتك
const supabaseKey = 'YOUR_SUPABASE_ANON_KEY'; // استبدله بمفتاح الـ Anon Key الخاص بك

export const supabase = createClient(supabaseUrl, supabaseKey);

