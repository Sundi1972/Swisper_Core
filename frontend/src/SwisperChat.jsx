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
    // Temporarily set the input, then call handleSend, then restore input
    // This is a simple way to reuse the existing handleSend logic.
    const originalInput = input; 
    setInput(ragQuestion); 
    
    // We need to ensure handleSend uses the updated input value.
    // Since setInput is async, we pass the value directly to a modified/new send function
    // For simplicity here, we'll assume handleSend will pick up the new 'input' state
    // or we create a version of handleSend that takes content.
    // Let's make a direct call by simulating the state update for `handleSend`.
    
    // Simulate messages update that handleSend expects
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
      setInput(originalInput); // Restore original input if any
    }
  };


  return (
    <div className="max-w-xl mx-auto p-4 space-y-4 font-sans">
      <div className="bg-chat-message rounded-lg p-4 h-[60vh] overflow-y-auto">
        {messages.map((msg, i) => (
          <div key={i} className={`text-sm mb-2 ${msg.role === 'user' ? 'text-right' : 'text-left'}`}>
            <span className="font-semibold">{msg.role === 'user' ? 'You' : 'Swisper'}:</span> {msg.content}
          </div>
        ))}
      </div>

      <div className="flex gap-2 mt-4">
        <InputField
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyPress={(e) => e.key === 'Enter' && handleSend()}
          placeholder="Type your message..."
          className="flex-1"
          disabled={loading}
        />
        <Button
          onClick={handleSend}
          disabled={loading}
          variant="fill"
          color="primary"
          size="xs"
        >
          {loading ? 'Sending...' : 'Send'}
        </Button>
      </div>
      
      <div className="flex gap-2 mt-2">
        <Button
          onClick={handleNewSession}
          variant="outline"
          color="secondary"
          size="xs"
          disabled={loading}
        >
          New Session
        </Button>
        <Button
          onClick={handleAskDocs}
          variant="outline"
          color="secondary"
          size="xs"
          disabled={loading}
        >
          Ask Docs
        </Button>
      </div>
    </div>
  );
});

SwisperChat.displayName = 'SwisperChat';

export default SwisperChat;
