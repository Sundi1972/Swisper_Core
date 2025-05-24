import { useState, useEffect } from 'react';

export default function SwisperChat() {
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
      <div className="bg-gray-100 rounded-lg p-4 h-[60vh] overflow-y-auto">
        {messages.map((msg, i) => (
          <div key={i} className={`text-sm mb-2 ${msg.role === 'user' ? 'text-right' : 'text-left'}`}>
            <span className="font-semibold">{msg.role === 'user' ? 'You' : 'Swisper'}:</span> {msg.content}
          </div>
        ))}
      </div>

      <div className="flex gap-2">
        <input
          className="flex-1 border border-gray-300 rounded px-3 py-2"
          placeholder="Type your message..."
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={loading}
        />
        <button
          onClick={handleSend}
          disabled={loading}
          className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700"
        >
          Send
        </button>
        <button
          onClick={handleAskDocs}
          disabled={loading}
          className="bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700"
          title="Sends the query '#rag What is Swisper?'"
        >
          Ask Docs: What is Swisper?
        </button>
      </div>
    </div>
  );
}