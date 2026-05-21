import { createClient } from '@supabase/supabase-js'

// روابط مشروعك الفعلي "my-voice-ai"
const supabaseUrl = 'https://uciymzougmatinbqxdpq.supabase.co'
const supabaseAnonKey = 'sb_publishable_kpi3MI3p6mej5J-aFEVq0g_5_1ic5m7'

export const supabase = createClient(supabaseUrl, supabaseAnonKey)

