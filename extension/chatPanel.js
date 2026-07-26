"use strict";
var __createBinding = (this && this.__createBinding) || (Object.create ? (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    var desc = Object.getOwnPropertyDescriptor(m, k);
    if (!desc || ("get" in desc ? !m.__esModule : desc.writable || desc.configurable)) {
      desc = { enumerable: true, get: function() { return m[k]; } };
    }
    Object.defineProperty(o, k2, desc);
}) : (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    o[k2] = m[k];
}));
var __setModuleDefault = (this && this.__setModuleDefault) || (Object.create ? (function(o, v) {
    Object.defineProperty(o, "default", { enumerable: true, value: v });
}) : function(o, v) {
    o["default"] = v;
});
var __importStar = (this && this.__importStar) || (function () {
    var ownKeys = function(o) {
        ownKeys = Object.getOwnPropertyNames || function (o) {
            var ar = [];
            for (var k in o) if (Object.prototype.hasOwnProperty.call(o, k)) ar[ar.length] = k;
            return ar;
        };
        return ownKeys(o);
    };
    return function (mod) {
        if (mod && mod.__esModule) return mod;
        var result = {};
        if (mod != null) for (var k = ownKeys(mod), i = 0; i < k.length; i++) if (k[i] !== "default") __createBinding(result, mod, k[i]);
        __setModuleDefault(result, mod);
        return result;
    };
})();
Object.defineProperty(exports, "__esModule", { value: true });
exports.ChatViewProvider = void 0;
const vscode = __importStar(require("vscode"));
class ChatViewProvider {
    _extensionUri;
    static viewType = 'm5-ai-chat-view';
    _view;
    constructor(_extensionUri) {
        this._extensionUri = _extensionUri;
    }
    resolveWebviewView(webviewView, context, _token) {
        this._view = webviewView;
        webviewView.webview.options = {
            enableScripts: true,
            localResourceRoots: [this._extensionUri]
        };
        webviewView.webview.html = this._getHtmlForWebview(webviewView.webview);
        // Listen for user messages sent from the HTML Chat UI
        webviewView.webview.onDidReceiveMessage(async (data) => {
            switch (data.type) {
                case 'askQuery': {
                    // Capture active document path in VS Code
                    const activeEditor = vscode.window.activeTextEditor;
                    const activeFilePath = activeEditor ? activeEditor.document.fileName : '';
                    // Send query to FastAPI backend
                    await this._handleQuery(data.value, activeFilePath);
                    break;
                }
            }
        });
    }
    async _handleQuery(query, filePath) {
        try {
            const response = await fetch('http://localhost:8000/api/v1/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ query: query, file_path: filePath })
            });
            if (!response.ok) {
                throw new Error(`Server returned status: ${response.status}`);
            }
            const data = await response.json();
            this._view?.webview.postMessage({ type: 'addAnswer', value: data.answer });
        }
        catch (err) {
            this._view?.webview.postMessage({ type: 'addError', value: `Error connecting to backend: ${err.message}` });
        }
    }
    _getHtmlForWebview(webview) {
        return `<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Graph-RAG Chat</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; padding: 10px; color: var(--vscode-foreground); background-color: var(--vscode-sideBar-background); }
        #chat-container { display: flex; flex-direction: column; height: calc(100vh - 80px); overflow-y: auto; margin-bottom: 10px; }
        .message { margin-bottom: 12px; padding: 8px 12px; border-radius: 6px; font-size: 13px; line-height: 1.4; word-wrap: break-word; }
        .user { background: var(--vscode-button-background); color: var(--vscode-button-foreground); align-self: flex-end; max-width: 85%; }
        .assistant { background: var(--vscode-editor-inactiveSelectionBackground); align-self: flex-start; max-width: 90%; border: 1px solid var(--vscode-widget-border); }
        .error { background: var(--vscode-inputValidation-errorBackground); border: 1px solid var(--vscode-inputValidation-errorBorder); color: var(--vscode-errorForeground); }
        #input-area { display: flex; gap: 6px; }
        input { flex: 1; padding: 8px; border-radius: 4px; border: 1px solid var(--vscode-input-border); background: var(--vscode-input-background); color: var(--vscode-input-foreground); }
        button { padding: 8px 14px; border-radius: 4px; border: none; background: var(--vscode-button-background); color: var(--vscode-button-foreground); cursor: pointer; font-weight: bold; }
        button:hover { background: var(--vscode-button-hoverBackground); }
    </style>
</head>
<body>
    <h3> M5 </h3>
    <div id="chat-container"></div>
    <div id="input-area">
        <input type="text" id="query-input" placeholder="Ask about open codebase..." />
        <button id="send-btn">Send</button>
    </div>

    <script>
        const vscode = acquireVsCodeApi();
        const chatContainer = document.getElementById('chat-container');
        const queryInput = document.getElementById('query-input');
        const sendBtn = document.getElementById('send-btn');

        function sendQuery() {
            const text = queryInput.value.trim();
            if (!text) return;
            
            appendMessage(text, 'user');
            queryInput.value = '';
            vscode.postMessage({ type: 'askQuery', value: text });
        }

        sendBtn.addEventListener('click', sendQuery);
        queryInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') sendQuery();
        });

        function appendMessage(text, className) {
            const msg = document.createElement('div');
            msg.className = 'message ' + className;
            msg.innerText = text;
            chatContainer.appendChild(msg);
            chatContainer.scrollTop = chatContainer.scrollHeight;
        }

        window.addEventListener('message', event => {
            const message = event.data;
            if (message.type === 'addAnswer') {
                appendMessage(message.value, 'assistant');
            } else if (message.type === 'addError') {
                appendMessage(message.value, 'error');
            }
        });
    </script>
</body>
</html>`;
    }
}
exports.ChatViewProvider = ChatViewProvider;
//# sourceMappingURL=chatPanel.js.map