import * as vscode from 'vscode';
import { ChatViewProvider } from './chatPanel';

export function activate(context: vscode.ExtensionContext) {
    const provider = new ChatViewProvider(context.extensionUri);

    // Register Sidebar Webview Provider
    context.subscriptions.push(
        vscode.window.registerWebviewViewProvider(ChatViewProvider.viewType, provider)
    );

    // Register Floating Chat Window Command
    context.subscriptions.push(
        vscode.commands.registerCommand('m5.openFloatingChat', () => {
            const panel = vscode.window.createWebviewPanel(
                'm5-floating-chat',
                'M5 Graph-RAG Floating Chat',
                vscode.ViewColumn.Beside,
                {
                    enableScripts: true,
                    localResourceRoots: [context.extensionUri],
                    retainContextWhenHidden: true
                }
            );

            panel.webview.html = provider.getHtmlForWebview(panel.webview);

            panel.webview.onDidReceiveMessage(async (data: any) => {
                switch (data.type) {
                    case 'askQuery': {
                        await provider.handleQueryFromWebview(data.value, panel.webview);
                        break;
                    }
                }
            });
        })
    );

    console.log('[+] Project M5 AI Assistant Extension activated!');
}

export function deactivate() {}
