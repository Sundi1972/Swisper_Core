import { useState, useEffect, useRef } from 'react';

const LogViewer = () => {
  const [logs, setLogs] = useState([]);
  const [logLevel, setLogLevel] = useState('INFO');
  const [isConnected, setIsConnected] = useState(false);
  const [autoScroll, setAutoScroll] = useState(true);
  const wsRef = useRef(null);
  const logsEndRef = useRef(null);

  const logLevels = ['DEBUG', 'INFO', 'WARNING', 'ERROR'];
  
  const logLevelColors = {
    DEBUG: 'text-gray-600',
    INFO: 'text-blue-600',
    WARNING: 'text-yellow-600',
    ERROR: 'text-red-600'
  };

  useEffect(() => {
    connectWebSocket();
    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, []);

  useEffect(() => {
    if (autoScroll && logsEndRef.current) {
      logsEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [logs, autoScroll]);

  const connectWebSocket = () => {
    try {
      const wsUrl = `ws://localhost:8000/ws/logs?level=${logLevel}`;
      wsRef.current = new WebSocket(wsUrl);
      
      wsRef.current.onopen = () => {
        setIsConnected(true);
        console.log('WebSocket connected for logs');
      };
      
      wsRef.current.onmessage = (event) => {
        const logEntry = JSON.parse(event.data);
        if (logEntry.type !== 'ping') {
          setLogs(prev => [...prev, logEntry]);
        }
      };
      
      wsRef.current.onclose = () => {
        setIsConnected(false);
        console.log('WebSocket disconnected');
        setTimeout(connectWebSocket, 3000);
      };
      
      wsRef.current.onerror = (error) => {
        console.error('WebSocket error:', error);
        setIsConnected(false);
      };
    } catch (error) {
      console.error('Failed to connect WebSocket:', error);
      setIsConnected(false);
    }
  };

  const handleLogLevelChange = (newLevel) => {
    setLogLevel(newLevel);
    setLogs([]); // Clear existing logs when changing level
    
    if (wsRef.current) {
      wsRef.current.close();
    }
    
    setTimeout(() => {
      connectWebSocket();
    }, 100);
  };

  const refreshLogs = async () => {
    try {
      const response = await fetch(`http://localhost:8000/api/logs?level=${logLevel}&limit=100`);
      if (response.ok) {
        const data = await response.json();
        setLogs(data.logs || []);
      }
    } catch (error) {
      console.error('Failed to refresh logs:', error);
    }
  };

  const clearLogs = () => {
    setLogs([]);
  };

  const formatTimestamp = (timestamp) => {
    return new Date(timestamp).toLocaleTimeString('en-US', {
      hour12: false,
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      fractionalSecondDigits: 3
    });
  };

  return (
    <div className="max-w-6xl mx-auto">
      {/* Header Controls */}
      <div className="bg-gray-50 border border-gray-200 rounded-t-lg p-4">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2">
              <span className="text-sm font-medium text-gray-700">Log Level:</span>
              <select
                value={logLevel}
                onChange={(e) => handleLogLevelChange(e.target.value)}
                className="px-3 py-1 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                {logLevels.map(level => (
                  <option key={level} value={level}>{level}</option>
                ))}
              </select>
            </div>
            
            <div className="flex items-center gap-2">
              <span className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-500' : 'bg-red-500'}`}></span>
              <span className="text-sm text-gray-600">
                {isConnected ? 'Connected' : 'Disconnected'}
              </span>
            </div>
          </div>
          
          <div className="flex items-center gap-2">
            <label className="flex items-center gap-2 text-sm text-gray-600">
              <input
                type="checkbox"
                checked={autoScroll}
                onChange={(e) => setAutoScroll(e.target.checked)}
                className="rounded"
              />
              Auto-scroll
            </label>
            
            <button
              onClick={refreshLogs}
              className="px-3 py-1 bg-blue-600 text-white text-sm rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              Refresh
            </button>
            
            <button
              onClick={clearLogs}
              className="px-3 py-1 bg-gray-600 text-white text-sm rounded-md hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-gray-500"
            >
              Clear
            </button>
          </div>
        </div>
      </div>

      {/* Log Display */}
      <div className="bg-black text-green-400 font-mono text-sm h-96 overflow-y-auto border-l border-r border-b border-gray-200 rounded-b-lg">
        <div className="p-4">
          {logs.length === 0 ? (
            <div className="text-gray-500 text-center py-8">
              No logs available. {!isConnected && 'Waiting for connection...'}
            </div>
          ) : (
            logs.map((log, index) => (
              <div key={index} className="mb-1 break-words">
                <span className="text-gray-400">
                  {formatTimestamp(log.timestamp)}
                </span>
                <span className={`ml-2 font-semibold ${logLevelColors[log.level] || 'text-white'}`}>
                  [{log.level}]
                </span>
                <span className="text-cyan-400 ml-2">
                  {log.logger}:
                </span>
                <span className="ml-2 text-green-400">
                  {log.message}
                </span>
                {log.extra && (
                  <div className="ml-8 text-yellow-400 text-xs">
                    {JSON.stringify(log.extra, null, 2)}
                  </div>
                )}
              </div>
            ))
          )}
          <div ref={logsEndRef} />
        </div>
      </div>
      
      {/* Footer Info */}
      <div className="text-xs text-gray-500 mt-2 text-center">
        Showing {logs.length} log entries at {logLevel} level and above
      </div>
    </div>
  );
};

export default LogViewer;
