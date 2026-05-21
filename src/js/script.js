import '../css/style.css';
import { initAuth, getActiveApiKey } from './auth';

document.addEventListener('DOMContentLoaded', () => {
    initAuth();

    // Nav logic
    const navItems = document.querySelectorAll('.nav-item');
    const sections = document.querySelectorAll('.app-section');
    const dynamicPageTitle = document.getElementById('dynamic-page-title');

    // Mobile responsive
    const mobileMenuBtn = document.getElementById('mobile-menu-btn');
    const sidebar = document.querySelector('.sidebar');
    const mobileOverlay = document.getElementById('mobile-overlay');

    // Sidebar Navigation logic
    navItems.forEach(item => {
        item.addEventListener('click', () => {
            // Update active nav
            navItems.forEach(nav => nav.classList.remove('active'));
            item.classList.add('active');

            // Update title
            const targetName = item.querySelector('span').innerText;
            if (dynamicPageTitle) dynamicPageTitle.innerText = targetName;

            // Show target section
            const targetId = item.getAttribute('data-target');
            sections.forEach(sec => {
                if (sec.id === targetId) {
                    sec.classList.add('active');
                } else {
                    sec.classList.remove('active');
                }
            });

            // Close mobile menu if open
            if (sidebar.classList.contains('open')) {
                sidebar.classList.remove('open');
                mobileOverlay.classList.remove('active');
            }
        });
    });

    // Mobile Menu Toggle
    if (mobileMenuBtn && sidebar && mobileOverlay) {
        mobileMenuBtn.addEventListener('click', () => {
            sidebar.classList.add('open');
            mobileOverlay.classList.add('active');
        });

        mobileOverlay.addEventListener('click', () => {
            sidebar.classList.remove('open');
            mobileOverlay.classList.remove('active');
        });
    }

    // Secret Message Character Counter
    const messageInput = document.getElementById('secret-message');
    const charCount = document.getElementById('char-count');

    if (messageInput && charCount) {
        messageInput.addEventListener('input', (e) => {
            const currentLen = e.target.value.length;
            const maxLen = e.target.getAttribute('maxlength') || 2000;
            charCount.textContent = `${currentLen} / ${maxLen} chars`;
        });
    }

    // Drag and Drop Logic
    function setupDropzone(dropzoneId, inputId) {
        const dropzone = document.getElementById(dropzoneId);
        const fileInput = document.getElementById(inputId);
        const selectBtn = dropzone ? dropzone.querySelector('button') : null;

        if (!dropzone || !fileInput) return;

        // Click to upload
        if (selectBtn) {
            selectBtn.addEventListener('click', (e) => {
                e.preventDefault();
                fileInput.click();
            });
        }

        dropzone.addEventListener('click', (e) => {
            if (e.target !== selectBtn) fileInput.click();
        });

        // Drag events
        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            dropzone.addEventListener(eventName, preventDefaults, false);
        });

        function preventDefaults(e) {
            e.preventDefault();
            e.stopPropagation();
        }

        ['dragenter', 'dragover'].forEach(eventName => {
            dropzone.addEventListener(eventName, () => {
                dropzone.classList.add('dragover');
            });
        });

        ['dragleave', 'drop'].forEach(eventName => {
            dropzone.addEventListener(eventName, () => {
                dropzone.classList.remove('dragover');
            });
        });

        dropzone.addEventListener('drop', (e) => {
            let df = e.dataTransfer;
            let files = df.files;
            handleFiles(files, dropzone, fileInput);
        });

        fileInput.addEventListener('change', function () {
            handleFiles(this.files, dropzone, fileInput);
        });
    }

    function handleFiles(files, dropzone, fileInput) {
        if (files.length > 0) {
            const fileName = files[0].name;
            const titleEl = dropzone.querySelector('.drop-title');
            const subTitleEl = dropzone.querySelector('.drop-subtitle');

            if (titleEl) titleEl.textContent = "File Ready";
            if (subTitleEl) subTitleEl.textContent = fileName;

            dropzone.classList.add('has-file');
        }
    }

    setupDropzone('encode-dropzone', 'encode-file-input');
    setupDropzone('decode-dropzone', 'decode-file-input');

    // API endpoints logic
    const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:5000';
    const encodeBtn = document.querySelector('#encode .btn-large');
    const decodeBtn = document.querySelector('#decode .btn-large');

    if (encodeBtn) {
        encodeBtn.addEventListener('click', async () => {
            const fileInput = document.getElementById('encode-file-input');
            const messageInput = document.getElementById('secret-message');
            const keyInput = document.getElementById('encode-key');
            const placeholder = document.querySelector('#encode .output-placeholder');

            if (!fileInput.files.length || !messageInput.value || !keyInput.value) {
                alert("Please provide a carrier file, a secret message, and an AES passphrase.");
                return;
            }

            placeholder.classList.add('processing');
            placeholder.innerHTML = `<i class="ph ph-spinner"></i><p>Injecting AES payload into carrier...</p>`;

            const formData = new FormData();
            formData.append('file', fileInput.files[0]);
            formData.append('message', messageInput.value);
            formData.append('key', keyInput.value);

            try {
                const apiKey = getActiveApiKey();
                const headers = {};
                if (apiKey) {
                    headers['X-API-Key'] = apiKey;
                }

                const response = await fetch(`${API_BASE_URL}/encode`, {
                    method: 'POST',
                    headers: headers,
                    body: formData
                });

                if (!response.ok) {
                    const errorData = await response.json();
                    throw new Error(errorData.message || "Encoding failed.");
                }

                // Extract filename from Content-Disposition header if possible, else default
                let filename = "bithide_stego." + fileInput.files[0].name.split('.').pop();
                const disposition = response.headers.get('Content-Disposition');
                if (disposition && disposition.indexOf('filename=') !== -1) {
                    filename = disposition.split('filename=')[1].replace(/["']/g, "");
                }

                const blob = await response.blob();
                const downloadUrl = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.style.display = 'none';
                a.href = downloadUrl;
                a.download = filename;
                document.body.appendChild(a);
                a.click();
                window.URL.revokeObjectURL(downloadUrl);
                document.body.removeChild(a);

                placeholder.classList.remove('processing');
                placeholder.innerHTML = `<i class="ph-fill ph-check-circle" style="color:var(--badge-green-text)"></i><p>Encode Success! Downloaded stego artifact.</p>`;
            } catch (error) {
                placeholder.classList.remove('processing');
                placeholder.innerHTML = `<i class="ph-fill ph-warning-circle" style="color:#ef4444"></i><p>Error: ${error.message}</p>`;
            }
        });
    }

    if (decodeBtn) {
        decodeBtn.addEventListener('click', async () => {
            const fileInput = document.getElementById('decode-file-input');
            const keyInput = document.getElementById('decode-key');
            const placeholder = document.querySelector('#decode .output-placeholder');

            if (!fileInput.files.length || !keyInput.value) {
                alert("Please provide a stego file and the AES passphrase.");
                return;
            }

            placeholder.classList.add('processing');
            placeholder.innerHTML = `<i class="ph ph-spinner"></i><p>Analyzing fragments & decrypting stream...</p>`;

            const formData = new FormData();
            formData.append('file', fileInput.files[0]);
            formData.append('key', keyInput.value);

            try {
                const apiKey = getActiveApiKey();
                const headers = {};
                if (apiKey) {
                    headers['X-API-Key'] = apiKey;
                }

                const response = await fetch(`${API_BASE_URL}/decode`, {
                    method: 'POST',
                    headers: headers,
                    body: formData
                });

                const data = await response.json();

                if (!response.ok) {
                    throw new Error(data.message || "Decoding failed.");
                }

                placeholder.classList.remove('processing');
                placeholder.innerHTML = `<i class="ph-fill ph-lock-open" style="color:var(--badge-green-text)"></i>
                                          <div style="text-align:left; width:100%; max-height:150px; overflow-y:auto; background:rgba(0,0,0,0.2); padding:16px; border-radius:12px; margin-top:12px;">
                                            <strong style="color:var(--text-main); font-family:monospace; white-space:pre-wrap;">${data.message.replace(/</g, "&lt;").replace(/>/g, "&gt;")}</strong>
                                          </div>`;
            } catch (error) {
                placeholder.classList.remove('processing');
                placeholder.innerHTML = `<i class="ph-fill ph-warning-circle" style="color:#ef4444"></i><p>Error: ${error.message}</p>`;
            }
        });
    }
});
