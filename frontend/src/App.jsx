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
  const [isFullWidth, setIsFullWidth] = useState(false);
  const chatRef = useRef();

  const tabs = [
    { id: 'chat', label: 'Chat', icon: '/images/img_icon.svg' },
    { id: 'contracts', label: 'Contracts', icon: '/images/img_folderfilled.svg' },
    { id: 'logs', label: 'Logs', icon: '/images/img_filterlistfilled.svg' }
  ];

  const handleSearch = (query) => {
    console.log('Search query:', query);
  };

  const handleSectionSelect = (section) => {
    console.log('Section selected:', section);
  };

  const handleSessionSelect = (sessionId) => {
    console.log('Session selected:', sessionId);
  };

  const handleSearchResultSelect = (sessionId, messageIndex) => {
    console.log('Search result selected:', sessionId, messageIndex);
  };

  const handleToggleFullWidth = () => {
    setIsFullWidth(!isFullWidth);
  };

  const handleToggleSidebar = () => {
    setSidebarCollapsed(!sidebarCollapsed);
  };

  return (
    <div className="min-h-screen bg-[#020305] text-white">
      <Header 
        onSearch={handleSearch}
        onSearchResultSelect={handleSearchResultSelect}
        isFullWidth={isFullWidth}
        onToggleFullWidth={handleToggleFullWidth}
        onToggleSidebar={handleToggleSidebar}
      />
      
      <div className="flex h-[calc(100vh-80px)] p-6 gap-6">
        {!sidebarCollapsed && (
          <Sidebar 
            onSectionSelect={handleSectionSelect}
            onSessionSelect={handleSessionSelect}
            currentSessionId="default_session"
            isCollapsed={sidebarCollapsed}
          />
        )}
        
        <main className={`flex-1 bg-[#141923] rounded-2xl p-6 flex flex-col ${isFullWidth ? 'max-w-none' : 'max-w-6xl mx-auto'}`}>
          <TabBar 
            tabs={tabs}
            activeTab={activeTab}
            onTabChange={setActiveTab}
          />
          
          <div className="flex-1 mt-6">
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
