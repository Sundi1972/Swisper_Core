import React, { useState, useEffect } from 'react';
import Modal from '../ui/Modal';
import { Button } from '../ui/Button';

interface Tool {
  name: string;
  description: string;
  parameters: any;
}

interface Contract {
  filename: string;
  contract_type: string;
  version: string;
  description: string;
  content: any;
}

interface SystemStatus {
  environment_variables: {
    USE_GPU: string;
    OPENAI_API_KEY: string;
    SEARCHAPI_API_KEY: string;
    SWISPER_MASTER_KEY: string;
  };
  system_status: {
    rag_available: boolean;
    t5_model_status: string;
    database_status: string;
    mcp_server_status: string;
  };
  performance_settings: {
    gpu_acceleration: boolean;
    model_type: string;
    max_tokens: number;
    inference_mode: string;
  };
  debug_logging: {
    log_level: string;
    websocket_logging: string;
    file_logging: string;
    console_logging: string;
  };
}

interface SettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
}

const SettingsModal: React.FC<SettingsModalProps> = ({ isOpen, onClose }) => {
  const [activeSection, setActiveSection] = useState<'tools' | 'contracts' | 'engine' | 'volatility'>('tools');
  const [tools, setTools] = useState<Tool[]>([]);
  const [contracts, setContracts] = useState<Contract[]>([]);
  const [systemStatus, setSystemStatus] = useState<SystemStatus | null>(null);
  const [selectedTool, setSelectedTool] = useState<Tool | null>(null);
  const [selectedContract, setSelectedContract] = useState<Contract | null>(null);
  const [loading, setLoading] = useState(false);
  const [volatilitySettings, setVolatilitySettings] = useState<{
    volatile_keywords: string[];
    semi_static_keywords: string[];
    static_keywords: string[];
  }>({
    volatile_keywords: [],
    semi_static_keywords: [],
    static_keywords: []
  });

  useEffect(() => {
    if (isOpen) {
      if (activeSection === 'tools') {
        fetchTools();
      } else if (activeSection === 'contracts') {
        fetchContracts();
      } else if (activeSection === 'engine') {
        fetchSystemStatus();
      } else if (activeSection === 'volatility') {
        fetchVolatilitySettings();
      }
    }
  }, [isOpen, activeSection]);

  const fetchTools = async () => {
    setLoading(true);
    try {
      const response = await fetch('/api/tools');
      const data = await response.json();
      setTools(Object.entries(data.tools || {}).map(([name, tool]: [string, any]) => ({
        name,
        description: tool.description,
        parameters: tool.parameters
      })));
    } catch (error) {
      console.error('Error fetching tools:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchContracts = async () => {
    setLoading(true);
    try {
      const response = await fetch('/api/contracts');
      const data = await response.json();
      setContracts(data.contracts || []);
    } catch (error) {
      console.error('Error fetching contracts:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchSystemStatus = async () => {
    setLoading(true);
    try {
      const response = await fetch('/api/system/status');
      const data = await response.json();
      setSystemStatus(data);
    } catch (error) {
      console.error('Error fetching system status:', error);
      setSystemStatus(null);
    } finally {
      setLoading(false);
    }
  };

  const fetchVolatilitySettings = async () => {
    setLoading(true);
    try {
      const response = await fetch('/api/volatility-settings');
      const data = await response.json();
      setVolatilitySettings(data.volatility_settings || {
        volatile_keywords: [],
        semi_static_keywords: [],
        static_keywords: []
      });
    } catch (error) {
      console.error('Error fetching volatility settings:', error);
    } finally {
      setLoading(false);
    }
  };

  const updateVolatilitySettings = async () => {
    setLoading(true);
    try {
      const response = await fetch('/api/volatility-settings', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(volatilitySettings)
      });
      if (response.ok) {
        console.log('Volatility settings updated successfully');
      }
    } catch (error) {
      console.error('Error updating volatility settings:', error);
    } finally {
      setLoading(false);
    }
  };

  const renderToolRegistry = () => (
    <div className="flex h-full">
      <div className="w-1/3 border-r border-[#8f99ad] p-4">
        <h3 className="text-md font-medium text-[#e5e7eb] mb-4">Available Tools</h3>
        {loading ? (
          <div className="text-[#8f99ad]">Loading tools...</div>
        ) : (
          <div className="space-y-2">
            {tools.map((tool) => (
              <button
                key={tool.name}
                onClick={() => setSelectedTool(tool)}
                className={`w-full text-left p-3 rounded-lg transition-colors ${
                  selectedTool?.name === tool.name
                    ? 'bg-[#8f99ad] text-[#141923]'
                    : 'hover:bg-[#1f2937] text-[#e5e7eb]'
                }`}
              >
                <div className="font-medium">{tool.name}</div>
                <div className="text-sm opacity-75 truncate">{tool.description}</div>
              </button>
            ))}
          </div>
        )}
      </div>
      <div className="w-2/3 p-4">
        {selectedTool ? (
          <div>
            <h4 className="text-lg font-medium text-[#e5e7eb] mb-2">{selectedTool.name}</h4>
            <p className="text-[#8f99ad] mb-4">{selectedTool.description}</p>
            <h5 className="text-md font-medium text-[#e5e7eb] mb-2">Parameters</h5>
            <pre className="bg-[#1f2937] p-3 rounded-lg text-sm text-[#e5e7eb] overflow-auto">
              {JSON.stringify(selectedTool.parameters, null, 2)}
            </pre>
          </div>
        ) : (
          <div className="text-[#8f99ad] text-center mt-8">
            Select a tool to view its details
          </div>
        )}
      </div>
    </div>
  );

  const renderContractRegistry = () => (
    <div className="flex h-full">
      <div className="w-1/3 border-r border-[#8f99ad] p-4">
        <h3 className="text-md font-medium text-[#e5e7eb] mb-4">Contract Templates</h3>
        {loading ? (
          <div className="text-[#8f99ad]">Loading contracts...</div>
        ) : (
          <div className="space-y-2">
            {contracts.map((contract) => (
              <button
                key={contract.filename}
                onClick={() => setSelectedContract(contract)}
                className={`w-full text-left p-3 rounded-lg transition-colors ${
                  selectedContract?.filename === contract.filename
                    ? 'bg-[#8f99ad] text-[#141923]'
                    : 'hover:bg-[#1f2937] text-[#e5e7eb]'
                }`}
              >
                <div className="font-medium">{contract.contract_type}</div>
                <div className="text-sm opacity-75">{contract.filename}</div>
                <div className="text-xs opacity-60 truncate">{contract.description}</div>
              </button>
            ))}
          </div>
        )}
      </div>
      <div className="w-2/3 p-4">
        {selectedContract ? (
          <div>
            <h4 className="text-lg font-medium text-[#e5e7eb] mb-2">{selectedContract.contract_type}</h4>
            <p className="text-[#8f99ad] mb-4">{selectedContract.description}</p>
            <h5 className="text-md font-medium text-[#e5e7eb] mb-2">YAML Content</h5>
            <pre className="bg-[#1f2937] p-3 rounded-lg text-sm text-[#e5e7eb] overflow-auto">
              {JSON.stringify(selectedContract.content, null, 2)}
            </pre>
          </div>
        ) : (
          <div className="text-[#8f99ad] text-center mt-8">
            Select a contract to view its YAML content
          </div>
        )}
      </div>
    </div>
  );

  const renderEngineConfig = () => (
    <div className="p-4">
      {loading ? (
        <div className="text-[#8f99ad]">Loading system status...</div>
      ) : systemStatus ? (
        <div className="space-y-6">
          <div>
            <h3 className="text-lg font-medium text-[#e5e7eb] mb-4">Environment Variables</h3>
            <div className="bg-[#1f2937] p-4 rounded-lg">
              <div className="grid grid-cols-2 gap-4">
                {systemStatus.environment_variables && Object.entries(systemStatus.environment_variables).map(([key, value]) => (
                  <div key={key} className="flex justify-between">
                    <span className="text-[#8f99ad]">{key}:</span>
                    <span className={`font-medium ${value === 'Set' || value === 'true' ? 'text-green-400' : 'text-red-400'}`}>
                      {value}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </div>

          <div>
            <h3 className="text-lg font-medium text-[#e5e7eb] mb-4">System Status</h3>
            <div className="bg-[#1f2937] p-4 rounded-lg">
              <div className="grid grid-cols-2 gap-4">
                {systemStatus.system_status && Object.entries(systemStatus.system_status).map(([key, value]) => (
                  <div key={key} className="flex justify-between">
                    <span className="text-[#8f99ad]">{key.replace(/_/g, ' ')}:</span>
                    <span className={`font-medium ${
                      typeof value === 'boolean' 
                        ? (value ? 'text-green-400' : 'text-red-400')
                        : 'text-[#e5e7eb]'
                    }`}>
                      {typeof value === 'boolean' ? (value ? 'Available' : 'Unavailable') : value}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </div>

          <div>
            <h3 className="text-lg font-medium text-[#e5e7eb] mb-4">Performance Settings</h3>
            <div className="bg-[#1f2937] p-4 rounded-lg">
              <div className="grid grid-cols-2 gap-4">
                {systemStatus.performance_settings && Object.entries(systemStatus.performance_settings).map(([key, value]) => (
                  <div key={key} className="flex justify-between">
                    <span className="text-[#8f99ad]">{key.replace(/_/g, ' ')}:</span>
                    <span className={`font-medium ${
                      typeof value === 'boolean' 
                        ? (value ? 'text-green-400' : 'text-yellow-400')
                        : 'text-[#e5e7eb]'
                    }`}>
                      {typeof value === 'boolean' ? (value ? 'Enabled' : 'Disabled') : value}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </div>

          <div>
            <h3 className="text-lg font-medium text-[#e5e7eb] mb-4">Debug/Logging Levels</h3>
            <div className="bg-[#1f2937] p-4 rounded-lg">
              <div className="grid grid-cols-2 gap-4">
                {systemStatus.debug_logging && Object.entries(systemStatus.debug_logging).map(([key, value]) => (
                  <div key={key} className="flex justify-between">
                    <span className="text-[#8f99ad]">{key.replace(/_/g, ' ')}:</span>
                    <span className="font-medium text-[#e5e7eb]">{value}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      ) : (
        <div className="text-[#8f99ad] text-center mt-8">
          Failed to load system status
        </div>
      )}
    </div>
  );

  const renderVolatilityConfig = () => (
    <div className="p-4">
      <div className="space-y-6">
        <div>
          <h3 className="text-lg font-medium text-[#e5e7eb] mb-4">Volatility Indicators</h3>
          <p className="text-sm text-[#8f99ad] mb-6">
            Configure keywords that help classify queries by information volatility for better intent routing.
          </p>
        </div>

        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-[#e5e7eb] mb-2">
              Volatile Keywords (Current/Time-sensitive information)
            </label>
            <textarea
              className="w-full p-3 bg-[#1f2937] border border-[#8f99ad] rounded-lg text-[#e5e7eb] focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              rows={3}
              value={volatilitySettings.volatile_keywords.join(', ')}
              onChange={(e) => setVolatilitySettings({
                ...volatilitySettings,
                volatile_keywords: e.target.value.split(',').map(k => k.trim()).filter(k => k)
              })}
              placeholder="latest, current, recent, today, now, ministers, government, CEO..."
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-[#e5e7eb] mb-2">
              Semi-static Keywords (Occasionally changing information)
            </label>
            <textarea
              className="w-full p-3 bg-[#1f2937] border border-[#8f99ad] rounded-lg text-[#e5e7eb] focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              rows={3}
              value={volatilitySettings.semi_static_keywords.join(', ')}
              onChange={(e) => setVolatilitySettings({
                ...volatilitySettings,
                semi_static_keywords: e.target.value.split(',').map(k => k.trim()).filter(k => k)
              })}
              placeholder="specs, specifications, features, iPhone, model, version..."
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-[#e5e7eb] mb-2">
              Static Keywords (Stable/Historical information)
            </label>
            <textarea
              className="w-full p-3 bg-[#1f2937] border border-[#8f99ad] rounded-lg text-[#e5e7eb] focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              rows={3}
              value={volatilitySettings.static_keywords.join(', ')}
              onChange={(e) => setVolatilitySettings({
                ...volatilitySettings,
                static_keywords: e.target.value.split(',').map(k => k.trim()).filter(k => k)
              })}
              placeholder="history, biography, born, capital, population, definition, explain..."
            />
          </div>

          <button
            onClick={updateVolatilitySettings}
            disabled={loading}
            className="w-full bg-blue-500 text-white py-2 px-4 rounded-lg hover:bg-blue-600 disabled:opacity-50"
          >
            {loading ? 'Updating...' : 'Update Volatility Settings'}
          </button>
        </div>
      </div>
    </div>
  );

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Settings">
      <div className="flex h-[600px]">
        <div className="w-48 border-r border-[#8f99ad] p-4">
          <nav className="space-y-2">
            <button
              onClick={() => setActiveSection('tools')}
              className={`w-full text-left p-3 rounded-lg transition-colors ${
                activeSection === 'tools'
                  ? 'bg-[#8f99ad] text-[#141923]'
                  : 'hover:bg-[#1f2937] text-[#e5e7eb]'
              }`}
            >
              Tool Registry
            </button>
            <button
              onClick={() => setActiveSection('contracts')}
              className={`w-full text-left p-3 rounded-lg transition-colors ${
                activeSection === 'contracts'
                  ? 'bg-[#8f99ad] text-[#141923]'
                  : 'hover:bg-[#1f2937] text-[#e5e7eb]'
              }`}
            >
              Contract Registry
            </button>
            <button
              onClick={() => setActiveSection('engine')}
              className={`w-full text-left p-3 rounded-lg transition-colors ${
                activeSection === 'engine'
                  ? 'bg-[#8f99ad] text-[#141923]'
                  : 'hover:bg-[#1f2937] text-[#e5e7eb]'
              }`}
            >
              Swisper Engine Config
            </button>
            <button
              onClick={() => setActiveSection('volatility')}
              className={`w-full text-left p-3 rounded-lg transition-colors ${
                activeSection === 'volatility'
                  ? 'bg-[#8f99ad] text-[#141923]'
                  : 'hover:bg-[#1f2937] text-[#e5e7eb]'
              }`}
            >
              Volatility Indicators
            </button>
          </nav>
        </div>

        <div className="flex-1">
          {activeSection === 'tools' && renderToolRegistry()}
          {activeSection === 'contracts' && renderContractRegistry()}
          {activeSection === 'engine' && renderEngineConfig()}
          {activeSection === 'volatility' && renderVolatilityConfig()}
        </div>
      </div>
    </Modal>
  );
};

export default SettingsModal;
