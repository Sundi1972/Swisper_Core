import { useState, useEffect, forwardRef, useImperativeHandle } from 'react';
import { Button } from './components/ui/Button';
import InputField from './components/ui/InputField';

const SwisperChat = forwardRef((props, ref) => {
  const [messages, setMessages] = useState([
    { role: "assistant", content: "Hi, how can I help you today?" }
  ]);
  const [input, setInput] = useState("");
  const [sessionId, setSessionId] = useState(null);
  const [loading, setLoading] = useState(false);

  // Persistent session ID using localStorage
  useEffect(() => {
    let sid = localStorage.getItem("swisper_session_id");
    if (!sid) {
      sid = crypto.randomUUID();
      localStorage.setItem("swisper_session_id", sid);
    }
    setSessionId(sid);
  }, []);

  useEffect(() => {
    if (sessionId) {
      const savedMessages = localStorage.getItem(`chat_history_${sessionId}`);
      if (savedMessages) {
        try {
          const parsedMessages = JSON.parse(savedMessages);
          setMessages(parsedMessages);
        } catch (e) {
          console.error('Failed to parse saved messages:', e);
        }
      }
    }
  }, [sessionId]);

  useEffect(() => {
    if (sessionId && messages.length > 1) {
      localStorage.setItem(`chat_history_${sessionId}`, JSON.stringify(messages));
    }
  }, [messages, sessionId]);

  const handleSend = async () => {
    if (!input.trim() || !sessionId) return;

    const updatedMessages = [...messages, { role: "user", content: input }];
    setMessages(updatedMessages);
    setInput("");
    setLoading(true);

    try {
      const response = await fetch("http://localhost:8000/chat", { // MODIFIED URL
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({ messages: updatedMessages, session_id: sessionId })
      });

      const data = await response.json();
      if (data.reply) {
        setMessages(prev => [...prev, { role: "assistant", content: data.reply }]);
      }
    } catch (err) {
      setMessages(prev => [...prev, { role: "assistant", content: "Something went wrong." }]);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter") handleSend();
  };

  const handleNewSession = () => {
    const newSessionId = crypto.randomUUID();
    localStorage.setItem("swisper_session_id", newSessionId);
    setSessionId(newSessionId);
    
    setMessages([{ role: "assistant", content: "Hi, how can I help you today?" }]);
    setInput("");
  };

  const handleAskDocs = async () => {
    const ragQuestion = "#rag What is Swisper?";
    const originalInput = input; 
    setInput(ragQuestion); 
    
    const updatedMessagesWithRag = [...messages, { role: "user", content: ragQuestion }];
    setMessages(updatedMessagesWithRag);
    setLoading(true);

    try {
      const response = await fetch("http://localhost:8000/chat", {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({ messages: updatedMessagesWithRag, session_id: sessionId })
      });

      const data = await response.json();
      if (data.reply) {
        setMessages(prev => [...prev, { role: "assistant", content: data.reply }]);
      }
    } catch (err) {
      setMessages(prev => [...prev, { role: "assistant", content: "Something went wrong with RAG query." }]);
    } finally {
      setLoading(false);
      setInput(originalInput);
    }
  };

  const handleVoiceInput = () => {
    console.log('Voice input activated');
  };

  const handleAddAction = () => {
    console.log('Add action triggered');
  };


  return (
    <div className="flex-1 flex flex-col h-full">
      <div className="flex items-center mb-6">
        <div className="flex items-center bg-transparent rounded-lg px-3 py-2">
          <span className="text-[#b6c2d1] text-base mr-3">Swisper AI</span>
          <svg className="h-6 w-6 text-[#b6c2d1]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
          </svg>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto space-y-6 mb-6">
        {messages.map((msg, i) => (
          <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div className={`max-w-[492px] ${
              msg.role === 'user' 
                ? 'bg-[#141923] rounded-lg p-4' 
                : 'bg-[#222834] rounded-2xl p-4 shadow-[0px_2px_1px_#00000033]'
            }`}>
              <p className={`text-sm leading-5 mb-2 ${
                msg.role === 'user' ? 'text-[#f9fbfc]' : 'text-[#f9fbfc]'
              }`} style={{ whiteSpace: 'pre-line' }}>
                {msg.content}
              </p>
            </div>
          </div>
        ))}
      </div>

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
            <svg className="h-5 w-5 text-[#b6c2d1]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
            </svg>
          </button>
          <button 
            onClick={handleAskDocs}
            className="h-[35px] w-[35px] border border-[#b6c2d1] rounded-[17px] flex items-center justify-center hover:bg-[#b6c2d1] hover:text-[#020305] transition-colors"
            title="Ask Docs"
          >
            <svg className="h-5 w-5 text-[#b6c2d1]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
          </button>
          <button 
            onClick={handleVoiceInput}
            className="h-[35px] w-[35px] border border-[#b6c2d1] rounded-[17px] flex items-center justify-center hover:bg-[#b6c2d1] hover:text-[#020305] transition-colors"
            title="Voice Input"
          >
            <svg className="h-5 w-5 text-[#b6c2d1]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" />
            </svg>
          </button>
          <div className="flex-1">
            <InputField
              placeholder="Type your message..."
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && handleSend()}
              className="border-none bg-transparent text-[#f9fbfc] placeholder-[#8f99ad]"
              disabled={loading}
            />
          </div>
          <Button
            onClick={handleSend}
            disabled={loading}
            size="icon"
            className="bg-[#00a9dd] rounded-[17px] h-[34px] w-[34px] hover:bg-[#0088bb] transition-colors"
          >
            <svg className="h-6 w-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
            </svg>
          </Button>
        </div>
      </div>
    </div>
  );
});

SwisperChat.displayName = 'SwisperChat';

export default SwisperChat;
