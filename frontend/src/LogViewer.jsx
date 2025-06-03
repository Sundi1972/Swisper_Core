import { useState, useEffect, useRef } from 'react';

const LogViewer = () => {
  const [logs, setLogs] = useState([]);
  const [logLevel, setLogLevel] = useState('INFO');
  const [isConnected, setIsConnected] = useState(false);
  const [autoScroll, setAutoScroll] = useState(true);
  const [viewMode, setViewMode] = useState('flow');
  const wsRef = useRef(null);
  const logsEndRef = useRef(null);

  const logLevels = ['DEBUG', 'INFO', 'WARNING', 'ERROR'];

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

  const groupLogsBySession = (logs) => {
    const sessions = {};
    logs.forEach(log => {
      const sessionId = log.extra?.session_id || 'system';
      if (!sessions[sessionId]) {
        sessions[sessionId] = [];
      }
      sessions[sessionId].push(log);
    });
    return sessions;
  };

  const getComponentIcon = (logger) => {
    if (logger.includes('gateway')) return '🚪';
    if (logger.includes('orchestrator')) return '🎯';
    if (logger.includes('contract')) return '📋';
    if (logger.includes('haystack')) return '🔍';
    if (logger.includes('tool_adapter')) return '🛠️';
    if (logger.includes('httpx')) return '🌐';
    return '⚙️';
  };

  const getFlowDirection = (message) => {
    if (message.includes('Received') || message.includes('handling request') || message.includes('triggered')) {
      return '➡️ INPUT';
    }
    if (message.includes('response') || message.includes('output') || message.includes('Selected') || message.includes('confirmed')) {
      return '⬅️ OUTPUT';
    }
    if (message.includes('extracted') || message.includes('found') || message.includes('search')) {
      return '🔄 PROCESS';
    }
    return '📝 INFO';
  };

  const buildComponentFlow = (sessionLogs) => {
    const flow = [];
    sessionLogs.forEach((log, index) => {
      const component = log.logger.split('.').pop();
      const flowDirection = getFlowDirection(log.message);
      const nextLog = sessionLogs[index + 1];
      
      flow.push({
        ...log,
        component,
        flowDirection,
        hasNext: !!nextLog,
        nextComponent: nextLog ? nextLog.logger.split('.').pop() : null
      });
    });
    return flow;
  };

  const formatInputOutput = (log) => {
    const inputs = {};
    const outputs = {};
    
    if (log.extra) {
      if (log.extra.session_id) inputs.session_id = log.extra.session_id;
      if (log.extra.message_count) inputs.message_count = log.extra.message_count;
      if (log.extra.user_input) inputs.user_input = log.extra.user_input;
      if (log.extra.contract_query) inputs.contract_query = log.extra.contract_query;
      if (log.extra.rag_question) inputs.rag_question = log.extra.rag_question;
      if (log.extra.search_query) inputs.search_query = log.extra.search_query;
      
      if (log.extra.intent) outputs.intent = log.extra.intent;
      if (log.extra.confidence) outputs.confidence = log.extra.confidence;
      if (log.extra.criteria) outputs.criteria = log.extra.criteria;
      if (log.extra.product) outputs.product = log.extra.product;
      if (log.extra.response_preview) outputs.response_preview = log.extra.response_preview;
    }
    
    return { inputs, outputs };
  };

  const getComponentColor = (logger) => {
    if (logger.includes('gateway')) return 'border-blue-500 bg-blue-50';
    if (logger.includes('orchestrator')) return 'border-purple-500 bg-purple-50';
    if (logger.includes('contract')) return 'border-green-500 bg-green-50';
    if (logger.includes('haystack')) return 'border-yellow-500 bg-yellow-50';
    if (logger.includes('tool_adapter')) return 'border-orange-500 bg-orange-50';
    if (logger.includes('httpx')) return 'border-gray-500 bg-gray-50';
    return 'border-gray-400 bg-gray-50';
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
            
            <div className="flex items-center gap-2">
              <span className="text-sm text-gray-600">View:</span>
              <select
                value={viewMode}
                onChange={(e) => setViewMode(e.target.value)}
                className="px-2 py-1 border border-gray-300 rounded text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="flow">Flow Diagram</option>
                <option value="compact">Compact</option>
              </select>
            </div>
            
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
      <div className="bg-gray-900 text-gray-100 text-sm h-96 overflow-y-auto border-l border-r border-b border-gray-200 rounded-b-lg">
        <div className="p-4">
          {logs.length === 0 ? (
            <div className="text-gray-500 text-center py-8">
              No logs available. {!isConnected && 'Waiting for connection...'}
            </div>
          ) : (
            Object.entries(groupLogsBySession(logs)).map(([sessionId, sessionLogs]) => (
              <div key={sessionId} className="mb-6 border border-gray-700 rounded-lg">
                {/* Session Header */}
                <div className="bg-gray-800 px-3 py-2 rounded-t-lg border-b border-gray-700">
                  <span className="text-blue-400 font-semibold">
                    🔗 Session: {sessionId === 'system' ? 'System Operations' : sessionId.slice(0, 8)}...
                  </span>
                  <span className="text-gray-400 ml-2 text-xs">
                    ({sessionLogs.length} operations)
                  </span>
                </div>
                
                {/* Session Logs */}
                <div className="p-3">
                  {viewMode === 'flow' ? (
                    buildComponentFlow(sessionLogs).map((log, index) => {
                      const flowDirection = getFlowDirection(log.message);
                      const componentIcon = getComponentIcon(log.logger);
                      const componentColor = getComponentColor(log.logger);
                      const { inputs, outputs } = formatInputOutput(log);
                      
                      return (
                        <div key={index} className="mb-4">
                          <div className={`border-l-4 ${componentColor} rounded-r-lg p-3 shadow-sm`}>
                            <div className="flex items-center justify-between mb-2">
                              <div className="flex items-center gap-2">
                                <span className="text-gray-400 text-xs">
                                  {formatTimestamp(log.timestamp)}
                                </span>
                                <span className={`text-xs px-2 py-1 rounded ${
                                  log.level === 'ERROR' ? 'bg-red-900 text-red-200' :
                                  log.level === 'WARNING' ? 'bg-yellow-900 text-yellow-200' :
                                  log.level === 'INFO' ? 'bg-blue-900 text-blue-200' :
                                  'bg-gray-700 text-gray-300'
                                }`}>
                                  {log.level}
                                </span>
                                <span className="text-purple-400 text-sm font-semibold">
                                  {componentIcon} {log.component}
                                </span>
                                <span className={`text-xs px-2 py-1 rounded ${
                                  flowDirection.includes('INPUT') ? 'bg-green-900 text-green-200' :
                                  flowDirection.includes('OUTPUT') ? 'bg-orange-900 text-orange-200' :
                                  flowDirection.includes('PROCESS') ? 'bg-cyan-900 text-cyan-200' :
                                  'bg-gray-700 text-gray-300'
                                }`}>
                                  {flowDirection}
                                </span>
                              </div>
                            </div>
                            
                            <div className="text-gray-800 mb-3 font-medium">
                              {log.message}
                            </div>
                            
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                              {Object.keys(inputs).length > 0 && (
                                <div className="bg-green-50 border border-green-200 rounded p-3">
                                  <div className="flex items-center gap-2 mb-2">
                                    <span className="text-green-600 font-semibold text-sm">➡️ INPUTS</span>
                                  </div>
                                  <div className="space-y-1">
                                    {Object.entries(inputs).map(([key, value]) => (
                                      <div key={key} className="flex text-xs">
                                        <span className="text-green-700 font-medium min-w-0 flex-shrink-0 mr-2">
                                          {key}:
                                        </span>
                                        <span className="text-green-800 break-all">
                                          {typeof value === 'object' ? JSON.stringify(value) : String(value)}
                                        </span>
                                      </div>
                                    ))}
                                  </div>
                                </div>
                              )}
                              
                              {Object.keys(outputs).length > 0 && (
                                <div className="bg-orange-50 border border-orange-200 rounded p-3">
                                  <div className="flex items-center gap-2 mb-2">
                                    <span className="text-orange-600 font-semibold text-sm">⬅️ OUTPUTS</span>
                                  </div>
                                  <div className="space-y-1">
                                    {Object.entries(outputs).map(([key, value]) => (
                                      <div key={key} className="flex text-xs">
                                        <span className="text-orange-700 font-medium min-w-0 flex-shrink-0 mr-2">
                                          {key}:
                                        </span>
                                        <span className="text-orange-800 break-all">
                                          {typeof value === 'object' ? JSON.stringify(value) : String(value)}
                                        </span>
                                      </div>
                                    ))}
                                  </div>
                                </div>
                              )}
                            </div>
                            
                            {log.extra && Object.keys(log.extra).length > Object.keys(inputs).length + Object.keys(outputs).length && (
                              <div className="mt-3 bg-gray-100 border border-gray-200 rounded p-2">
                                <div className="text-gray-600 font-semibold text-xs mb-1">📊 Additional Context:</div>
                                <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                                  {Object.entries(log.extra).filter(([key]) => 
                                    !inputs[key] && !outputs[key]
                                  ).map(([key, value]) => (
                                    <div key={key} className="flex text-xs">
                                      <span className="text-gray-600 min-w-0 flex-shrink-0 mr-2">
                                        {key}:
                                      </span>
                                      <span className="text-gray-700 break-all">
                                        {typeof value === 'object' ? JSON.stringify(value) : String(value)}
                                      </span>
                                    </div>
                                  ))}
                                </div>
                              </div>
                            )}
                          </div>
                          
                          {log.hasNext && log.nextComponent !== log.component && (
                            <div className="flex justify-center my-2">
                              <div className="flex items-center gap-2 text-gray-500 text-sm">
                                <span>⬇️</span>
                                <span className="text-xs bg-gray-100 px-2 py-1 rounded">
                                  handoff to {getComponentIcon(log.nextComponent)} {log.nextComponent}
                                </span>
                                <span>⬇️</span>
                              </div>
                            </div>
                          )}
                        </div>
                      );
                    })
                  ) : (
                    sessionLogs.map((log, index) => {
                      const flowDirection = getFlowDirection(log.message);
                      const componentIcon = getComponentIcon(log.logger);
                      
                      return (
                        <div key={index} className="mb-3 border-l-2 border-gray-600 pl-4">
                          <div className="flex items-center gap-2 mb-1">
                            <span className="text-gray-400 text-xs">
                              {formatTimestamp(log.timestamp)}
                            </span>
                            <span className={`text-xs px-2 py-1 rounded ${
                              log.level === 'ERROR' ? 'bg-red-900 text-red-200' :
                              log.level === 'WARNING' ? 'bg-yellow-900 text-yellow-200' :
                              log.level === 'INFO' ? 'bg-blue-900 text-blue-200' :
                              'bg-gray-700 text-gray-300'
                            }`}>
                              {log.level}
                            </span>
                            <span className="text-purple-400 text-xs">
                              {componentIcon} {log.logger}
                            </span>
                            <span className={`text-xs px-2 py-1 rounded ${
                              flowDirection.includes('INPUT') ? 'bg-green-900 text-green-200' :
                              flowDirection.includes('OUTPUT') ? 'bg-orange-900 text-orange-200' :
                              flowDirection.includes('PROCESS') ? 'bg-cyan-900 text-cyan-200' :
                              'bg-gray-700 text-gray-300'
                            }`}>
                              {flowDirection}
                            </span>
                          </div>
                          
                          <div className="text-gray-100 mb-2">
                            {log.message}
                          </div>
                          
                          {log.extra && Object.keys(log.extra).length > 0 && (
                            <div className="bg-gray-800 rounded p-2 text-xs">
                              <div className="text-yellow-400 mb-1">📊 Context Data:</div>
                              <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                                {Object.entries(log.extra).map(([key, value]) => (
                                  <div key={key} className="flex">
                                    <span className="text-cyan-400 min-w-0 flex-shrink-0 mr-2">
                                      {key}:
                                    </span>
                                    <span className="text-gray-300 break-all">
                                      {typeof value === 'object' ? JSON.stringify(value) : String(value)}
                                    </span>
                                  </div>
                                ))}
                              </div>
                            </div>
                          )}
                        </div>
                      );
                    })
                  )}
                </div>
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
