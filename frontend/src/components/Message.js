import React from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import remarkMath from 'remark-math';
import rehypeKatex from 'rehype-katex';
import 'katex/dist/katex.min.css';

const MODE_CONFIG = {
  exercise: { label: 'Exercise', color: '#ff6b35', bg: 'rgba(255,107,53,0.12)' },
  content: { label: 'Concept', color: '#3ddc84', bg: 'rgba(61,220,132,0.12)' },
};

export default function Message({ message }) {
  const isUser = message.role === 'user';

  if (isUser) {
    return (
      <div style={{
        display: 'flex',
        justifyContent: 'flex-end',
        marginBottom: 16,
        animation: 'fadeSlideIn 0.2s ease',
      }}>
        <div style={{ maxWidth: '70%' }}>
          {message.imagePreview && (
            <div style={{
              marginBottom: 6,
              borderRadius: 10,
              overflow: 'hidden',
              border: '1px solid var(--border)',
              maxWidth: 240,
              marginLeft: 'auto',
            }}>
              <img
                src={message.imagePreview}
                alt="Uploaded"
                style={{ display: 'block', width: '100%', maxHeight: 180, objectFit: 'cover' }}
              />
            </div>
          )}
          <div style={{
            background: 'var(--accent)',
            color: 'white',
            padding: '10px 14px',
            borderRadius: '18px 18px 4px 18px',
            fontSize: 14,
            lineHeight: 1.5,
            wordBreak: 'break-word',
          }}>
            {message.content}
          </div>
        </div>
      </div>
    );
  }

  const modeConf = MODE_CONFIG[message.mode] || MODE_CONFIG.content;

  return (
    <div style={{
      display: 'flex',
      gap: 10,
      marginBottom: 20,
      animation: 'fadeSlideIn 0.2s ease',
    }}>
      {/* Avatar */}
      <div style={{
        width: 32, height: 32, flexShrink: 0,
        background: 'linear-gradient(135deg, var(--accent) 0%, #c0392b 100%)',
        borderRadius: 10,
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        fontSize: 14, marginTop: 2,
        boxShadow: '0 2px 8px var(--accent-glow)',
      }}>📚</div>

      <div style={{ flex: 1, minWidth: 0 }}>
        {/* Mode badge */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 6 }}>
          <span style={{
            fontSize: 11, fontWeight: 600, letterSpacing: '0.5px',
            color: modeConf.color,
            background: modeConf.bg,
            padding: '2px 7px', borderRadius: 20,
            border: `1px solid ${modeConf.color}40`,
          }}>
            {modeConf.label}
          </span>
          <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>TUTOR AI</span>
        </div>

        {/* Content */}
        <div style={{
          background: 'var(--bg-surface)',
          border: '1px solid var(--border)',
          borderRadius: '4px 18px 18px 18px',
          padding: '12px 14px',
          fontSize: 14,
        }}>
          <div className="markdown-body">
            <ReactMarkdown
              remarkPlugins={[remarkGfm, remarkMath]}
              rehypePlugins={[rehypeKatex]}
            >
              {message.content}
            </ReactMarkdown>
          </div>
        </div>
      </div>
    </div>
  );
}