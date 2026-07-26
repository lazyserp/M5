import * as vscode from 'vscode';
import { ChatViewProvider } from './chatPanel';

export function activate(context: vscode.ExtensionContext) {
    const provider = new ChatViewProvider(context.extensionUri);

    // Register our Sidebar Webview Provider
    context.subscriptions.push(
        vscode.window.registerWebviewViewProvider(ChatViewProvider.viewType, provider)
    );

    console.log('[+] Project M5 AI Assistant Extension activated!');
}

export function deactivate() {}
