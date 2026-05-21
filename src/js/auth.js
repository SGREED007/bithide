import { createClient } from '@supabase/supabase-js';

// ─── Supabase Configuration ─────────────────────────────────────────────────
const SUPABASE_URL = 'https://iobfxpwtcgyiypolcwys.supabase.co';
// Replace this with your standard public "Anon Key" or "Publishable Key"
const SUPABASE_ANON_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImlvYmZ4cHd0Y2d5aXlwb2xjd3lzIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzIxMjc0MDUsImV4cCI6MjA4NzcwMzQwNX0.ezGhcTnU-yBLBTQ0MZKVcbMfhDY4RJOKlzK7MdQtJWo';

const supabase = createClient(SUPABASE_URL, SUPABASE_ANON_KEY);
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:5000';

// ─── DOM Elements ───────────────────────────────────────────────────────────
const authModal = document.getElementById('auth-modal');
const authForm = document.getElementById('auth-form');
const authEmail = document.getElementById('auth-email');
const authPassword = document.getElementById('auth-password');
const authError = document.getElementById('auth-error');
const authSubmitBtn = document.getElementById('auth-submit-btn');
const authToggleLink = document.getElementById('auth-toggle-link');
const authToggleText = document.getElementById('auth-toggle-text');
const btnLogout = document.getElementById('btn-logout');
const userDisplay = document.getElementById('user-display');
const authCloseBtn = document.getElementById('auth-close-btn');

// Dashboard Elements
const apiKeyText = document.getElementById('api-key-text');
const btnCopyKey = document.getElementById('btn-copy-key');
const btnGenerateKey = document.getElementById('btn-generate-key');

let isLoginMode = true;
let currentSession = null;

// ─── Auth Logic ─────────────────────────────────────────────────────────────

export async function initAuth() {
    // Check active session on load
    const { data: { session } } = await supabase.auth.getSession();
    handleSessionState(session);

    // Listen to changes
    supabase.auth.onAuthStateChange((event, session) => {
        handleSessionState(session);
    });

    // Toggle Login/SignUp
    if (authToggleLink) {
        authToggleLink.addEventListener('click', () => {
            isLoginMode = !isLoginMode;
            authError.style.display = 'none';
            if (isLoginMode) {
                document.getElementById('auth-title').innerText = "Sign In to BitHide";
                authSubmitBtn.innerText = "Authenticate Session";
                authToggleText.innerText = "Need to establish clearance?";
                authToggleLink.innerText = "Sign Up";
            } else {
                document.getElementById('auth-title').innerText = "Create Clearance";
                authSubmitBtn.innerText = "Register Identity";
                authToggleText.innerText = "Already possess clearance?";
                authToggleLink.innerText = "Sign In";
            }
        });
    }

    // Submit Auth Form
    if (authForm) {
        authForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            authError.style.display = 'none';
            authSubmitBtn.disabled = true;
            authSubmitBtn.innerText = "Processing...";

            const email = authEmail.value.trim();
            const password = authPassword.value;

            try {
                if (isLoginMode) {
                    const { error } = await supabase.auth.signInWithPassword({ email, password });
                    if (error) throw error;
                } else {
                    const { error } = await supabase.auth.signUp({ email, password });
                    if (error) throw error;
                    alert("Clearance granted! Welcome to BitHide.");
                    isLoginMode = true; // Switch back to login
                    authSubmitBtn.innerText = "Authenticate Session";
                    authSubmitBtn.disabled = false;
                    return;
                }
            } catch (error) {
                authError.innerText = error.message;
                authError.style.display = 'block';
                authSubmitBtn.disabled = false;
                authSubmitBtn.innerText = isLoginMode ? "Authenticate Session" : "Register Identity";
            }
        });
    }

    // Logout / Open Auth
    if (btnLogout) {
        btnLogout.addEventListener('click', async () => {
            if (currentSession) {
                await supabase.auth.signOut();
                localStorage.removeItem('bithide_live_api_key');
                alert("Successfully signed out. Secure session terminated.");
            } else {
                openAuthModal();
            }
        });
    }

    if (authCloseBtn) {
        authCloseBtn.addEventListener('click', () => {
            closeAuthModal();
        });
    }

    // Generate API Key
    if (btnGenerateKey) {
        btnGenerateKey.addEventListener('click', async () => {
            if (!currentSession) {
                openAuthModal();
                return;
            }
            if (!confirm("Warning: Generating a new key will instantly revoke your old active key. Continue?")) return;

            btnGenerateKey.disabled = true;
            btnGenerateKey.innerText = "Generating...";

            try {
                const res = await fetch(`${API_BASE_URL}/auth/keys/generate`, {
                    method: 'POST',
                    headers: { 'Authorization': `Bearer ${currentSession.access_token}` }
                });
                const data = await res.json();

                if (!res.ok) throw new Error(data.message || "Failed to generate key");

                // Store locally so encode/decode work immediately
                localStorage.setItem('bithide_live_api_key', data.api_key);

                // Show to user ONCE
                apiKeyText.innerText = data.api_key;
                apiKeyText.style.color = "var(--text-main)";
                btnCopyKey.style.display = "block";

                alert("CRITICAL: Save your new API key now. You will NEVER be able to see it again once you refresh.");

            } catch (e) {
                alert("Error: " + e.message);
            } finally {
                btnGenerateKey.disabled = false;
                btnGenerateKey.innerHTML = '<i class="ph ph-arrows-clockwise"></i> Generate New Key';
            }
        });
    }

    // Copy Key
    if (btnCopyKey) {
        btnCopyKey.addEventListener('click', () => {
            navigator.clipboard.writeText(apiKeyText.innerText);
            const icon = btnCopyKey.querySelector('i');
            icon.className = 'ph-fill ph-check';
            icon.style.color = "var(--badge-green-text)";
            setTimeout(() => {
                icon.className = 'ph ph-copy';
                icon.style.color = "inherit";
            }, 2000);
        });
    }
}

async function handleSessionState(session) {
    currentSession = session;
    if (session) {
        // User logged in
        authModal.classList.remove('active');
        if (userDisplay) {
            userDisplay.innerText = session.user.email.split('@')[0];
        }
        await fetchCurrentKeyStatus(session.access_token);
        btnLogout.title = "Sign Out";
        btnLogout.innerHTML = `<span id="user-display">${session.user.email.split('@')[0]}</span><i class="ph-fill ph-sign-out"></i>`;
    } else {
        // Logged out
        authModal.classList.remove('active'); // Don't force overlay!
        if (userDisplay) {
            userDisplay.innerText = "Developer Session";
        }
        btnLogout.title = "Sign In for Developer API";
        btnLogout.innerHTML = `<span id="user-display">Sign In / Register</span><i class="ph-fill ph-sign-in"></i>`;
        if (apiKeyText) {
            apiKeyText.innerText = "Authentication required. Sign in or register to generate an API key.";
            apiKeyText.style.color = "var(--text-muted)";
            if (btnCopyKey) btnCopyKey.style.display = "none";
        }
    }
}

async function fetchCurrentKeyStatus(token) {
    try {
        const res = await fetch(`${API_BASE_URL}/auth/keys/current`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        const data = await res.json();

        if (data.has_key) {
            const localKey = localStorage.getItem('bithide_live_api_key');
            if (localKey) {
                apiKeyText.innerText = "Key is active and loaded in secure memory.";
            } else {
                apiKeyText.innerText = data.masked_key + " (Local memory cleared. Please generate a new key)";
                apiKeyText.style.color = "#ef4444";
            }
        } else {
            apiKeyText.innerText = "No active key found. Generate one below.";
            apiKeyText.style.color = "#ef4444";
        }
    } catch (e) {
        console.error("Failed to fetch key status", e);
        apiKeyText.innerText = "Error loading key status.";
    }
}

export function getActiveApiKey() {
    return localStorage.getItem('bithide_live_api_key');
}

export function openAuthModal() {
    authModal.classList.add('active');
}

export function closeAuthModal() {
    authModal.classList.remove('active');
}
