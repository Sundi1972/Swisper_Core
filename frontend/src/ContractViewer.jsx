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
      const response = await fetch(`http://localhost:8000/contracts/current/${sessionId}`);
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
      <pre className="bg-gray-50 p-4 rounded-lg overflow-auto text-sm font-mono whitespace-pre-wrap">
        <code className="text-gray-800">{jsonString}</code>
      </pre>
    );
  };

  if (loading) {
    return (
      <div className="max-w-xl mx-auto p-4">
        <div className="text-center text-gray-600">Loading contract data...</div>
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
        <div className="bg-gray-50 border border-gray-200 rounded-lg p-8 text-center">
          <div className="text-gray-600 text-lg font-medium">No Contract</div>
          <div className="text-gray-500 text-sm mt-2">
            No active contract found for this session. Start a purchase to see contract details.
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-xl mx-auto p-4 space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-gray-800">Current Contract</h2>
        <button
          onClick={fetchContractData}
          disabled={loading}
          className="bg-blue-600 text-white px-3 py-1 rounded text-sm hover:bg-blue-700 disabled:opacity-50"
        >
          {loading ? 'Refreshing...' : 'Refresh'}
        </button>
      </div>
      
      <div className="bg-white border border-gray-200 rounded-lg">
        <div className="p-4 border-b border-gray-200">
          <div className="text-sm text-gray-600">
            <strong>State:</strong> {contractData.contract_data?.current_state || 'Unknown'}
          </div>
          <div className="text-sm text-gray-600 mt-1">
            <strong>Template:</strong> {contractData.contract_data?.template_path || 'Unknown'}
          </div>
        </div>
        
        <div className="p-4">
          <JsonDisplay data={contractData.contract_data} />
        </div>
      </div>
    </div>
  );
}
