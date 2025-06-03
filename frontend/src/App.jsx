import { useState, useRef } from 'react';
import SwisperChat from './SwisperChat';
import ContractViewer from './ContractViewer';
import LogViewer from './LogViewer';

function App() {
  const [activeTab, setActiveTab] = useState('chat');
  const chatRef = useRef();

  return (
    <main className="min-h-screen bg-chat-background text-chat-text p-6">
      {/* Tab Navigation */}
      <div className="max-w-xl mx-auto mb-4">
        <div className="flex border-b border-chat-muted">
          <button
            onClick={() => setActiveTab('chat')}
            className={`px-4 py-2 font-medium text-sm border-b-2 transition-colors ${
              activeTab === 'chat'
                ? 'border-chat-accent text-chat-accent'
                : 'border-transparent text-chat-secondary hover:text-chat-text'
            }`}
          >
            Chat
          </button>
          <button
            onClick={() => setActiveTab('contracts')}
            className={`px-4 py-2 font-medium text-sm border-b-2 transition-colors ${
              activeTab === 'contracts'
                ? 'border-chat-accent text-chat-accent'
                : 'border-transparent text-chat-secondary hover:text-chat-text'
            }`}
          >
            Contracts
          </button>
          <button
            onClick={() => setActiveTab('logs')}
            className={`px-4 py-2 font-medium text-sm border-b-2 transition-colors ${
              activeTab === 'logs'
                ? 'border-chat-accent text-chat-accent'
                : 'border-transparent text-chat-secondary hover:text-chat-text'
            }`}
          >
            Logs
          </button>
        </div>
      </div>

      {/* Tab Content */}
      {activeTab === 'chat' && <SwisperChat ref={chatRef} />}
      {activeTab === 'contracts' && <ContractViewer />}
      {activeTab === 'logs' && <LogViewer />}
    </main>
  );
}

export default App;
