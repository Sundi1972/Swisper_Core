import { useState, useRef, useEffect } from 'react';
import SwisperChat from './SwisperChat';
import ContractViewer from './ContractViewer';
import LogViewer from './LogViewer';
import TabBar from './components/ui/TabBar';
import Header from './components/common/Header';
import Sidebar from './components/common/Sidebar';

function App() {
  console.log('Frontend Environment Check:');
  console.log('API Base URL:', __API_BASE_URL__);
  console.log('Expected: http://localhost:8000');
  
  const [activeTab, setActiveTab] = useState('chat');
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [isFullWidth, setIsFullWidth] = useState(false);
  const [currentSessionId, setCurrentSessionId] = useState(null);
  const [currentSearchQuery, setCurrentSearchQuery] = useState('');
  const [searchHighlightEnabled, setSearchHighlightEnabled] = useState(false);
  const chatRef = useRef();

  const tabs = [
    { id: 'chat', label: 'Chat', icon: '/images/img_icon.svg' },
    { id: 'contracts', label: 'Contracts', icon: '/images/img_folderfilled.svg' },
    { id: 'logs', label: 'Logs', icon: '/images/img_filterlistfilled.svg' }
  ];

  const handleSearch = (query) => {
    console.log('Search query:', query);
    setSearchHighlightEnabled(query.trim().length > 0);
    setCurrentSearchQuery(query);
  };

  const handleSectionSelect = (section) => {
    console.log('Section selected:', section);
  };

  const handleSessionSelect = async (sessionId) => {
    console.log('Session selected:', sessionId);
    try {
      setCurrentSessionId(sessionId);
      
      if (chatRef.current) {
        await chatRef.current.loadSession(sessionId);
      }
    } catch (error) {
      console.error('Error switching to session:', error);
      alert('Failed to switch to selected session. Please try again.');
    }
  };

  const handleSearchResultSelect = async (sessionId, messageIndex) => {
    console.log('Search result selected:', sessionId, messageIndex);
    
    try {
      setCurrentSessionId(sessionId);
      
      if (chatRef.current) {
        await chatRef.current.loadSession(sessionId);
        
        setTimeout(() => {
          if (chatRef.current && chatRef.current.scrollToMessage) {
            chatRef.current.scrollToMessage(messageIndex);
          }
        }, 500);
      }
      
      setSearchHighlightEnabled(true);
      
    } catch (error) {
      console.error('Error switching to session:', error);
      alert('Failed to switch to selected session. Please try again.');
    }
  };

  const handleToggleFullWidth = () => {
    setIsFullWidth(!isFullWidth);
  };

  const handleToggleSidebar = () => {
    setSidebarCollapsed(!sidebarCollapsed);
  };

  useEffect(() => {
    const updateSessionId = () => {
      if (chatRef.current && chatRef.current.getSessionId) {
        setCurrentSessionId(chatRef.current.getSessionId());
      }
    };
    
    const interval = setInterval(updateSessionId, 1000);
    updateSessionId();
    
    return () => clearInterval(interval);
  }, [activeTab]);

  return (
    <div className="min-h-screen bg-[#020305] text-white">
      <Header 
        onSearch={handleSearch}
        onSearchResultSelect={handleSearchResultSelect}
        onSearchQueryChange={setCurrentSearchQuery}
        isFullWidth={isFullWidth}
        onToggleFullWidth={handleToggleFullWidth}
        onToggleSidebar={handleToggleSidebar}
        currentSessionId={currentSessionId}
      />
      
      <div className="flex h-[calc(100vh-80px)] p-6 gap-6">
        <Sidebar 
          onSectionSelect={handleSectionSelect}
          onSessionSelect={handleSessionSelect}
          currentSessionId={currentSessionId}
          isCollapsed={sidebarCollapsed}
          onToggleSidebar={handleToggleSidebar}
        />
        
        <main className={`flex-1 bg-[#141923] rounded-2xl p-6 flex flex-col ${isFullWidth ? 'max-w-none' : 'max-w-6xl mx-auto'}`}>
          <TabBar 
            tabs={tabs}
            activeTab={activeTab}
            onTabChange={setActiveTab}
          />
          
          <div className="flex-1 mt-6">
            {activeTab === 'chat' && (
              <SwisperChat 
                ref={chatRef} 
                searchQuery={currentSearchQuery}
                highlightEnabled={searchHighlightEnabled}
              />
            )}
            {activeTab === 'contracts' && <ContractViewer />}
            {activeTab === 'logs' && <LogViewer />}
          </div>
        </main>
      </div>
    </div>
  );
}

export default App;
