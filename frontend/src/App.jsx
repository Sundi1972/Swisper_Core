import { useState, useRef } from 'react';
import SwisperChat from './SwisperChat';
import ContractViewer from './ContractViewer';
import LogViewer from './LogViewer';

function App() {
  const [activeTab, setActiveTab] = useState('chat');
  const chatRef = useRef();

  return (
    <main className="min-h-screen bg-white text-black p-6">
      {/* Tab Navigation */}
      <div className="max-w-xl mx-auto mb-4">
        <div className="flex border-b border-gray-300">
          <button
            onClick={() => setActiveTab('chat')}
            className={`px-4 py-2 font-medium text-sm border-b-2 transition-colors ${
              activeTab === 'chat'
                ? 'border-blue-600 text-blue-600'
                : 'border-transparent text-gray-600 hover:text-gray-800'
            }`}
          >
            Chat
          </button>
          <button
            onClick={() => setActiveTab('contracts')}
            className={`px-4 py-2 font-medium text-sm border-b-2 transition-colors ${
              activeTab === 'contracts'
                ? 'border-blue-600 text-blue-600'
                : 'border-transparent text-gray-600 hover:text-gray-800'
            }`}
          >
            Contracts
          </button>
          <button
            onClick={() => setActiveTab('logs')}
            className={`px-4 py-2 font-medium text-sm border-b-2 transition-colors ${
              activeTab === 'logs'
                ? 'border-blue-600 text-blue-600'
                : 'border-transparent text-gray-600 hover:text-gray-800'
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
