// ==UserScript==
// @name         NopeRi Zoho Outreach Assistant
// @namespace    http://tampermonkey.net/
// @version      1.2
// @description  Automates email composition and outreach tracking directly inside Zoho Mail for NopeRi
// @author       Kaushal Shah & Antigravity
// @match        https://mail.zoho.com/*
// @run-at       document-end
// ==UserScript==

(function() {
    'use strict';

    const API_BASE = 'http://localhost:8000';
    let pendingOutreach = [];
    let currentIndex = 0;
    let isMinimized = false;

    // --- Create modern CSS ---
    const style = document.createElement('style');
    style.innerHTML = `
        #noperi-assistant-toggle {
            position: fixed;
            right: 0;
            top: 15%;
            z-index: 100000;
            background: linear-gradient(135deg, #6366f1, #4f46e5);
            color: white;
            padding: 12px 16px;
            border-radius: 8px 0 0 8px;
            cursor: pointer;
            box-shadow: -2px 4px 20px rgba(0,0,0,0.3);
            font-family: 'Outfit', 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            font-size: 14px;
            font-weight: 600;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            border-left: 2px solid rgba(255,255,255,0.4);
        }
        #noperi-assistant-toggle:hover {
            padding-right: 22px;
            background: linear-gradient(135deg, #4f46e5, #4338ca);
        }
        #noperi-assistant-panel {
            position: fixed;
            right: 20px;
            top: 10%;
            width: 380px;
            max-height: 80vh;
            z-index: 100000;
            background: rgba(18, 18, 22, 0.95);
            backdrop-filter: blur(12px);
            border: 1px solid rgba(255,255,255,0.1);
            border-radius: 16px;
            box-shadow: 0 20px 50px rgba(0,0,0,0.5);
            font-family: 'Outfit', 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            color: #f3f4f6;
            display: flex;
            flex-direction: column;
            overflow: hidden;
            transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
        }
        #noperi-assistant-panel.hidden {
            transform: translateX(420px);
            opacity: 0;
            pointer-events: none;
        }
        .noperi-header {
            background: linear-gradient(135deg, #1e1e24, #121216);
            padding: 16px 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 1px solid rgba(255,255,255,0.08);
        }
        .noperi-header h3 {
            margin: 0;
            font-size: 16px;
            font-weight: 700;
            letter-spacing: 0.5px;
            background: linear-gradient(135deg, #a5b4fc, #818cf8);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        .noperi-header-actions {
            display: flex;
            gap: 10px;
        }
        .noperi-icon-btn {
            background: none;
            border: none;
            color: #9ca3af;
            cursor: pointer;
            padding: 4px;
            font-size: 14px;
            transition: color 0.2s;
            border-radius: 4px;
        }
        .noperi-icon-btn:hover {
            color: #fff;
            background: rgba(255,255,255,0.05);
        }
        .noperi-content {
            padding: 20px;
            overflow-y: auto;
            flex: 1;
            display: flex;
            flex-direction: column;
            gap: 16px;
        }
        .noperi-card {
            background: rgba(255,255,255,0.03);
            border: 1px solid rgba(255,255,255,0.05);
            border-radius: 10px;
            padding: 12px;
        }
        .noperi-meta-title {
            font-size: 11px;
            text-transform: uppercase;
            color: #818cf8;
            font-weight: 600;
            letter-spacing: 1px;
            margin-bottom: 4px;
        }
        .noperi-meta-val {
            font-size: 14px;
            font-weight: 500;
            color: #fff;
            word-break: break-all;
        }
        .noperi-field-box {
            display: flex;
            flex-direction: column;
            gap: 6px;
        }
        .noperi-label-row {
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .noperi-copy-btn {
            background: rgba(99, 102, 241, 0.15);
            border: 1px solid rgba(99, 102, 241, 0.3);
            color: #a5b4fc;
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 11px;
            cursor: pointer;
            font-weight: 600;
            transition: all 0.2s;
        }
        .noperi-copy-btn:hover {
            background: #4f46e5;
            color: white;
        }
        .noperi-text-input {
            width: 100%;
            background: rgba(0,0,0,0.3);
            border: 1px solid rgba(255,255,255,0.08);
            border-radius: 6px;
            color: #fff;
            padding: 8px;
            font-size: 13px;
            font-family: inherit;
            box-sizing: border-box;
        }
        .noperi-textarea {
            width: 100%;
            height: 110px;
            background: rgba(0,0,0,0.3);
            border: 1px solid rgba(255,255,255,0.08);
            border-radius: 6px;
            color: #d1d5db;
            padding: 8px;
            font-size: 12px;
            resize: none;
            font-family: inherit;
            line-height: 1.5;
            box-sizing: border-box;
        }
        .noperi-footer {
            padding: 16px 20px;
            background: rgba(10, 10, 12, 0.8);
            border-top: 1px solid rgba(255,255,255,0.06);
            display: flex;
            flex-direction: column;
            gap: 10px;
        }
        .noperi-primary-btn {
            background: linear-gradient(135deg, #6366f1, #4f46e5);
            border: none;
            color: white;
            padding: 12px;
            border-radius: 8px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s;
            display: flex;
            justify-content: center;
            align-items: center;
            gap: 8px;
            box-shadow: 0 4px 15px rgba(99, 102, 241, 0.3);
            font-family: inherit;
        }
        .noperi-primary-btn:hover {
            background: linear-gradient(135deg, #4f46e5, #4338ca);
            transform: translateY(-1px);
        }
        .noperi-secondary-btn {
            background: rgba(255,255,255,0.05);
            border: 1px solid rgba(255,255,255,0.1);
            color: #d1d5db;
            padding: 10px;
            border-radius: 8px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s;
            font-family: inherit;
        }
        .noperi-secondary-btn:hover {
            background: rgba(255,255,255,0.1);
            color: #fff;
        }
        .noperi-btn-row {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 10px;
        }
        .noperi-badge {
            background: rgba(16, 185, 129, 0.15);
            color: #34d399;
            border: 1px solid rgba(16, 185, 129, 0.3);
            padding: 2px 8px;
            border-radius: 12px;
            font-size: 11px;
            font-weight: 600;
        }
        .noperi-empty {
            text-align: center;
            color: #9ca3af;
            padding: 40px 10px;
            display: flex;
            flex-direction: column;
            gap: 10px;
            font-size: 14px;
        }
        .noperi-success-toast {
            position: fixed;
            bottom: 20px;
            left: 50%;
            transform: translateX(-50%);
            background: #10b981;
            color: white;
            padding: 10px 20px;
            border-radius: 20px;
            font-weight: 600;
            box-shadow: 0 4px 15px rgba(16, 185, 129, 0.3);
            z-index: 100001;
            opacity: 0;
            transition: opacity 0.3s;
            pointer-events: none;
            font-family: inherit;
        }
    `;
    document.head.appendChild(style);

    // --- Toast container ---
    const toast = document.createElement('div');
    toast.className = 'noperi-success-toast';
    toast.innerText = 'Copied to clipboard!';
    document.body.appendChild(toast);

    function showToast(message) {
        toast.innerText = message;
        toast.style.opacity = '1';
        setTimeout(() => {
            toast.style.opacity = '0';
        }, 2000);
    }

    // --- HTML UI Structure ---
    const toggleBtn = document.createElement('div');
    toggleBtn.id = 'noperi-assistant-toggle';
    toggleBtn.innerHTML = '✉️ NopeRi';
    document.body.appendChild(toggleBtn);

    const panel = document.createElement('div');
    panel.id = 'noperi-assistant-panel';
    panel.className = 'hidden';
    document.body.appendChild(panel);

    // Toggle event
    toggleBtn.addEventListener('click', () => {
        panel.classList.toggle('hidden');
        if (!panel.classList.contains('hidden')) {
            fetchPendingDrafts();
        }
    });

    // --- Hash Navigation Listener ---
    function parseHashAndFocus() {
        const hash = window.location.hash || '';
        const match = hash.match(/noperi-company-id=([^&]+)/);
        if (match && match[1]) {
            const targetId = match[1];
            const idx = pendingOutreach.findIndex(d => d.company_id === targetId);
            if (idx !== -1) {
                currentIndex = idx;
                return true;
            }
        }
        return false;
    }

    window.addEventListener('hashchange', () => {
        if (pendingOutreach.length > 0) {
            const focused = parseHashAndFocus();
            if (focused) {
                renderWidget();
                panel.classList.remove('hidden');
                showToast('Switched to selected draft!');
            }
        }
    });

    // --- Main Widget Render Function ---
    function renderWidget() {
        if (pendingOutreach.length === 0) {
            panel.innerHTML = `
                <div class="noperi-header">
                    <h3>NopeRi Assistant</h3>
                    <div class="noperi-header-actions">
                        <button class="noperi-icon-btn" id="noperi-btn-refresh">🔄</button>
                        <button class="noperi-icon-btn" id="noperi-btn-close">✖</button>
                    </div>
                </div>
                <div class="noperi-content">
                    <div class="noperi-empty">
                        <span>🎉 All caught up!</span>
                        <span style="font-size: 12px;">No pending email drafts found. Start a new local outreach search on the dashboard.</span>
                    </div>
                </div>
            `;
            attachEmptyEvents();
            return;
        }

        const draft = pendingOutreach[currentIndex];
        const emails = draft.extracted_emails || [];
        const recipient = emails.length > 0 ? emails[0] : 'N/A';

        panel.innerHTML = `
            <div class="noperi-header">
                <h3>NopeRi Assistant (${currentIndex + 1}/${pendingOutreach.length})</h3>
                <div class="noperi-header-actions">
                    <button class="noperi-icon-btn" id="noperi-btn-refresh" title="Refresh Drafts">🔄</button>
                    <button class="noperi-icon-btn" id="noperi-btn-close">✖</button>
                </div>
            </div>
            <div class="noperi-content">
                <div class="noperi-card">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <div>
                            <div class="noperi-meta-title">Company Name</div>
                            <div class="noperi-meta-val" style="font-size: 15px; font-weight: 700; color: #a5b4fc;">${draft.company_name}</div>
                        </div>
                        ${draft.website ? `<a href="${draft.website.startsWith('http') ? draft.website : 'https://' + draft.website}" target="_blank" style="font-size: 12px; color: #818cf8; text-decoration: none; font-weight: 600;">🌐 Website</a>` : ''}
                    </div>
                </div>

                <div class="noperi-field-box">
                    <div class="noperi-label-row">
                        <div class="noperi-meta-title">To (HR Email)</div>
                        <button class="noperi-copy-btn" id="noperi-copy-to">Copy</button>
                    </div>
                    <input type="text" class="noperi-text-input" value="${recipient}" readonly>
                </div>

                <div class="noperi-field-box">
                    <div class="noperi-label-row">
                        <div class="noperi-meta-title">Subject Line</div>
                        <button class="noperi-copy-btn" id="noperi-copy-su">Copy</button>
                    </div>
                    <input type="text" class="noperi-text-input" value="${draft.email_subject}" readonly>
                </div>

                <div class="noperi-field-box">
                    <div class="noperi-label-row">
                        <div class="noperi-meta-title">Email Body</div>
                        <button class="noperi-copy-btn" id="noperi-copy-bo">Copy</button>
                    </div>
                    <textarea class="noperi-textarea" readonly>${draft.email_body}</textarea>
                </div>
            </div>
            <div class="noperi-footer">
                <button class="noperi-primary-btn" id="noperi-btn-autofill">
                    ⚡ Auto-Fill Composer
                </button>
                <div class="noperi-btn-row">
                    <button class="noperi-secondary-btn" style="border-color: rgba(16, 185, 129, 0.3); color: #34d399;" id="noperi-btn-mark-sent">
                        Mark Sent & Next
                    </button>
                    <button class="noperi-secondary-btn" id="noperi-btn-skip">
                        Skip
                    </button>
                </div>
            </div>
        `;

        attachActiveEvents(draft, recipient);
    }

    // --- API Calls ---
    function fetchPendingDrafts() {
        fetch(`${API_BASE}/api/outreach/pending`)
            .then(res => res.json())
            .then(data => {
                pendingOutreach = data;
                
                // Parse company ID from hash/URL if present to auto-focus
                parseHashAndFocus();
                
                if (currentIndex >= pendingOutreach.length) {
                    currentIndex = 0;
                }
                renderWidget();
            })
            .catch(err => {
                console.error('Error fetching pending drafts:', err);
                panel.innerHTML = `
                    <div class="noperi-header">
                        <h3>Connection Error</h3>
                        <button class="noperi-icon-btn" id="noperi-btn-close">✖</button>
                    </div>
                    <div class="noperi-content">
                        <div class="noperi-empty" style="color: #ef4444;">
                            <span>⚠️ NopeRi Backend Offline</span>
                            <span style="font-size: 12px; color: #9ca3af;">Please ensure your FastAPI backend service is running locally at http://localhost:8000.</span>
                        </div>
                    </div>
                `;
                document.getElementById('noperi-btn-close').onclick = () => panel.classList.add('hidden');
            });
    }

    // Initialize checking on startup if panel opened
    if (window.location.hash.includes('noperi-company-id')) {
        panel.classList.remove('hidden');
        fetchPendingDrafts();
    }

    function markDraftAsSent(companyId, emailId) {
        // 1. Mark email as sent
        const p1 = fetch(`${API_BASE}/api/emails/${emailId}/status`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ sent_status: 'sent' })
        });

        // 2. Mark company as sent_manually
        const p2 = fetch(`${API_BASE}/api/companies/${companyId}/status`, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ status: 'sent_manually' })
        });

        Promise.all([p1, p2])
            .then(() => {
                showToast('🚀 Status updated back to local dashboard!');
                fetchPendingDrafts();
            })
            .catch(err => {
                console.error('Error updating status:', err);
                showToast('❌ Failed to update status.');
            });
    }

    // --- Event Bindings ---
    function attachEmptyEvents() {
        document.getElementById('noperi-btn-close').onclick = () => panel.classList.add('hidden');
        document.getElementById('noperi-btn-refresh').onclick = fetchPendingDrafts;
    }

    function attachActiveEvents(draft, recipient) {
        // Top buttons
        document.getElementById('noperi-btn-close').onclick = () => panel.classList.add('hidden');
        document.getElementById('noperi-btn-refresh').onclick = fetchPendingDrafts;

        // Clipboard Copy buttons
        document.getElementById('noperi-copy-to').onclick = () => {
            navigator.clipboard.writeText(recipient).then(() => showToast('Copied recipient email!'));
        };
        document.getElementById('noperi-copy-su').onclick = () => {
            navigator.clipboard.writeText(draft.email_subject).then(() => showToast('Copied email subject!'));
        };
        document.getElementById('noperi-copy-bo').onclick = () => {
            navigator.clipboard.writeText(draft.email_body).then(() => showToast('Copied email body!'));
        };

        // Autofill logic
        document.getElementById('noperi-btn-autofill').onclick = () => {
            // Check if composer is open. If not, try triggering compose
            let composeBtn = document.querySelector('[data-test-id="compose-mail"]') || 
                             document.querySelector('.zmComposeBtn') || 
                             document.querySelector('.zm-compose-btn') ||
                             document.querySelector('[id*="compose"]') ||
                             Array.from(document.querySelectorAll('button, div')).find(el => el.textContent.trim().toLowerCase() === 'compose');
            
            if (composeBtn) {
                composeBtn.click();
                showToast('Opening Zoho composer...');
                // Wait for the Zoho composer UI tab to initialize
                setTimeout(() => {
                    executeAutoFill(recipient, draft.email_subject, draft.email_body);
                }, 750);
            } else {
                // If composer already open, execute directly
                executeAutoFill(recipient, draft.email_subject, draft.email_body);
            }
        };

        // Footer buttons
        document.getElementById('noperi-btn-mark-sent').onclick = () => {
            markDraftAsSent(draft.company_id, draft.email_id);
        };

        document.getElementById('noperi-btn-skip').onclick = () => {
            if (currentIndex < pendingOutreach.length - 1) {
                currentIndex++;
                renderWidget();
                showToast('Skipped to next draft.');
            } else {
                currentIndex = 0;
                renderWidget();
                showToast('Returned to first draft.');
            }
        };
    }

    // --- Auto Fill Execution Block ---
    function executeAutoFill(toEmail, subject, bodyText) {
        let filledSuccess = false;

        // 1. Fill To/Recipient Field
        let toInput = document.querySelector('input[placeholder="To"]') || 
                      document.querySelector('.zmComposeTo input') || 
                      document.querySelector('.to-fieldContent contenteditable') ||
                      document.querySelector('.zmComposeTo .zm-search-input') ||
                      document.querySelector('input[role="combobox"][placeholder*="To"]') ||
                      document.querySelector('[data-test-id="compose-to"] input') ||
                      document.querySelector('.zm-search-input');
                      
        if (toInput) {
            if (toInput.tagName === 'INPUT' || toInput.tagName === 'TEXTAREA') {
                toInput.focus();
                toInput.value = toEmail;
                toInput.dispatchEvent(new Event('input', { bubbles: true }));
                toInput.dispatchEvent(new Event('change', { bubbles: true }));
            } else {
                toInput.focus();
                toInput.innerText = toEmail;
                toInput.dispatchEvent(new Event('input', { bubbles: true }));
            }
            filledSuccess = true;
        }

        // 2. Fill Subject Field
        let subjectInput = document.querySelector('input[placeholder="Subject"]') || 
                           document.querySelector('.zmComposeSubject') || 
                           document.querySelector('input[name="subject"]') ||
                           document.querySelector('[data-test-id="compose-subject"]') ||
                           document.querySelector('input[class*="subject"]');
                           
        if (subjectInput) {
            subjectInput.focus();
            subjectInput.value = subject;
            subjectInput.dispatchEvent(new Event('input', { bubbles: true }));
            subjectInput.dispatchEvent(new Event('change', { bubbles: true }));
            filledSuccess = true;
        }

        // 3. Fill Body rich-text contenteditable Editor
        let bodyEditor = document.querySelector('div[contenteditable="true"].zm-editor-body') || 
                         document.querySelector('.zmEditor div[contenteditable="true"]') ||
                         document.querySelector('.zmComposeBody div[contenteditable="true"]') ||
                         document.querySelector('.zm-editor-body') ||
                         document.querySelector('div[contenteditable="true"]');
                         
        if (bodyEditor) {
            bodyEditor.focus();
            // Map plain text formatting to rich HTML newlines
            let formattedBody = bodyText.replace(/\n/g, '<br>');
            bodyEditor.innerHTML = formattedBody;
            bodyEditor.dispatchEvent(new Event('input', { bubbles: true }));
            filledSuccess = true;
        }

        if (filledSuccess) {
            showToast('⚡ Composer filled! Please drag & attach your resume.');
        } else {
            showToast('⚠️ Could not locate composer fields. Use copy buttons as fallback!');
        }
    }

})();
