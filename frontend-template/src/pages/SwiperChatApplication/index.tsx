// src/pages/SwiperChatApplication/index.tsx
import React, { useState } from 'react';
import Header from '../../components/common/Header';
import Sidebar from '../../components/common/Sidebar';
import TabBar from '../../components/ui/TabBar';
import { Button } from '../../components/ui/Button';
import InputField from '../../components/ui/InputField';
import { Message, Tab } from '../../types/SwiperChatApplication';

const SwiperChatApplication: React.FC = () => {
  const [isFullWidth, setIsFullWidth] = useState(false);
  const [selectedSection, setSelectedSection] = useState('');
  const [messageInput, setMessageInput] = useState('');
  const [activeTab, setActiveTab] = useState('chat');
  const [messages, setMessages] = useState<Message[]>([
    {
      id: '1',
      content: 'Qorem ipsum dolor sit amet, consectetur adipiscing elit. Etiam eu turpis molestie, dictum est a, mattis tellus. Sed dignissim, metus nec fringilla accumsan, risus sem sollicitudin lacus, ut interdum tellus elit sed risus. Maecenas eget condimentum velit, sit amet feugiat lectu?',
      timestamp: 'Yesterday, 17:56',
      isUser: false
    },
    {
      id: '2',
      content: 'I am a 60-year-old man, standing at 1.78 meters tall, and I am trying to improve my overall health, energy levels, and mobility as I get older. I would like to know how many times per week I should ideally be working out to achieve good fitness without overstraining myself or risking injury.\n\nShould I be focusing more on strength training, cardio, flexibility exercises, or a balanced combination of all three?\n\nAlso, are there specific considerations for someone my age and height when planning a weekly workout routine, and how important is rest and recovery between sessions to maximise results?',
      timestamp: 'Yesterday, 17:56',
      isUser: true
    },
    {
      id: '3',
      content: 'Is creatine really effective?',
      timestamp: 'Yesterday, 15:23',
      isUser: false
    },
    {
      id: '4',
      content: 'Qorem ipsum dolor sit amet, consectetur adipiscing elit. Etiam eu turpis molestie, dictum est a, mattis tellus. Sed dignissim, metus nec fringilla accumsan, risus sem sollicitudin lacus, ut interdum tellus elit sed risus. Maecenas eget condimentum velit, sit amet feugiat lectus. Class aptent taciti sociosqu ad litora torquent per conubia nostra, per inceptos himenaeos. Praesent auctor purus luctus enim egestas, ac scelerisque ante pulvinar. Donec ut rhoncus ex. Suspendisse ac rhoncus nisl, eu tempor urna. Curabitur vel bibendum lorem. Morbi convallis convallis diam sit amet lacinia. Aliquam in elementum tellus.\n\nCurabitur tempor quis eros tempus lacinia. Nam bibendum pellentesque quam a convallis. Sed ut vulputate nisi. Integer in felis sed leo vestibulum venenatis. Suspendisse quis arcu sem. Aenean feugiat ex eu vestibulum vestibulum. Morbi a eleifend magna. Nam metus lacus, porttitor eu mauris a, blandit ultrices nibh. Mauris sit amet magna non ligula vestibulum eleifend. Nulla varius volutpat turpis sed lacinia. Nam eget mi in purus lobortis eleifend. Sed nec ante dictum sem condimentum ullamcorper quis venenatis nisi. Proin vitae facilisis nisi, ac posuere leo.',
      timestamp: 'Yesterday, 17:56',
      isUser: true
    }
  ]);

  const tabs: Tab[] = [
    {
      id: 'chat',
      label: 'Chat',
      icon: '/images/img_icon.svg'
    },
    {
      id: 'contracts',
      label: 'Contracts',
      icon: '/images/img_folderfilled.svg'
    },
    {
      id: 'logs',
      label: 'Logs',
      icon: '/images/img_filterlistfilled.svg'
    }
  ];

  const handleToggleFullWidth = () => {
    setIsFullWidth(!isFullWidth);
  };

  const handleSectionSelect = (section: string) => {
    setSelectedSection(section);
    console.log('Selected section:', section);
  };

  const handleFeedback = () => {
    alert('Thank you for your feedback!');
  };

  const handleSearch = (query: string) => {
    console.log('Search query:', query);
  };

  const handleSendMessage = () => {
    if (messageInput.trim()) {
      const newMessage: Message = {
        id: Date.now().toString(),
        content: messageInput,
        timestamp: new Date().toLocaleString(),
        isUser: true
      };
      setMessages([...messages, newMessage]);
      setMessageInput('');
    }
  };

  const handleVoiceInput = () => {
    console.log('Voice input activated');
    alert('Voice input feature activated');
  };

  const handleAddAction = () => {
    console.log('Add action triggered');
    alert('Add new item');
  };

  const handleNewSession = () => {
    console.log('New session started');
    alert('Starting new session');
    setMessages([]);
    setMessageInput('');
  };

  const handleAskDox = () => {
    console.log('Ask Dox activated');
    alert('Ask Dox feature activated');
  };

  const handleTabChange = (tabId: string) => {
    setActiveTab(tabId);
    console.log('Active tab changed to:', tabId);
  };

  const renderTabContent = () => {
    switch (activeTab) {
      case 'chat':
        return (
          <>
            {/* Chat Header */}
            <div className="flex items-center mb-6">
              <div className="flex items-center bg-transparent rounded-lg px-3 py-2">
                <span className="text-[#b6c2d1] text-base mr-3">DeepSeek 2.0</span>
                <img src="/images/img_arrowdropdownfilled.svg" alt="Dropdown" className="h-6 w-6" />
              </div>
            </div>

            {/* Messages Area */}
            <div className="flex-1 overflow-y-auto space-y-6 mb-6">
              {messages.map((message, index) => (
                <div key={message.id} className={`flex ${message.isUser ? 'justify-end' : 'justify-start'}`}>
                  <div className={`max-w-[492px] ${
                    message.isUser 
                      ? 'bg-[#141923] rounded-lg p-4' 
                      : 'bg-[#222834] rounded-2xl p-4 shadow-[0px_2px_1px_#00000033]'
                  }`}>
                    <p className={`text-sm leading-5 mb-2 ${
                      message.isUser ? 'text-[#000000dd]' : 'text-[#f9fbfc]'
                    }`} style={{ whiteSpace: 'pre-line' }}>
                      {message.content}
                    </p>
                    <p className="text-[#b6c2d1] text-sm">{message.timestamp}</p>
                  </div>
                </div>
              ))}
            </div>

            {/* Message Input Area */}
            <div className="bg-[#020305] rounded-lg p-5">
              <p className="text-[#8f99ad] text-sm mb-4">How can I help?</p>
              <div className="flex items-center space-x-3">
                <button 
                  onClick={handleAddAction}
                  className="h-[35px] w-[35px] border border-[#b6c2d1] rounded-[17px] flex items-center justify-center text-[#b6c2d1] text-base hover:bg-[#b6c2d1] hover:text-[#020305] transition-colors"
                >
                  +
                </button>
                <button 
                  onClick={handleNewSession}
                  className="h-[35px] w-[35px] border border-[#b6c2d1] rounded-[17px] flex items-center justify-center hover:bg-[#b6c2d1] hover:text-[#020305] transition-colors"
                  title="New Session"
                >
                  <img src="/images/img_addfilled.svg" alt="New Session" className="h-5 w-5" />
                </button>
                <button 
                  onClick={handleAskDox}
                  className="h-[35px] w-[35px] border border-[#b6c2d1] rounded-[17px] flex items-center justify-center hover:bg-[#b6c2d1] hover:text-[#020305] transition-colors"
                  title="Ask Dox"
                >
                  <img src="/images/img_folderfilled.svg" alt="Ask Dox" className="h-5 w-5" />
                </button>
                <button 
                  onClick={handleVoiceInput}
                  className="h-[35px] w-[35px] border border-[#b6c2d1] rounded-[17px] flex items-center justify-center hover:bg-[#b6c2d1] hover:text-[#020305] transition-colors"
                >
                  <img src="/images/img_microphone.svg" alt="Microphone" className="h-5 w-5" />
                </button>
                <div className="flex-1">
                  <InputField
                    placeholder="Type your message..."
                    value={messageInput}
                    onChange={(e) => setMessageInput(e.target.value)}
                    className="border-none bg-transparent text-[#f9fbfc] placeholder-[#8f99ad]"
                    onKeyPress={(e: React.KeyboardEvent) => {
                      if (e.key === 'Enter') {
                        handleSendMessage();
                      }
                    }}
                  />
                </div>
                <Button
                  onClick={handleSendMessage}
                  size="icon"
                  className="bg-[#00a9dd] rounded-[17px] h-[34px] w-[34px] hover:bg-[#0088bb] transition-colors"
                >
                  <img src="/images/img_keyboardreturnoutlined.svg" alt="Send" className="h-6 w-6" />
                </Button>
              </div>
            </div>
          </>
        );
      case 'contracts':
        return (
          <div className="flex-1 flex items-center justify-center">
            <div className="text-center">
              <img src="/images/img_folderfilled.svg" alt="Contracts" className="h-16 w-16 mx-auto mb-4 opacity-50" />
              <p className="text-[#8f99ad] text-lg">Contracts</p>
              <p className="text-[#8f99ad] text-sm mt-2">Contract management features coming soon</p>
            </div>
          </div>
        );
      case 'logs':
        return (
          <div className="flex-1 flex items-center justify-center">
            <div className="text-center">
              <img src="/images/img_filterlistfilled.svg" alt="Logs" className="h-16 w-16 mx-auto mb-4 opacity-50" />
              <p className="text-[#8f99ad] text-lg">Logs</p>
              <p className="text-[#8f99ad] text-sm mt-2">System logs and activity history</p>
            </div>
          </div>
        );
      default:
        return null;
    }
  };

  return (
    <div className="min-h-screen bg-[#020305] text-white">
      <Header 
        onSearch={handleSearch}
        isFullWidth={isFullWidth}
        onToggleFullWidth={handleToggleFullWidth}
      />
      
      <div className="flex h-[calc(100vh-80px)] p-6 gap-6">
        <Sidebar 
          onSectionSelect={handleSectionSelect}
          onFeedback={handleFeedback}
        />
        
        <main className="flex-1 bg-[#141923] rounded-2xl p-6 flex flex-col">
          {/* Tab Bar */}
          <TabBar 
            tabs={tabs}
            activeTab={activeTab}
            onTabChange={handleTabChange}
          />
          
          {/* Tab Content */}
          {renderTabContent()}
        </main>
      </div>
    </div>
  );
};

export default SwiperChatApplication;