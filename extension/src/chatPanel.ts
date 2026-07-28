import * as vscode from 'vscode';

export class ChatViewProvider implements vscode.WebviewViewProvider {
    public static readonly viewType = 'm5-ai-chat-view';
    private _view?: vscode.WebviewView;

    constructor(private readonly _extensionUri: vscode.Uri) {}

    public resolveWebviewView(
        webviewView: vscode.WebviewView,
        context: vscode.WebviewViewResolveContext,
        _token: vscode.CancellationToken,
    ) {
        this._view = webviewView;

        webviewView.webview.options = {
            enableScripts: true,
            localResourceRoots: [this._extensionUri]
        };

        webviewView.webview.html = this._getHtmlForWebview(webviewView.webview);

        // Listen for user messages sent from the HTML Chat UI
        webviewView.webview.onDidReceiveMessage(async (data: any) => {
            switch (data.type) {
                case 'askQuery': {
                    await this._handleQuery(data.value);
                    break;
                }
            }
        });
    }

    private async _handleQuery(query: string) {
        try {
            const config = vscode.workspace.getConfiguration('m5');
            const serverUrl = config.get<string>('serverUrl') || 'http://localhost:18000';
            const repositoryId = config.get<string>('repositoryId') || '';
            const commitSha = config.get<string>('commitSha') || '';
            const accessToken = config.get<string>('accessToken') || '';
            if (!repositoryId || !commitSha || !accessToken) {
                throw new Error('Set m5.repositoryId, m5.commitSha, and m5.accessToken before asking a question.');
            }

            const response = await fetch(`${serverUrl}/api/v1/chat`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${accessToken}`
                },
                body: JSON.stringify({
                    query: query,
                    repository_id: repositoryId,
                    commit_sha: commitSha
                })
            });

            if (!response.ok) {
                throw new Error(`Server returned status: ${response.status}`);
            }
            this._view?.webview.postMessage({ type: 'addAnswer', value: await response.json() });
        } catch (err: any) {
            this._view?.webview.postMessage({ type: 'addError', value: `Error connecting to backend: ${err.message}` });
        }
    }

    private _getHtmlForWebview(webview: vscode.Webview): string {
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
    <h3>M   5 </h3>
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
        let activeStreamElement = null;

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
            if (message.type === 'startStream') {
                activeStreamElement = document.createElement('div');
                activeStreamElement.className = 'message assistant';
                chatContainer.appendChild(activeStreamElement);
            } else if (message.type === 'appendToken') {
                if (activeStreamElement) {
                    activeStreamElement.innerText += message.value;
                    chatContainer.scrollTop = chatContainer.scrollHeight;
                }
            } else if (message.type === 'addAnswer') {
                const answer = message.value;
                let text = answer.answer;
                if (answer.citations && answer.citations.length) {
                    text += '\n\nSources:';
                    for (const citation of answer.citations) {
                        text += '\n• ' + citation.repository_id + ' | ' + citation.commit_sha.slice(0, 8) + ' | ' + citation.file_path + ' | lines ' + citation.start_line + '-' + citation.end_line + ' | score ' + citation.retrieval_score;
                    }
                }
                appendMessage(text, 'assistant');
            } else if (message.type === 'addError') {
                appendMessage(message.value, 'error');
            }
        });
    </script>
</body>
</html>`;
    }
}
