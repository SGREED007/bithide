# BitHide

🔒 **BitHide** is an advanced, production-ready web application that provides dual-layer data concealment by combining **AES-256 Symmetric Encryption** with **Least Significant Bit (LSB) Steganography**.

Hide your most sensitive text and data payloads invisibly within seemingly normal images (PNG, JPEG), audio files (WAV), and documents (PDF). Built with a modern, responsive Vite frontend and a secure, modular Flask backend.

---

### 🔥 Key Features
- **Dual-Layer Security:** Text is first encrypted with AES-256 (via PBKDF2 key derivation), then injected deep into the binary carrier file using LSB manipulation or EOF sentinel appending.
- **Multi-Format Support:** Easily embed secrets into **Images (PNG, JPG)**, **Audio (WAV)**, and **Documents (PDF)**.
- **Flawless UI/UX:** A beautiful, responsive, and professional dashboard built with custom HTML/CSS and Vite, mimicking enterprise-level SaaS tools.
- **Clean Architecture:** Modular backend built with Flask, completely separating the API controllers, cryptography layers, and data-processing engines.
- **Robust Error Handling:** Comprehensive data validation, carrier file capacity checking, rate-limiting, and sanitized exception reporting.

---

### 🚀 Tech Stack
- **Frontend**: Lightweight, high-performance **Vanilla JS & CSS** powered by **Vite**
- **Backend**: **Python 3.10+, Flask** (with Flask-CORS & Flask-Limiter for API security)
- **Cryptography**: `cryptography` library (AES-256 Fernet + PBKDF2HMAC)
- **Media Processing**: `Pillow` (Images), `wave` (Audio), and custom byte parsing (PDFs).

---

### ⚙️ Quick Start

**Backend Setup:**
```bash
cd backend
python -m venv venv
source venv/Scripts/activate # Windows
pip install -r requirements.txt
cp .env.example .env # Ensure you set a SECRET_KEY
python app.py
# Backend runs on http://localhost:5000
```

**Frontend Setup:**
```bash
# In the root project folder
npm install
npm run dev
# Frontend runs on http://localhost:5173
```
