import { useState, useEffect, forwardRef, useImperativeHandle, useRef } from 'react';
import { Button } from './components/ui/Button';
import InputField from './components/ui/InputField';
import ReactMarkdown from 'react-markdown';
import rehypeHighlight from 'rehype-highlight';
import 'highlight.js/styles/github-dark.css';

const SwisperChat = forwardRef((props, ref) => {
  const [messages, setMessages] = useState([
    { role: "assistant", content: "Hi, how can I help you today?" }
  ]);
  const [input, setInput] = useState("");
  const [sessionId, setSessionId] = useState(null);
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef(null);

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

  useEffect(() => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages]);

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
    } catch {
      setMessages(prev => [...prev, { role: "assistant", content: "Something went wrong." }]);
    } finally {
      setLoading(false);
    }
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
    } catch {
      setMessages(prev => [...prev, { role: "assistant", content: "Something went wrong with RAG query." }]);
    } finally {
      setLoading(false);
      setInput(originalInput);
    }
  };

  const handleVoiceInput = () => {
    console.log('Voice mode activated');
  };

  const handleAddFile = () => {
    console.log('Add file triggered');
  };

  useImperativeHandle(ref, () => ({
    handleNewSession,
    getSessionId: () => sessionId
  }));


  return (
    <div className="flex flex-col h-full max-h-[calc(100vh-200px)]">
      <div className="flex items-center mb-6 flex-shrink-0">
        <div className="flex items-center bg-transparent rounded-lg px-3 py-2">
          <span className="text-[#b6c2d1] text-base mr-3">Swisper AI</span>
          <svg className="h-6 w-6 text-[#b6c2d1]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
          </svg>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto space-y-6 mb-20 min-h-0">
        {messages.map((msg, i) => (
          <div key={i} className={`w-3/4 ${msg.role === 'user' ? 'ml-auto' : 'ml-0'}`}>
            <div className={`${
              msg.role === 'user' 
                ? 'bg-[#141923] rounded-lg p-4' 
                : 'bg-[#222834] rounded-2xl p-4 shadow-[0px_2px_1px_#00000033]'
            }`}>
              <div className={`text-sm leading-5 mb-2 ${
                msg.role === 'user' ? 'text-[#f9fbfc]' : 'text-[#f9fbfc]'
              }`}>
                {msg.role === 'assistant' ? (
                  <ReactMarkdown
                    rehypePlugins={[rehypeHighlight]}
                    components={{
                      code: ({inline, className, children, ...props}) => {
                        return !inline ? (
                          <pre className="bg-[#1a1a1a] rounded-lg p-3 overflow-x-auto">
                            <code className={className} {...props}>
                              {children}
                            </code>
                          </pre>
                        ) : (
                          <code className="bg-[#1a1a1a] px-1 py-0.5 rounded text-sm" {...props}>
                            {children}
                          </code>
                        );
                      },
                      p: ({children}) => <p className="mb-2 last:mb-0">{children}</p>,
                      ul: ({children}) => <ul className="list-disc list-inside mb-2 space-y-1">{children}</ul>,
                      ol: ({children}) => <ol className="list-decimal list-inside mb-2 space-y-1">{children}</ol>,
                      li: ({children}) => <li className="text-[#f9fbfc]">{children}</li>,
                      h1: ({children}) => <h1 className="text-lg font-bold mb-2 text-[#f9fbfc]">{children}</h1>,
                      h2: ({children}) => <h2 className="text-base font-bold mb-2 text-[#f9fbfc]">{children}</h2>,
                      h3: ({children}) => <h3 className="text-sm font-bold mb-2 text-[#f9fbfc]">{children}</h3>,
                      strong: ({children}) => <strong className="font-bold text-[#f9fbfc]">{children}</strong>,
                      em: ({children}) => <em className="italic text-[#f9fbfc]">{children}</em>
                    }}
                  >
                    {msg.content}
                  </ReactMarkdown>
                ) : (
                  <p style={{ whiteSpace: 'pre-line' }}>{msg.content}</p>
                )}
              </div>
            </div>
          </div>
        ))}
        <div ref={messagesEndRef} />
      </div>

      <div className="bg-[#020305] rounded-lg p-5 flex-shrink-0 sticky bottom-8">
        <p className="text-[#8f99ad] text-sm mb-4">How can I help?</p>
        <div className="flex items-center space-x-3">
          <button 
            onClick={handleAddFile}
            className="h-[35px] w-[35px] border border-[#b6c2d1] rounded-[17px] flex items-center justify-center hover:bg-[#b6c2d1] hover:text-[#020305] transition-colors"
            title="Add File"
          >
            <svg className="h-5 w-5 text-[#b6c2d1]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.172 7l-6.586 6.586a2 2 0 102.828 2.828l6.414-6.586a4 4 0 00-5.656-5.656l-6.415 6.585a6 6 0 108.486 8.486L20.5 13" />
            </svg>
          </button>
          <button 
            onClick={handleAskDocs}
            className="h-[35px] w-[35px] border border-[#b6c2d1] rounded-[17px] flex items-center justify-center hover:bg-[#b6c2d1] hover:text-[#020305] transition-colors"
            title="Test RAG"
          >
            <svg className="h-5 w-5 text-[#b6c2d1]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
          </button>
          <button 
            onClick={handleVoiceInput}
            className="h-[35px] w-[35px] border border-[#b6c2d1] rounded-[17px] flex items-center justify-center hover:bg-[#b6c2d1] hover:text-[#020305] transition-colors"
            title="Voice Mode"
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
