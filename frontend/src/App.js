import React, { useState, useEffect } from "react";
import "./App.css";
import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

function App() {
  const [keywords, setKeywords] = useState(['crypto trading', 'day trading']);
  const [maxVideos, setMaxVideos] = useState(2000);
  const [maxChannels, setMaxChannels] = useState(500);
  const [subscriberMin, setSubscriberMin] = useState(10000);
  const [subscriberMax, setSubscriberMax] = useState(1000000);
  const [contentFrequencyMin, setContentFrequencyMin] = useState(0.14);
  const [contentFrequencyMax, setContentFrequencyMax] = useState(2.0);
  const [processing, setProcessing] = useState(false);
  const [status, setStatus] = useState(null);
  const [currentStatusId, setCurrentStatusId] = useState(null);
  const [mainLeads, setMainLeads] = useState([]);
  const [noEmailLeads, setNoEmailLeads] = useState([]);
  const [selectedTab, setSelectedTab] = useState('generator');
  
  // Monitoring dashboard state
  const [performanceMetrics, setPerformanceMetrics] = useState(null);
  const [monitoringLoading, setMonitoringLoading] = useState(false);

  // Poll for status updates
  useEffect(() => {
    let interval;
    if (currentStatusId && processing) {
      interval = setInterval(async () => {
        try {
          const response = await axios.get(`${API}/lead-generation/status/${currentStatusId}`);
          setStatus(response.data);
          
          if (response.data.status === 'completed' || response.data.status === 'failed') {
            setProcessing(false);
            loadLeads();
          }
        } catch (error) {
          console.error('Error polling status:', error);
        }
      }, 3000);
    }
    
    return () => {
      if (interval) clearInterval(interval);
    };
  }, [currentStatusId, processing]);

  const startLeadGeneration = async () => {
    try {
      setProcessing(true);
      setStatus(null);
      
      const response = await axios.post(`${API}/lead-generation/start`, {
        keywords,
        max_videos_per_keyword: maxVideos,
        max_channels: maxChannels,
        subscriber_min: subscriberMin,
        subscriber_max: subscriberMax,
        content_frequency_min: contentFrequencyMin,
        content_frequency_max: contentFrequencyMax
      });
      
      setCurrentStatusId(response.data.id);
      setStatus(response.data);
    } catch (error) {
      console.error('Error starting lead generation:', error);
      setProcessing(false);
      alert('Failed to start lead generation. Please check the console for details.');
    }
  };

  const loadLeads = async () => {
    try {
      const [mainResponse, noEmailResponse] = await Promise.all([
        axios.get(`${API}/leads/main`),
        axios.get(`${API}/leads/no-email`)
      ]);
      
      setMainLeads(mainResponse.data);
      setNoEmailLeads(noEmailResponse.data);
    } catch (error) {
      console.error('Error loading leads:', error);
    }
  };

  const addEmailToLead = async (channelId, email) => {
    try {
      await axios.post(`${API}/leads/add-email/${channelId}?email=${encodeURIComponent(email)}`);
      alert('Email added successfully! Client outreach will be sent and channel moved to main leads.');
      loadLeads();
    } catch (error) {
      console.error('Error adding email:', error);
      alert('Failed to add email. Please try again.');
    }
  };

  const handleKeywordChange = (index, value) => {
    const newKeywords = [...keywords];
    newKeywords[index] = value;
    setKeywords(newKeywords);
  };

  const addKeyword = () => {
    setKeywords([...keywords, '']);
  };

  const removeKeyword = (index) => {
    if (keywords.length > 1) {
      setKeywords(keywords.filter((_, i) => i !== index));
    }
  };

  useEffect(() => {
    loadLeads();
  }, []);

  const LeadCard = ({ lead, showEmailInput = false }) => {
    const [emailInput, setEmailInput] = useState('');
    
    return (
      <div className="bg-white rounded-lg shadow-md p-6 border border-gray-200 hover:shadow-lg transition-shadow">
        <div className="flex items-start justify-between mb-4">
          <div>
            <h3 className="text-lg font-semibold text-gray-800 mb-1">
              {lead.channel_title}
            </h3>
            <p className="text-sm text-gray-600">
              👥 {lead.subscriber_count?.toLocaleString()} subscribers • 📹 {lead.video_count} videos
              {lead.content_frequency_weekly && (
                <span> • 📅 {lead.content_frequency_weekly} videos/week</span>
              )}
            </p>
          </div>
          <div className="flex flex-col items-end space-y-1">
            <span className={`px-2 py-1 text-xs rounded-full font-medium ${
              lead.email_status === 'found' ? 'bg-green-100 text-green-800' : 
              lead.email_status === 'manually_added' ? 'bg-blue-100 text-blue-800' :
              'bg-red-100 text-red-800'
            }`}>
              {lead.email_status === 'found' ? '✅ Email Found' :
               lead.email_status === 'manually_added' ? '📝 Manual Email' : 
               '❌ No Email'}
            </span>
            {lead.email_sent_status && (
              <span className={`px-2 py-1 text-xs rounded-full font-medium ${
                lead.email_sent_status === 'sent' ? 'bg-green-100 text-green-800' : 
                lead.email_sent_status === 'failed' ? 'bg-red-100 text-red-800' :
                'bg-gray-100 text-gray-800'
              }`}>
                {lead.email_sent_status === 'sent' ? '✉️ Outreach Sent' : 
                 lead.email_sent_status === 'failed' ? '❌ Send Failed' : 
                 '⏳ Pending'}
              </span>
            )}
          </div>
        </div>
        
        <div className="space-y-2 text-sm text-gray-600">
          <p><strong>🔗 Channel:</strong> 
            <a href={lead.channel_url} target="_blank" rel="noopener noreferrer" 
               className="text-blue-500 hover:underline ml-1">
              View on YouTube
            </a>
          </p>
          
          {lead.email && (
            <p><strong>📧 Email:</strong> <code className="bg-gray-100 px-2 py-1 rounded text-xs">{lead.email}</code></p>
          )}
          
          {lead.latest_video_title && (
            <p><strong>🎬 Latest Video:</strong> {lead.latest_video_title}</p>
          )}
          
          {lead.keywords_found_in?.length > 0 && (
            <p><strong>🏷️ Keywords:</strong> 
              <span className="ml-1">
                {lead.keywords_found_in.map((keyword, idx) => (
                  <span key={idx} className="inline-block bg-blue-100 text-blue-800 text-xs px-2 py-1 rounded mr-1">
                    {keyword}
                  </span>
                ))}
              </span>
            </p>
          )}
          
          {lead.top_comment && (
            <div className="bg-gray-50 p-3 rounded border-l-4 border-blue-400">
              <p className="text-xs font-medium text-gray-700">💬 Top Comment:</p>
              <p className="text-xs italic text-gray-600 mt-1">
                "{lead.top_comment}" 
                {lead.comment_author && <span className="font-medium"> - {lead.comment_author}</span>}
              </p>
            </div>
          )}
          
          {lead.email_subject && (
            <div className="bg-green-50 p-3 rounded border-l-4 border-green-400">
              <p className="text-xs font-medium text-green-700">✉️ Generated Outreach Subject:</p>
              <p className="text-xs text-green-600 mt-1 font-medium">{lead.email_subject}</p>
            </div>
          )}
        </div>
        
        {showEmailInput && (
          <div className="mt-4 p-3 bg-yellow-50 rounded border border-yellow-200">
            <p className="text-xs text-yellow-700 mb-2">📧 Add email to send client outreach:</p>
            <div className="flex space-x-2">
              <input
                type="email"
                placeholder="Enter email address"
                value={emailInput}
                onChange={(e) => setEmailInput(e.target.value)}
                className="flex-1 px-3 py-2 border border-gray-300 rounded-md text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
              <button
                onClick={() => {
                  if (emailInput.trim()) {
                    addEmailToLead(lead.channel_id, emailInput.trim());
                    setEmailInput('');
                  }
                }}
                className="px-4 py-2 bg-blue-500 text-white rounded-md hover:bg-blue-600 text-sm font-medium transition-colors"
              >
                Send Outreach
              </button>
            </div>
          </div>
        )}
        
        <div className="mt-3 flex justify-between items-center text-xs text-gray-400 border-t pt-3">
          <span>📅 Discovered: {new Date(lead.discovery_timestamp).toLocaleDateString()}</span>
          {lead.processing_timestamp && (
            <span>⚡ Processed: {new Date(lead.processing_timestamp).toLocaleDateString()}</span>
          )}
        </div>
      </div>
    );
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <h1 className="text-xl font-bold text-gray-900">
                  🎯 YouTube Client Lead Generation Platform
                </h1>
              </div>
            </div>
            <div className="flex space-x-4">
              <button
                onClick={() => setSelectedTab('generator')}
                className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
                  selectedTab === 'generator' 
                    ? 'bg-blue-100 text-blue-700' 
                    : 'text-gray-500 hover:text-gray-700'
                }`}
              >
                🚀 Generator
              </button>
              <button
                onClick={() => setSelectedTab('leads')}
                className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
                  selectedTab === 'leads' 
                    ? 'bg-green-100 text-green-700' 
                    : 'text-gray-500 hover:text-gray-700'
                }`}
              >
                📧 Clients ({mainLeads.length})
              </button>
              <button
                onClick={() => setSelectedTab('no-email')}
                className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
                  selectedTab === 'no-email' 
                    ? 'bg-orange-100 text-orange-700' 
                    : 'text-gray-500 hover:text-gray-700'
                }`}
              >
                ❌ No Email ({noEmailLeads.length})
              </button>
              <button
                onClick={() => setSelectedTab('monitoring')}
                className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
                  selectedTab === 'monitoring' 
                    ? 'bg-purple-100 text-purple-700' 
                    : 'text-gray-500 hover:text-gray-700'
                }`}
              >
                📊 Monitoring
              </button>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto py-8 px-4 sm:px-6 lg:px-8">
        {selectedTab === 'generator' && (
          <div className="bg-white rounded-lg shadow p-8">
            <div className="text-center mb-8">
              <h2 className="text-3xl font-bold text-gray-900 mb-2">
                🎯 Client Lead Generation
              </h2>
              <p className="text-gray-600">
                Find YouTube creators and send them professional video editing service outreach
              </p>
            </div>
            
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  🔍 Search Keywords
                </label>
                <div className="space-y-2">
                  {keywords.map((keyword, index) => (
                    <div key={index} className="flex space-x-2">
                      <input
                        type="text"
                        value={keyword}
                        onChange={(e) => handleKeywordChange(index, e.target.value)}
                        placeholder="Enter keyword (e.g., crypto trading)"
                        className="flex-1 px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                      />
                      {keywords.length > 1 && (
                        <button
                          onClick={() => removeKeyword(index)}
                          className="px-3 py-2 text-red-500 hover:text-red-700 font-bold"
                        >
                          ✕
                        </button>
                      )}
                    </div>
                  ))}
                  <button
                    onClick={addKeyword}
                    className="text-sm text-blue-500 hover:text-blue-700 font-medium"
                  >
                    + Add Keyword
                  </button>
                </div>
              </div>
              
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    📹 Max Videos per Keyword
                  </label>
                  <input
                    type="number"
                    value={maxVideos}
                    onChange={(e) => setMaxVideos(parseInt(e.target.value) || 2000)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    min="100"
                    max="5000"
                  />
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    🎯 Max Channels to Process
                  </label>
                  <input
                    type="number"
                    value={maxChannels}
                    onChange={(e) => setMaxChannels(parseInt(e.target.value) || 500)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    min="10"
                    max="1000"
                  />
                </div>
              </div>
            </div>
            
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8 border-t border-gray-200 pt-6">
              <div>
                <h3 className="text-lg font-medium text-gray-900 mb-4 flex items-center">
                  👥 Subscriber Range Filter
                </h3>
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Minimum Subscribers
                    </label>
                    <input
                      type="number"
                      value={subscriberMin}
                      onChange={(e) => setSubscriberMin(parseInt(e.target.value) || 0)}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                      min="0"
                      placeholder="e.g., 10000 (10K)"
                    />
                    <p className="text-xs text-gray-500 mt-1">
                      Default: 10,000 (Small channels)
                    </p>
                  </div>
                  
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Maximum Subscribers
                    </label>
                    <input
                      type="number"
                      value={subscriberMax}
                      onChange={(e) => setSubscriberMax(parseInt(e.target.value) || 1000000)}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                      min="1000"
                      placeholder="e.g., 1000000 (1M)"
                    />
                    <p className="text-xs text-gray-500 mt-1">
                      Default: 1,000,000 (Medium channels)
                    </p>
                  </div>
                </div>
              </div>
              
              <div>
                <h3 className="text-lg font-medium text-gray-900 mb-4 flex items-center">
                  📅 Content Frequency Filter
                </h3>
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Minimum Videos per Week
                    </label>
                    <input
                      type="number"
                      step="0.1"
                      value={contentFrequencyMin}
                      onChange={(e) => setContentFrequencyMin(parseFloat(e.target.value) || 0)}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                      min="0"
                      max="10"
                      placeholder="e.g., 0.14 (~1 video/week)"
                    />
                    <p className="text-xs text-gray-500 mt-1">
                      Default: 0.14 (~1 video per week minimum)
                    </p>
                  </div>
                  
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Maximum Videos per Week
                    </label>
                    <input
                      type="number"
                      step="0.1"
                      value={contentFrequencyMax}
                      onChange={(e) => setContentFrequencyMax(parseFloat(e.target.value) || 10)}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                      min="0.1"
                      max="20"
                      placeholder="e.g., 2.0 (2 videos/week)"
                    />
                    <p className="text-xs text-gray-500 mt-1">
                      Default: 2.0 (2 videos per week maximum)
                    </p>
                  </div>
                </div>
              </div>
            </div>

            <button
              onClick={startLeadGeneration}
              disabled={processing || keywords.some(k => !k.trim())}
              className={`w-full py-4 px-6 rounded-md font-medium text-lg transition-all ${
                processing || keywords.some(k => !k.trim())
                  ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
                  : 'bg-blue-600 text-white hover:bg-blue-700 transform hover:scale-105'
              }`}
            >
              {processing ? '🔄 Finding Potential Clients...' : '🚀 Start Client Lead Generation'}
            </button>

            {status && (
              <div className="mt-8 p-6 bg-gradient-to-r from-blue-50 to-purple-50 rounded-lg border">
                <h3 className="text-lg font-medium text-gray-900 mb-4 flex items-center">
                  📊 Processing Status
                </h3>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
                  <div className="text-center p-3 bg-white rounded-lg shadow">
                    <p className="text-2xl font-bold text-blue-600">
                      {status.channels_discovered || 0}
                    </p>
                    <p className="text-sm text-gray-600">🔍 Discovered</p>
                  </div>
                  <div className="text-center p-3 bg-white rounded-lg shadow">
                    <p className="text-2xl font-bold text-green-600">
                      {status.channels_processed || 0}
                    </p>
                    <p className="text-sm text-gray-600">✅ Processed</p>
                  </div>
                  <div className="text-center p-3 bg-white rounded-lg shadow">
                    <p className="text-2xl font-bold text-purple-600">
                      {status.emails_found || 0}
                    </p>
                    <p className="text-sm text-gray-600">📧 Emails Found</p>
                  </div>
                  <div className="text-center p-3 bg-white rounded-lg shadow">
                    <p className="text-2xl font-bold text-orange-600">
                      {status.emails_sent || 0}
                    </p>
                    <p className="text-sm text-gray-600">✉️ Outreach Sent</p>
                  </div>
                </div>
                
                <div className="mb-4">
                  <p className="text-sm text-gray-600 mb-2">⚡ Current Step:</p>
                  <p className="font-medium">{status.current_step}</p>
                </div>
                
                <div className={`px-4 py-2 rounded-md ${
                  status.status === 'completed' ? 'bg-green-100 text-green-800' :
                  status.status === 'failed' ? 'bg-red-100 text-red-800' :
                  'bg-blue-100 text-blue-800'
                }`}>
                  Status: {status.status?.toUpperCase()}
                </div>
                
                {status.errors?.length > 0 && (
                  <div className="mt-4">
                    <p className="text-sm text-red-600 font-medium">⚠️ Errors:</p>
                    <ul className="text-sm text-red-500 list-disc list-inside">
                      {status.errors.map((error, index) => (
                        <li key={index}>{error}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {selectedTab === 'leads' && (
          <div>
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-2xl font-bold text-gray-900 flex items-center">
                📧 Potential Clients ({mainLeads.length})
              </h2>
              <button
                onClick={loadLeads}
                className="px-4 py-2 text-blue-600 hover:text-blue-800 font-medium"
              >
                🔄 Refresh
              </button>
            </div>
            
            {mainLeads.length === 0 ? (
              <div className="text-center py-12 bg-white rounded-lg shadow">
                <div className="text-6xl mb-4">📧</div>
                <p className="text-gray-500 text-lg">No potential clients with emails found yet.</p>
                <p className="text-sm text-gray-400 mt-2">
                  Run the lead generation process to discover YouTube creators with contact emails for client outreach.
                </p>
              </div>
            ) : (
              <div className="grid gap-6">
                {mainLeads.map((lead) => (
                  <LeadCard key={lead.id} lead={lead} />
                ))}
              </div>
            )}
          </div>
        )}

        {selectedTab === 'no-email' && (
          <div>
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-2xl font-bold text-gray-900 flex items-center">
                ❌ Leads Without Email ({noEmailLeads.length})
              </h2>
              <button
                onClick={loadLeads}
                className="px-4 py-2 text-blue-600 hover:text-blue-800 font-medium"
              >
                🔄 Refresh
              </button>
            </div>
            
            {noEmailLeads.length === 0 ? (
              <div className="text-center py-12 bg-white rounded-lg shadow">
                <div className="text-6xl mb-4">🎉</div>
                <p className="text-gray-500 text-lg">No leads without emails!</p>
                <p className="text-sm text-gray-400 mt-2">
                  This is excellent! It means all discovered channels have contact information for client outreach.
                </p>
              </div>
            ) : (
              <div className="grid gap-6">
                {noEmailLeads.map((lead) => (
                  <LeadCard key={lead.id} lead={lead} showEmailInput={true} />
                ))}
              </div>
            )}
          </div>
        )}
      </main>
      
      {/* Footer */}
      <footer className="bg-white border-t mt-12">
        <div className="max-w-7xl mx-auto py-6 px-4 sm:px-6 lg:px-8">
          <div className="text-center text-gray-500 text-sm">
            <p>🎯 YouTube Client Lead Generation Platform | Find creators, send professional outreach</p>
            <p className="mt-2">💡 Tip: Use the Discord bot for advanced automation and real-time notifications</p>
          </div>
        </div>
      </footer>
    </div>
  );
}

export default App;