import React from 'react';

const SUBJECT_DISPLAY = (s) => s.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());

const SUBJECT_ICONS = {
  ssc_physics: '⚡',
  ssc_chemistry: '🧪',
  ssc_biology: '🌿',
  ssc_math: '📐',
  ssc_ict: '💻',
  ssc_science: '🔬',
  ssc_english_1st: '📖',
  ssc_english_2nd: '✏️',
  ssc_bangla_2nd: '📝',
  ssc_bangla_sahitto: '📚',
  ssc_bangla_sohopath: '📗',
};

export default function Sidebar({ subjects, selectedSubject, onSubjectChange, sessionId, onClearChat, sidebarOpen, onCloseSidebar }) {
  return (
    <>
      {/* Mobile overlay */}
      {sidebarOpen && (
        <div
          style={{
            position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.6)',
            zIndex: 40, display: 'none'
          }}
          className="sidebar-overlay"
          onClick={onCloseSidebar}
        />
      )}

      <aside style={{
        width: 'var(--sidebar-width)',
        background: 'var(--bg-secondary)',
        borderRight: '1px solid var(--border)',
        display: 'flex',
        flexDirection: 'column',
        flexShrink: 0,
        height: '100%',
        overflow: 'hidden',
      }}>
        {/* Logo */}
        <div style={{
          padding: '20px 16px 16px',
          borderBottom: '1px solid var(--border)',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <div style={{
              width: 36, height: 36,
              background: 'linear-gradient(135deg, var(--accent) 0%, #c0392b 100%)',
              borderRadius: 10,
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              fontSize: 18, flexShrink: 0,
              boxShadow: '0 4px 12px var(--accent-glow)',
            }}>📚</div>
            <div>
              <div style={{ fontWeight: 700, fontSize: 15, letterSpacing: '-0.3px', color: 'var(--text-primary)' }}>TUTOR AI</div>
              <div style={{ fontSize: 11, color: 'var(--text-muted)', letterSpacing: '0.3px' }}>Study Companion</div>
            </div>
          </div>
        </div>

        {/* Subjects */}
        <div style={{ padding: '14px 12px 8px', flex: 1, overflowY: 'auto' }}>
          <div style={{
            fontSize: 11, fontWeight: 600, color: 'var(--text-muted)',
            letterSpacing: '0.8px', textTransform: 'uppercase', marginBottom: 8, padding: '0 4px'
          }}>
            Subjects
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
            {subjects.map(subject => {
              const isActive = subject === selectedSubject;
              return (
                <button
                  key={subject}
                  onClick={() => { onSubjectChange(subject); onCloseSidebar(); }}
                  style={{
                    display: 'flex', alignItems: 'center', gap: 10,
                    padding: '8px 10px',
                    background: isActive ? 'var(--accent-dim)' : 'transparent',
                    border: isActive ? '1px solid rgba(233,69,96,0.3)' : '1px solid transparent',
                    borderRadius: 8,
                    cursor: 'pointer',
                    color: isActive ? 'var(--accent)' : 'var(--text-secondary)',
                    fontFamily: 'var(--font-main)',
                    fontSize: 13,
                    fontWeight: isActive ? 600 : 400,
                    textAlign: 'left',
                    transition: 'all 0.15s ease',
                    width: '100%',
                  }}
                  onMouseEnter={e => { if (!isActive) { e.currentTarget.style.background = 'var(--bg-hover)'; e.currentTarget.style.color = 'var(--text-primary)'; } }}
                  onMouseLeave={e => { if (!isActive) { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.color = 'var(--text-secondary)'; } }}
                >
                  <span style={{ fontSize: 16, flexShrink: 0 }}>{SUBJECT_ICONS[subject] || '📘'}</span>
                  <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {SUBJECT_DISPLAY(subject)}
                  </span>
                </button>
              );
            })}
          </div>

          {/* Tips */}
          <div style={{
            marginTop: 20,
            padding: '12px',
            background: 'var(--bg-surface)',
            border: '1px solid var(--border)',
            borderRadius: 10,
            fontSize: 12,
            color: 'var(--text-secondary)',
            lineHeight: 1.6,
          }}>
            <div style={{ fontWeight: 600, marginBottom: 6, color: 'var(--text-primary)', fontSize: 12 }}>💡 Tips</div>
            <div style={{ marginBottom: 5 }}>📷 <strong>Attach image</strong> to solve problems from photos</div>
            <div style={{ marginBottom: 5 }}>📝 Say <strong>"MCQ"</strong> or <strong>"CQ"</strong> for practice questions</div>
            <div>📑 Say <strong>"Chapter 3"</strong> to filter content</div>
          </div>
        </div>

        {/* Bottom */}
        <div style={{ padding: '12px', borderTop: '1px solid var(--border)' }}>
          <button
            onClick={onClearChat}
            style={{
              width: '100%', padding: '8px 12px',
              background: 'transparent',
              border: '1px solid var(--border)',
              borderRadius: 8,
              color: 'var(--text-secondary)',
              fontFamily: 'var(--font-main)',
              fontSize: 13, cursor: 'pointer',
              display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6,
              transition: 'all 0.15s ease',
            }}
            onMouseEnter={e => { e.currentTarget.style.borderColor = 'var(--accent)'; e.currentTarget.style.color = 'var(--accent)'; }}
            onMouseLeave={e => { e.currentTarget.style.borderColor = 'var(--border)'; e.currentTarget.style.color = 'var(--text-secondary)'; }}
          >
            🗑️ Clear Chat
          </button>
          {sessionId && (
            <div style={{ textAlign: 'center', marginTop: 8, fontSize: 11, color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
              {sessionId.slice(0, 8)}…
            </div>
          )}
        </div>
      </aside>
    </>
  );
}
