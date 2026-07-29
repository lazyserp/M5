import * as vscode from 'vscode';
import { marked } from 'marked';

export class ChatViewProvider implements vscode.WebviewViewProvider {
    public static readonly viewType = 'm5-ai-chat-view';
    private _view?: vscode.WebviewView;

    constructor(private readonly _extensionUri: vscode.Uri) {
        marked.setOptions({
            gfm: true,
            breaks: true
        });
    }

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

        webviewView.webview.html = this.getHtmlForWebview(webviewView.webview);

        webviewView.webview.onDidReceiveMessage(async (data: any) => {
            switch (data.type) {
                case 'askQuery': {
                    await this.handleQueryFromWebview(data.value, webviewView.webview, data.history);
                    break;
                }
            }
        });
    }

    public async handleQueryFromWebview(query: string, webview: vscode.Webview, history?: Array<{role: string, content: string}>) {
        try {
            const config = vscode.workspace.getConfiguration('m5');
            const serverUrl = config.get<string>('serverUrl') || 'http://localhost:18000';
            const headers: Record<string, string> = {
                'Content-Type': 'application/json'
            };

            const body: Record<string, any> = { query: query };
            if (history && history.length) body['history'] = history;

            const response = await fetch(`${serverUrl}/api/v1/chat`, {
                method: 'POST',
                headers: headers,
                body: JSON.stringify(body)
            });

            if (!response.ok) {
                throw new Error(`Server returned status: ${response.status}`);
            }

            const answerData: any = await response.json();
            const rawAnswer = answerData.answer || '';
            let html = await marked.parse(rawAnswer);

            if (answerData.citations && answerData.citations.length) {
                html += '<div class="citations-container"><strong>Sources:</strong><ul>';
                const seen = new Set<string>();
                for (const citation of answerData.citations) {
                    let cleanPath = citation.file_path.replace(/^\/app\/workspace\//, '').replace(/^app\/workspace\//, '');
                    const lineRange = 'lines ' + citation.start_line + '-' + citation.end_line;
                    const key = cleanPath + ':' + lineRange;
                    if (!seen.has(key)) {
                        seen.add(key);
                        html += `<li>📄 <code>${cleanPath}</code> (${lineRange})</li>`;
                    }
                }
                html += '</ul></div>';
            }

            webview.postMessage({ type: 'addAnswer', value: { rawText: rawAnswer, html: html } });
        } catch (err: any) {
            webview.postMessage({ type: 'addError', value: `Error connecting to backend: ${err.message}` });
        }
    }

    private getWebviewScript(): string {
        return [
            'const vscode = acquireVsCodeApi();',
            'const chatContainer = document.getElementById("chat-container");',
            'const queryInput = document.getElementById("query-input");',
            'const sendBtn = document.getElementById("send-btn");',
            'const clearBtn = document.getElementById("clear-btn");',
            'let state = vscode.getState() || { history: [] };',
            '',
            'function renderHistory() {',
            '    chatContainer.innerHTML = "";',
            '    if (state.history && state.history.length) {',
            '        state.history.forEach(function(item) { appendMessage(item.text, item.className, item.html, false); });',
            '        chatContainer.scrollTop = chatContainer.scrollHeight;',
            '    }',
            '}',
            '',
            'function saveMessage(text, className, html) {',
            '    state.history = state.history || [];',
            '    state.history.push({ text: text, className: className, html: html });',
            '    vscode.setState(state);',
            '    appendMessage(text, className, html, true);',
            '}',
            '',
            'function appendMessage(text, className, html, scroll) {',
            '    if (scroll === undefined) scroll = true;',
            '    const msg = document.createElement("div");',
            '    msg.className = "message " + className;',
            '    if (className === "assistant" && html) {',
            '        msg.innerHTML = html;',
            '    } else {',
            '        msg.innerText = text;',
            '    }',
            '    chatContainer.appendChild(msg);',
            '    if (scroll) { chatContainer.scrollTop = chatContainer.scrollHeight; }',
            '}',
            '',
            'renderHistory();',
            '',
            'function sendQuery() {',
            '    const text = queryInput.value.trim();',
            '    if (!text) return;',
            '    const history = (state.history || []).map(function(h) { return { role: h.className === "user" ? "user" : "assistant", content: h.text }; });',
            '    saveMessage(text, "user", null);',
            '    queryInput.value = "";',
            '    vscode.postMessage({ type: "askQuery", value: text, history: history });',
            '}',
            '',
            'sendBtn.addEventListener("click", sendQuery);',
            'queryInput.addEventListener("keypress", function(e) { if (e.key === "Enter") sendQuery(); });',
            'clearBtn.addEventListener("click", function() { state.history = []; vscode.setState(state); chatContainer.innerHTML = ""; });',
            '',
            'window.addEventListener("message", function(event) {',
            '    const message = event.data;',
            '    if (message.type === "addAnswer") {',
            '        const answer = message.value;',
            '        saveMessage(answer.rawText, "assistant", answer.html);',
            '    } else if (message.type === "addError") {',
            '        saveMessage(message.value, "error", null);',
            '    }',
            '});'
        ].join('\n');
    }

    public getHtmlForWebview(webview: vscode.Webview): string {
        return `<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>M5 Graph-RAG Chat</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; padding: 10px; color: var(--vscode-foreground); background-color: var(--vscode-sideBar-background); margin: 0; box-sizing: border-box; }
        #header-bar { display: flex; justify-content: space-between; align-items: center; padding-bottom: 8px; border-bottom: 1px solid var(--vscode-widget-border); margin-bottom: 10px; }
        #header-bar h3 { margin: 0; font-size: 13px; color: var(--vscode-sideBarTitle-foreground); font-weight: 600; }
        .clear-btn { background: transparent; border: 1px solid var(--vscode-widget-border); color: var(--vscode-foreground); padding: 2px 8px; border-radius: 4px; font-size: 11px; cursor: pointer; }
        .clear-btn:hover { background: var(--vscode-button-secondaryHoverBackground); }
        #chat-container { display: flex; flex-direction: column; height: calc(100vh - 110px); overflow-y: auto; margin-bottom: 10px; padding-right: 4px; }
        .message { margin-bottom: 12px; padding: 10px 14px; border-radius: 6px; font-size: 13px; line-height: 1.55; word-wrap: break-word; }
        .user { background: var(--vscode-button-background); color: var(--vscode-button-foreground); align-self: flex-end; max-width: 85%; white-space: pre-wrap; }
        .assistant { background: var(--vscode-editor-inactiveSelectionBackground); align-self: flex-start; max-width: 92%; border: 1px solid var(--vscode-widget-border); color: var(--vscode-editor-foreground); }
        .error { background: var(--vscode-inputValidation-errorBackground); border: 1px solid var(--vscode-inputValidation-errorBorder); color: var(--vscode-errorForeground); white-space: pre-wrap; }

        /* Rich Markdown Typography */
        .assistant p { margin: 6px 0; }
        .assistant h1, .assistant h2, .assistant h3, .assistant h4 { margin-top: 14px; margin-bottom: 6px; color: var(--vscode-sideBarTitle-foreground); font-weight: 600; border-bottom: 1px solid var(--vscode-widget-border); padding-bottom: 3px; }
        .assistant h1 { font-size: 16px; }
        .assistant h2 { font-size: 15px; }
        .assistant h3 { font-size: 14px; }
        .assistant strong { font-weight: 600; color: var(--vscode-editor-foreground); }
        .assistant em { font-style: italic; opacity: 0.9; }
        .assistant ul, .assistant ol { margin: 6px 0; padding-left: 20px; }
        .assistant li { margin-bottom: 4px; }
        .assistant hr { border: none; border-top: 1px solid var(--vscode-widget-border); margin: 12px 0; }

        /* Code Blocks & Inline Code */
        code, code.inline-code { background: var(--vscode-textCodeBlock-background, rgba(127,127,127,0.15)); padding: 2px 5px; border-radius: 3px; font-family: var(--vscode-editor-font-family, Consolas, Monaco, monospace); font-size: 0.9em; border: 1px solid var(--vscode-widget-border); color: var(--vscode-textPreformat-foreground, inherit); }
        pre { margin: 10px 0; padding: 10px; border: 1px solid var(--vscode-widget-border); border-radius: 6px; background: var(--vscode-editor-background, #1e1e1e); overflow-x: auto; font-family: var(--vscode-editor-font-family, Consolas, Monaco, monospace); font-size: 12px; line-height: 1.4; color: var(--vscode-editor-foreground); }
        pre code { background: none; border: none; padding: 0; }

        .citations-container { margin-top: 12px; padding-top: 8px; border-top: 1px solid var(--vscode-widget-border); font-size: 12px; }
        .citations-container ul { margin: 4px 0 0 0; padding-left: 16px; list-style-type: none; }
        .citations-container li { margin-bottom: 4px; }

        #input-area { display: flex; gap: 6px; }
        input { flex: 1; padding: 8px; border-radius: 4px; border: 1px solid var(--vscode-input-border); background: var(--vscode-input-background); color: var(--vscode-input-foreground); }
        button#send-btn { padding: 8px 14px; border-radius: 4px; border: none; background: var(--vscode-button-background); color: var(--vscode-button-foreground); cursor: pointer; font-weight: bold; }
        button#send-btn:hover { background: var(--vscode-button-hoverBackground); }
    </style>
</head>
<body>
    <div id="header-bar">
        <h3>M5 Intelligence Chat</h3>
        <button class="clear-btn" id="clear-btn" title="Clear Chat History">Clear</button>
    </div>
    <div id="chat-container"></div>
    <div id="input-area">
        <input type="text" id="query-input" placeholder="Ask about open codebase..." />
        <button id="send-btn">Send</button>
    </div>

    <script>
${this.getWebviewScript()}
    </script>
</body>
</html>`;
    }
}
