import { useState, useRef } from 'react';
import SwisperChat from './SwisperChat';
import ContractViewer from './ContractViewer';
import LogViewer from './LogViewer';
import TabBar from './components/ui/TabBar';
import Header from './components/common/Header';
import Sidebar from './components/common/Sidebar';

function App() {
  const [activeTab, setActiveTab] = useState('chat');
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const chatRef = useRef();

  const tabs = [
    { id: 'chat', label: 'Chat' },
    { id: 'contracts', label: 'Contracts' },
    { id: 'logs', label: 'Logs' }
  ];

  const handleSearch = (query) => {
    console.log('Search query:', query);
  };

  const handleSectionSelect = (section) => {
    console.log('Section selected:', section);
  };

  return (
    <div className="min-h-screen bg-chat-background text-chat-text flex flex-col">
      <Header onSearch={handleSearch} />
      
      <div className="flex flex-1 gap-4 p-4">
        <Sidebar 
          onSectionSelect={handleSectionSelect}
          isCollapsed={sidebarCollapsed}
        />
        
        <main className="flex-1 flex flex-col">
          <div className="mb-4">
            <TabBar 
              tabs={tabs}
              activeTab={activeTab}
              onTabChange={setActiveTab}
            />
          </div>

          <div className="flex-1">
            {activeTab === 'chat' && <SwisperChat ref={chatRef} />}
            {activeTab === 'contracts' && <ContractViewer />}
            {activeTab === 'logs' && <LogViewer />}
          </div>
        </main>
      </div>
    </div>
  );
}

export default App;
