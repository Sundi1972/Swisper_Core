import { useState, useEffect } from 'react';

export default function ContractViewer() {
  const [contractData, setContractData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [sessionId, setSessionId] = useState(null);

  useEffect(() => {
    const sid = localStorage.getItem("swisper_session_id");
    if (sid) {
      setSessionId(sid);
    } else {
      setError("No session ID found");
      setLoading(false);
    }
  }, []);

  const fetchContractData = async () => {
    if (!sessionId) return;
    
    setLoading(true);
    setError(null);
    
    try {
      const response = await fetch(`${__API_BASE_URL__}/contracts/current/${sessionId}`);
      const data = await response.json();
      
      if (!response.ok) {
        throw new Error(data.detail || 'Failed to fetch contract data');
      }
      
      setContractData(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (sessionId) {
      fetchContractData();
    }
  }, [sessionId]);


  const JsonDisplay = ({ data }) => {
    const jsonString = JSON.stringify(data, null, 2);
    
    return (
      <pre className="bg-chat-message p-4 rounded-lg overflow-auto text-sm font-mono whitespace-pre-wrap">
        <code className="text-chat-text">{jsonString}</code>
      </pre>
    );
  };

  if (loading) {
    return (
      <div className="max-w-xl mx-auto p-4">
        <div className="text-center text-chat-secondary">Loading contract data...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="max-w-xl mx-auto p-4">
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <div className="text-red-800 font-medium">Error loading contract data</div>
          <div className="text-red-600 text-sm mt-1">{error}</div>
          <button
            onClick={fetchContractData}
            className="mt-2 bg-red-600 text-white px-3 py-1 rounded text-sm hover:bg-red-700"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  if (!contractData?.has_contract) {
    return (
      <div className="max-w-xl mx-auto p-4">
        <div className="bg-chat-message border border-chat-muted rounded-lg p-8 text-center">
          <div className="text-chat-secondary text-lg font-medium">No Contract</div>
          <div className="text-chat-muted text-sm mt-2">
            No active contract found for this session. Start a purchase to see contract details.
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto p-4 space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-chat-text">Current Contract</h2>
        <button
          onClick={fetchContractData}
          disabled={loading}
          className="bg-chat-accent text-white px-3 py-1 rounded text-sm hover:bg-chat-accent/80 disabled:opacity-50"
        >
          {loading ? 'Refreshing...' : 'Refresh'}
        </button>
      </div>
      
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="bg-chat-background border border-chat-muted rounded-lg">
          <div className="p-4 border-b border-chat-muted">
            <h3 className="text-md font-semibold text-chat-text">Contract Data</h3>
            <div className="text-sm text-chat-secondary mt-2">
              <strong>State:</strong> {contractData.contract_data?.current_state || 'Unknown'}
            </div>
            <div className="text-sm text-chat-secondary mt-1">
              <strong>Template:</strong> {contractData.contract_data?.template_path || 'Unknown'}
            </div>
          </div>
          
          <div className="p-4">
            <JsonDisplay data={contractData.contract_data} />
          </div>
        </div>

        {contractData.context && (
          <div className="bg-chat-background border border-chat-muted rounded-lg">
            <div className="p-4 border-b border-chat-muted">
              <h3 className="text-md font-semibold text-chat-text">SwisperContext</h3>
              <div className="text-sm text-chat-secondary mt-2">
                <strong>Session:</strong> {contractData.context.session_id}
              </div>
              <div className="text-sm text-chat-secondary mt-1">
                <strong>Status:</strong> {contractData.context.contract_status}
              </div>
              <div className="text-sm text-chat-secondary mt-1">
                <strong>Created:</strong> {new Date(contractData.context.created_at).toLocaleString()}
              </div>
              {contractData.context.updated_at && (
                <div className="text-sm text-chat-secondary mt-1">
                  <strong>Updated:</strong> {new Date(contractData.context.updated_at).toLocaleString()}
                </div>
              )}
            </div>
            
            <div className="p-4">
              <JsonDisplay data={contractData.context} />
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
