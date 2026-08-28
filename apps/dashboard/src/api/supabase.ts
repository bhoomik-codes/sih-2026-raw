/**
 * Supabase client configuration for IBVAP Dashboard
 */

export const SUPABASE_URL = (import.meta as any).env?.VITE_SUPABASE_URL || 'https://***.supabase.co';
export const SUPABASE_ANON_KEY = (import.meta as any).env?.VITE_SUPABASE_ANON_KEY || '';

export const isSupabaseConfigured = Boolean(SUPABASE_URL && SUPABASE_ANON_KEY);
