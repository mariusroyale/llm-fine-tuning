/**
 * Codebase RAG Chat Client
 * Handles WebSocket communication and UI updates
 */

class ChatClient {
    constructor() {
        this.ws = null;
        this.isConnected = false;
        this.isProcessing = false;
        this.questionsCount = 0;
        this.sourcesCount = 0;
        this.currentSources = [];

        // DOM Elements
        this.chatMessages = document.getElementById('chat-messages');
        this.chatInput = document.getElementById('chat-input');
        this.sendBtn = document.getElementById('send-btn');
        this.clearChatBtn = document.getElementById('clear-chat');
        this.sourcesPanel = document.getElementById('sources-panel');
        this.sourcesContent = document.getElementById('sources-content');
        this.closeSourcesBtn = document.getElementById('close-sources');

        // Settings
        this.languageFilter = document.getElementById('language-filter');
        this.hybridSearch = document.getElementById('hybrid-search');
        this.showSources = document.getElementById('show-sources');

        // Stats
        this.questionsCountEl = document.getElementById('questions-count');
        this.sourcesCountEl = document.getElementById('sources-count');

        // Templates
        this.userMessageTemplate = document.getElementById('user-message-template');
        this.assistantMessageTemplate = document.getElementById('assistant-message-template');
        this.thinkingTemplate = document.getElementById('thinking-template');

        // Configure marked.js
        this.configureMarked();

        // Initialize
        this.init();
    }

    configureMarked() {
        // Custom renderer for code blocks with copy button
        const renderer = new marked.Renderer();

        renderer.code = (code, language) => {
            const validLang = language && hljs.getLanguage(language) ? language : 'plaintext';
            const highlighted = hljs.highlight(code, { language: validLang }).value;
            const langLabel = language || 'code';

            return `
                <div class="code-block">
                    <div class="code-block-header">
                        <span class="code-block-lang">${langLabel}</span>
                        <button class="copy-code-btn" onclick="chatClient.copyCode(this)">
                            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
                                <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
                            </svg>
                            Copy
                        </button>
                    </div>
                    <pre><code class="hljs language-${validLang}">${highlighted}</code></pre>
                </div>
            `;
        };

        marked.setOptions({
            renderer: renderer,
            gfm: true,
            breaks: true,
            highlight: (code, lang) => {
                if (lang && hljs.getLanguage(lang)) {
                    return hljs.highlight(code, { language: lang }).value;
                }
                return code;
            }
        });
    }

    init() {
        this.connect();
        this.setupEventListeners();
        this.autoResizeTextarea();
    }

    connect() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws/chat`;

        this.ws = new WebSocket(wsUrl);

        this.ws.onopen = () => {
            console.log('WebSocket connected');
            this.isConnected = true;
            this.updateSendButton();
        };

        this.ws.onclose = () => {
            console.log('WebSocket disconnected');
            this.isConnected = false;
            this.updateSendButton();

            // Attempt to reconnect after 3 seconds
            setTimeout(() => this.connect(), 3000);
        };

        this.ws.onerror = (error) => {
            console.error('WebSocket error:', error);
        };

        this.ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            this.handleMessage(data);
        };
    }

    setupEventListeners() {
        // Send button
        this.sendBtn.addEventListener('click', () => this.sendMessage());

        // Enter to send, Shift+Enter for new line
        this.chatInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendMessage();
            }
        });

        // Clear chat
        this.clearChatBtn.addEventListener('click', () => this.clearChat());

        // Close sources panel
        this.closeSourcesBtn.addEventListener('click', () => this.closeSourcesPanel());

        // Auto-resize textarea
        this.chatInput.addEventListener('input', () => this.autoResizeTextarea());
    }

    autoResizeTextarea() {
        this.chatInput.style.height = 'auto';
        this.chatInput.style.height = Math.min(this.chatInput.scrollHeight, 200) + 'px';
    }

    updateSendButton() {
        this.sendBtn.disabled = !this.isConnected || this.isProcessing || !this.chatInput.value.trim();
    }

    sendMessage() {
        const question = this.chatInput.value.trim();
        if (!question || !this.isConnected || this.isProcessing) return;

        // Add user message to chat
        this.addUserMessage(question);

        // Clear input
        this.chatInput.value = '';
        this.autoResizeTextarea();

        // Show thinking indicator
        this.showThinking();

        // Send to server
        this.isProcessing = true;
        this.updateSendButton();

        this.ws.send(JSON.stringify({
            question: question,
            language: this.languageFilter.value || null,
            use_hybrid_search: this.hybridSearch.checked,
        }));

        // Update stats
        this.questionsCount++;
        this.questionsCountEl.textContent = this.questionsCount;
    }

    handleMessage(data) {
        switch (data.type) {
            case 'status':
                this.updateThinkingText(data.content);
                break;

            case 'analysis':
                this.currentAnalysis = data.content;
                break;

            case 'sources':
                this.currentSources = data.content;
                this.sourcesCount += data.content.length;
                this.sourcesCountEl.textContent = this.sourcesCount;
                break;

            case 'answer':
                this.hideThinking();
                this.addAssistantMessage(data.content, this.currentSources, this.currentAnalysis);
                this.currentSources = [];
                this.currentAnalysis = null;
                break;

            case 'done':
                this.isProcessing = false;
                this.updateSendButton();
                break;

            case 'error':
                this.hideThinking();
                this.addErrorMessage(data.content);
                this.isProcessing = false;
                this.updateSendButton();
                break;
        }
    }

    addUserMessage(text) {
        const template = this.userMessageTemplate.content.cloneNode(true);
        const messageText = template.querySelector('.message-text');
        messageText.textContent = text;

        this.chatMessages.appendChild(template);
        this.scrollToBottom();
    }

    addAssistantMessage(text, sources, analysis) {
        const template = this.assistantMessageTemplate.content.cloneNode(true);
        const messageText = template.querySelector('.message-text');
        const messageSources = template.querySelector('.message-sources');
        const messageMeta = template.querySelector('.message-meta');

        // Render markdown
        messageText.innerHTML = marked.parse(text);

        // Apply syntax highlighting to any code blocks that weren't caught
        messageText.querySelectorAll('pre code:not(.hljs)').forEach((block) => {
            hljs.highlightElement(block);
        });

        // Add analysis badges
        if (analysis) {
            const analysisDiv = document.createElement('div');
            analysisDiv.className = 'query-analysis';

            if (analysis.intent) {
                const intentBadge = document.createElement('span');
                intentBadge.className = 'analysis-badge intent';
                intentBadge.textContent = analysis.intent;
                analysisDiv.appendChild(intentBadge);
            }

            if (analysis.class_names && analysis.class_names.length > 0) {
                analysis.class_names.slice(0, 3).forEach(name => {
                    const badge = document.createElement('span');
                    badge.className = 'analysis-badge';
                    badge.textContent = name;
                    analysisDiv.appendChild(badge);
                });
            }

            messageText.parentElement.insertBefore(analysisDiv, messageText);
        }

        // Add sources badge
        if (sources && sources.length > 0 && this.showSources.checked) {
            const sourcesBadge = document.createElement('button');
            sourcesBadge.className = 'sources-badge';
            sourcesBadge.innerHTML = `
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                    <polyline points="14 2 14 8 20 8"></polyline>
                </svg>
                ${sources.length} source${sources.length > 1 ? 's' : ''}
            `;
            sourcesBadge.onclick = () => this.showSourcesPanel(sources);
            messageSources.appendChild(sourcesBadge);
        }

        this.chatMessages.appendChild(template);
        this.scrollToBottom();
    }

    addErrorMessage(text) {
        const template = this.assistantMessageTemplate.content.cloneNode(true);
        const messageText = template.querySelector('.message-text');
        messageText.innerHTML = `<span style="color: var(--accent-error);">Error: ${this.escapeHtml(text)}</span>`;

        this.chatMessages.appendChild(template);
        this.scrollToBottom();
    }

    showThinking() {
        const template = this.thinkingTemplate.content.cloneNode(true);
        const thinking = template.querySelector('.thinking');
        thinking.id = 'current-thinking';

        this.chatMessages.appendChild(template);
        this.scrollToBottom();
    }

    updateThinkingText(text) {
        const thinking = document.getElementById('current-thinking');
        if (thinking) {
            const thinkingText = thinking.querySelector('.thinking-text');
            if (thinkingText) {
                thinkingText.textContent = text;
            }
        }
    }

    hideThinking() {
        const thinking = document.getElementById('current-thinking');
        if (thinking) {
            thinking.remove();
        }
    }

    showSourcesPanel(sources) {
        this.sourcesContent.innerHTML = '';

        sources.forEach((source, index) => {
            const card = this.createSourceCard(source, index);
            this.sourcesContent.appendChild(card);
        });

        this.sourcesPanel.classList.add('open');
    }

    createSourceCard(source, index) {
        const card = document.createElement('div');
        card.className = 'source-card';

        const scorePercent = Math.round(source.score * 100);
        const scoreColor = scorePercent >= 80 ? 'var(--accent-success)' :
                          scorePercent >= 60 ? 'var(--accent-warning)' :
                          'var(--text-secondary)';

        card.innerHTML = `
            <div class="source-card-header">
                <div class="source-file-info">
                    <div class="source-file-path">${this.escapeHtml(source.file_path)}</div>
                    <div class="source-location">Lines ${source.start_line}-${source.end_line}</div>
                </div>
                <div class="source-score" style="background-color: ${scoreColor}">
                    ${scorePercent}%
                </div>
            </div>
            <div class="source-meta">
                ${source.class_name ? `
                    <div class="source-meta-item">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect>
                        </svg>
                        ${this.escapeHtml(source.class_name)}
                    </div>
                ` : ''}
                ${source.method_name ? `
                    <div class="source-meta-item">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <polyline points="4 17 10 11 4 5"></polyline>
                            <line x1="12" y1="19" x2="20" y2="19"></line>
                        </svg>
                        ${this.escapeHtml(source.method_name)}
                    </div>
                ` : ''}
                <div class="source-meta-item">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <polyline points="16 18 22 12 16 6"></polyline>
                        <polyline points="8 6 2 12 8 18"></polyline>
                    </svg>
                    ${source.language || 'unknown'}
                </div>
            </div>
            <div class="source-code">
                <pre><code class="language-${source.language || 'plaintext'}">${this.escapeHtml(source.content)}</code></pre>
            </div>
        `;

        // Apply syntax highlighting
        const codeBlock = card.querySelector('code');
        if (codeBlock) {
            hljs.highlightElement(codeBlock);
        }

        return card;
    }

    closeSourcesPanel() {
        this.sourcesPanel.classList.remove('open');
    }

    clearChat() {
        // Keep only the welcome message
        const messages = this.chatMessages.querySelectorAll('.message');
        messages.forEach((msg, index) => {
            if (index > 0) {
                msg.remove();
            }
        });

        this.closeSourcesPanel();
    }

    copyCode(button) {
        const codeBlock = button.closest('.code-block');
        const code = codeBlock.querySelector('code');
        const text = code.textContent;

        navigator.clipboard.writeText(text).then(() => {
            const originalHtml = button.innerHTML;
            button.innerHTML = `
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <polyline points="20 6 9 17 4 12"></polyline>
                </svg>
                Copied!
            `;
            button.style.color = 'var(--accent-success)';

            setTimeout(() => {
                button.innerHTML = originalHtml;
                button.style.color = '';
            }, 2000);
        });
    }

    scrollToBottom() {
        requestAnimationFrame(() => {
            this.chatMessages.scrollTop = this.chatMessages.scrollHeight;
        });
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

// Initialize chat client
const chatClient = new ChatClient();
