import React, { useState, useEffect, useRef, useCallback } from 'react';
import Sidebar from './components/Sidebar';
import Message from './components/Message';
import ChatInput from './components/ChatInput';
import * as api from './api';

const WELCOME_MESSAGE = {
  role: 'assistant',
  mode: 'content',
  content: `Welcome to **TUTOR AI** 👋

I'm your intelligent study companion, powered by your SSC syllabus. Here's what I can do:

- 📖 **Explain concepts** from your textbooks clearly and simply
- 📐 **Solve problems** step by step with full working
- 📷 **Read images** — attach a photo of a problem from your book or notebook
- 🎯 **Practice questions** — ask for MCQ or CQ exercises from any chapter

**To get started:** select a subject on the left, then type your question or attach an image!`,
};

export default function App() {
  const [sessionId, setSessionId] = useState(null);
  const [subjects, setSubjects] = useState([]);
  const [selectedSubject, setSelectedSubject] = useState('');
  const [messages, setMessages] = useState([WELCOME_MESSAGE]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [initError, setInitError] = useState('');
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const messagesEndRef = useRef(null);

  // Scroll to bottom on new message
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Init: create session + load subjects
  useEffect(() => {
    (async () => {
      try {
        const [sessionData, subjectsData] = await Promise.all([
          api.createSession(),
          api.getSubjects(),
        ]);
        setSessionId(sessionData.session_id);
        setSubjects(subjectsData.subjects);
        if (subjectsData.subjects.length > 0) {
          setSelectedSubject(subjectsData.subjects[0]);
        }
      } catch (err) {
        setInitError(`Cannot connect to TUTOR AI API. Make sure the backend is running at ${process.env.REACT_APP_API_URL || 'http://localhost:8000'}. Error: ${err.message}`);
      }
    })();
  }, []);

  const handleClearChat = useCallback(async () => {
    try {
      if (sessionId) await api.clearSession(sessionId);
    } catch (_) {}
    // Revoke any blob URLs from image previews before clearing
    setMessages(prev => {
      prev.forEach(msg => {
        if (msg.imagePreview) URL.revokeObjectURL(msg.imagePreview);
      });
      return [WELCOME_MESSAGE];
    });
    setError('');
  }, [sessionId]);

  const handleSend = useCallback(async ({ text, file, imagePreview }) => {
    if (!sessionId || !selectedSubject) return;
    setError('');

    // Add user message immediately
    const userMsg = {
      role: 'user',
      content: text,
      imagePreview: imagePreview || null,
    };
    setMessages(prev => [...prev, userMsg]);
    setLoading(true);

    try {
      let data;
      if (file) {
        data = await api.sendImageMessage(sessionId, text, selectedSubject, file);
      } else {
        data = await api.sendTextMessage(sessionId, text, selectedSubject);
      }

      setMessages(prev => [...prev, {
        role: 'assistant',
        content: data.answer,
        mode: data.mode,
      }]);
    } catch (err) {
      setError(`❌ ${err.message}`);
      // Remove the optimistic user message on error and revoke its preview URL
      if (imagePreview) URL.revokeObjectURL(imagePreview);
      setMessages(prev => prev.slice(0, -1));
    } finally {
      setLoading(false);
    }
  }, [sessionId, selectedSubject]);

  if (initError) {
    return (
      <div style={{
        height: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center',
        flexDirection: 'column', gap: 16, padding: 24, textAlign: 'center',
      }}>
        <div style={{ fontSize: 40 }}>⚠️</div>
        <div style={{ fontSize: 18, fontWeight: 600, color: 'var(--text-primary)' }}>Connection Failed</div>
        <div style={{
          maxWidth: 480, fontSize: 13, color: 'var(--text-secondary)', lineHeight: 1.6,
          background: 'var(--bg-surface)', border: '1px solid var(--border)',
          borderRadius: 10, padding: '14px 18px',
        }}>
          {initError}
        </div>
        <button
          onClick={() => window.location.reload()}
          style={{
            padding: '9px 20px', background: 'var(--accent)', color: 'white',
            border: 'none', borderRadius: 8, cursor: 'pointer',
            fontFamily: 'var(--font-main)', fontSize: 13, fontWeight: 500,
          }}
        >
          Retry
        </button>
      </div>
    );
  }

  return (
    <div style={{
      height: '100vh', display: 'flex', flexDirection: 'column', overflow: 'hidden',
    }}>
      {/* Keyframes */}
      <style>{`
        @keyframes fadeSlideIn {
          from { opacity: 0; transform: translateY(8px); }
          to { opacity: 1; transform: translateY(0); }
        }
        @keyframes pulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.5; }
        }
      `}</style>

      {/* Header */}
      <header style={{
        height: 'var(--header-height)', flexShrink: 0,
        background: 'var(--bg-secondary)',
        borderBottom: '1px solid var(--border)',
        display: 'flex', alignItems: 'center',
        padding: '0 16px', gap: 12, zIndex: 10,
      }}>
        {/* Mobile menu button */}
        <button
          onClick={() => setSidebarOpen(o => !o)}
          style={{
            display: 'none', // shown via media query in real app; for now always hidden on desktop
            background: 'transparent', border: 'none', cursor: 'pointer',
            color: 'var(--text-secondary)', padding: 4,
          }}
        >☰</button>

        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <div style={{
            width: 28, height: 28,
            background: 'linear-gradient(135deg, var(--accent) 0%, #c0392b 100%)',
            borderRadius: 8, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 14,
          }}>📚</div>
          <span style={{ fontWeight: 700, fontSize: 15, letterSpacing: '-0.3px' }}>TUTOR AI</span>
        </div>

        <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: 10 }}>
          {selectedSubject && (
            <div style={{
              padding: '4px 10px',
              background: 'var(--bg-surface)', border: '1px solid var(--border)',
              borderRadius: 20, fontSize: 12, color: 'var(--text-secondary)',
            }}>
              {selectedSubject.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())}
            </div>
          )}
          {loading && (
            <div style={{
              fontSize: 12, color: 'var(--accent)',
              animation: 'pulse 1s ease infinite',
            }}>
              ● thinking…
            </div>
          )}
        </div>
      </header>

      {/* Body */}
      <div style={{ flex: 1, display: 'flex', overflow: 'hidden' }}>
        {/* Sidebar */}
        {subjects.length > 0 && (
          <Sidebar
            subjects={subjects}
            selectedSubject={selectedSubject}
            onSubjectChange={setSelectedSubject}
            sessionId={sessionId}
            onClearChat={handleClearChat}
            sidebarOpen={sidebarOpen}
            onCloseSidebar={() => setSidebarOpen(false)}
          />
        )}

        {/* Chat area */}
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden', minWidth: 0 }}>
          {/* Messages */}
          <div style={{
            flex: 1, overflowY: 'auto',
            padding: '24px 20px 8px',
          }}>
            <div style={{ maxWidth: 760, margin: '0 auto' }}>
              {messages.map((msg, i) => (
                <Message key={i} message={msg} />
              ))}

              {/* Loading indicator */}
              {loading && (
                <div style={{
                  display: 'flex', gap: 10, marginBottom: 16,
                  animation: 'fadeSlideIn 0.2s ease',
                }}>
                  <div style={{
                    width: 32, height: 32, flexShrink: 0,
                    background: 'linear-gradient(135deg, var(--accent) 0%, #c0392b 100%)',
                    borderRadius: 10,
                    display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 14,
                    boxShadow: '0 2px 8px var(--accent-glow)',
                  }}>📚</div>
                  <div style={{
                    background: 'var(--bg-surface)', border: '1px solid var(--border)',
                    borderRadius: '4px 18px 18px 18px',
                    padding: '12px 16px',
                    display: 'flex', alignItems: 'center', gap: 6,
                  }}>
                    {[0, 0.2, 0.4].map((delay, i) => (
                      <div key={i} style={{
                        width: 7, height: 7, borderRadius: '50%',
                        background: 'var(--text-muted)',
                        animation: `pulse 1s ease ${delay}s infinite`,
                      }} />
                    ))}
                  </div>
                </div>
              )}

              {/* Error */}
              {error && (
                <div style={{
                  maxWidth: 500,
                  padding: '10px 14px', marginBottom: 16,
                  background: 'rgba(233,69,96,0.1)', border: '1px solid rgba(233,69,96,0.3)',
                  borderRadius: 10, fontSize: 13, color: '#ff8096',
                  animation: 'fadeSlideIn 0.2s ease',
                }}>
                  {error}
                  <button
                    onClick={() => setError('')}
                    style={{
                      marginLeft: 8, background: 'none', border: 'none',
                      cursor: 'pointer', color: '#ff8096', fontSize: 14,
                    }}
                  >✕</button>
                </div>
              )}

              <div ref={messagesEndRef} />
            </div>
          </div>

          {/* Input */}
          <div style={{ maxWidth: 760, margin: '0 auto', width: '100%' }}>
            <ChatInput
              onSend={handleSend}
              loading={loading}
              disabled={!sessionId || subjects.length === 0}
              selectedSubject={selectedSubject}
            />
          </div>
        </div>
      </div>
    </div>
  );
}
