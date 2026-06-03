import React, { useRef, useState, useEffect } from 'react';

const MAX_FILE_SIZE = 10 * 1024 * 1024; // 10MB
const ALLOWED_TYPES = ['image/jpeg', 'image/png', 'image/webp', 'image/gif'];

export default function ChatInput({ onSend, loading, disabled, selectedSubject }) {
  const [text, setText] = useState('');
  const [attachedFile, setAttachedFile] = useState(null); // { file: File, preview: string }
  const [attachError, setAttachError] = useState('');
  const textareaRef = useRef(null);
  const fileInputRef = useRef(null);

  // Auto-resize textarea
  useEffect(() => {
    const ta = textareaRef.current;
    if (!ta) return;
    ta.style.height = 'auto';
    ta.style.height = Math.min(ta.scrollHeight, 160) + 'px';
  }, [text]);

  const handleFileSelect = (e) => {
    const file = e.target.files[0];
    if (!file) return;
    setAttachError('');

    if (!ALLOWED_TYPES.includes(file.type)) {
      setAttachError('Only JPEG, PNG, WEBP, or GIF images are supported.');
      e.target.value = '';
      return;
    }
    if (file.size > MAX_FILE_SIZE) {
      setAttachError('Image is too large. Maximum size is 10 MB.');
      e.target.value = '';
      return;
    }

    const preview = URL.createObjectURL(file);
    setAttachedFile({ file, preview });
    e.target.value = ''; // reset input so same file can be re-selected
  };

  const removeAttachment = () => {
    if (attachedFile?.preview) URL.revokeObjectURL(attachedFile.preview);
    setAttachedFile(null);
    setAttachError('');
  };

  const handleSend = () => {
    const message = text.trim();
    if (!message && !attachedFile) return;
    if (loading || disabled) return;

    onSend({
      text: message || 'Please read and solve the problem shown in this photo.',
      file: attachedFile?.file || null,
      imagePreview: attachedFile?.preview || null,
    });

    setText('');
    // Don't revoke preview here — Message component still needs it for display
    // Caller should manage the preview lifecycle
    setAttachedFile(null);
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const canSend = (text.trim() || attachedFile) && !loading && !disabled;

  return (
    <div style={{
      padding: '12px 16px 16px',
      borderTop: '1px solid var(--border)',
      background: 'var(--bg-secondary)',
    }}>
      {/* Attachment preview */}
      {attachedFile && (
        <div style={{
          display: 'flex', alignItems: 'center', gap: 8,
          marginBottom: 8,
          padding: '8px 10px',
          background: 'var(--bg-surface)',
          border: '1px solid var(--border)',
          borderRadius: 8,
        }}>
          <img
            src={attachedFile.preview}
            alt="Preview"
            style={{
              width: 40, height: 40, objectFit: 'cover',
              borderRadius: 6, flexShrink: 0,
            }}
          />
          <div style={{ flex: 1, overflow: 'hidden' }}>
            <div style={{ fontSize: 12, fontWeight: 500, color: 'var(--text-primary)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
              {attachedFile.file.name}
            </div>
            <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>
              {(attachedFile.file.size / 1024).toFixed(0)} KB · {attachedFile.file.type.split('/')[1].toUpperCase()}
            </div>
          </div>
          <button
            onClick={removeAttachment}
            title="Remove"
            style={{
              background: 'transparent', border: 'none', cursor: 'pointer',
              color: 'var(--text-muted)', fontSize: 16, padding: '2px 4px',
              borderRadius: 4, lineHeight: 1,
              flexShrink: 0,
            }}
            onMouseEnter={e => e.currentTarget.style.color = 'var(--accent)'}
            onMouseLeave={e => e.currentTarget.style.color = 'var(--text-muted)'}
          >
            ✕
          </button>
        </div>
      )}

      {/* Error */}
      {attachError && (
        <div style={{
          marginBottom: 8, padding: '7px 10px',
          background: 'rgba(233,69,96,0.1)', border: '1px solid rgba(233,69,96,0.3)',
          borderRadius: 7, fontSize: 12, color: 'var(--accent)',
        }}>
          ⚠️ {attachError}
        </div>
      )}

      {/* Input row */}
      <div style={{
        display: 'flex', alignItems: 'flex-end', gap: 8,
        background: 'var(--bg-surface)',
        border: '1px solid var(--border-light)',
        borderRadius: 14,
        padding: '8px 8px 8px 12px',
        transition: 'border-color 0.15s',
      }}
        onFocus={() => {}}
        onClick={() => textareaRef.current?.focus()}
      >
        {/* Paperclip button */}
        <button
          type="button"
          onClick={() => fileInputRef.current?.click()}
          disabled={loading || disabled}
          title="Attach image"
          style={{
            width: 34, height: 34, flexShrink: 0,
            background: attachedFile ? 'var(--accent-dim)' : 'transparent',
            border: attachedFile ? '1px solid rgba(233,69,96,0.4)' : '1px solid transparent',
            borderRadius: 8, cursor: loading || disabled ? 'not-allowed' : 'pointer',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            color: attachedFile ? 'var(--accent)' : 'var(--text-muted)',
            transition: 'all 0.15s ease',
            opacity: loading || disabled ? 0.5 : 1,
          }}
          onMouseEnter={e => { if (!loading && !disabled && !attachedFile) { e.currentTarget.style.color = 'var(--text-secondary)'; e.currentTarget.style.background = 'var(--bg-hover)'; } }}
          onMouseLeave={e => { if (!attachedFile) { e.currentTarget.style.color = 'var(--text-muted)'; e.currentTarget.style.background = 'transparent'; } }}
        >
          <PaperclipIcon />
        </button>

        {/* Hidden file input */}
        <input
          ref={fileInputRef}
          type="file"
          accept="image/jpeg,image/png,image/webp,image/gif"
          style={{ display: 'none' }}
          onChange={handleFileSelect}
        />

        {/* Textarea */}
        <textarea
          ref={textareaRef}
          value={text}
          onChange={e => setText(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={loading || disabled}
          placeholder={
            attachedFile
              ? 'Add context for this image… (optional)'
              : `Ask anything about ${selectedSubject ? selectedSubject.replace(/_/g, ' ') : 'your subject'}…`
          }
          rows={1}
          style={{
            flex: 1, resize: 'none',
            background: 'transparent', border: 'none', outline: 'none',
            color: 'var(--text-primary)', fontFamily: 'var(--font-main)',
            fontSize: 14, lineHeight: 1.5,
            padding: '5px 0',
            maxHeight: 160,
            overflowY: 'auto',
          }}
        />

        {/* Send button */}
        <button
          type="button"
          onClick={handleSend}
          disabled={!canSend}
          title="Send (Enter)"
          style={{
            width: 34, height: 34, flexShrink: 0,
            background: canSend ? 'var(--accent)' : 'var(--bg-hover)',
            border: 'none', borderRadius: 9,
            cursor: canSend ? 'pointer' : 'not-allowed',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            color: canSend ? 'white' : 'var(--text-muted)',
            transition: 'all 0.15s ease',
            opacity: canSend ? 1 : 0.5,
          }}
          onMouseEnter={e => { if (canSend) e.currentTarget.style.background = '#c73652'; }}
          onMouseLeave={e => { if (canSend) e.currentTarget.style.background = 'var(--accent)'; }}
        >
          {loading ? <SpinnerIcon /> : <SendIcon />}
        </button>
      </div>

      <div style={{ fontSize: 11, color: 'var(--text-muted)', textAlign: 'center', marginTop: 6 }}>
        Press Enter to send · Shift+Enter for new line · Attach image with 📎
      </div>
    </div>
  );
}

function PaperclipIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M21.44 11.05l-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48"/>
    </svg>
  );
}

function SendIcon() {
  return (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
      <line x1="22" y1="2" x2="11" y2="13"/>
      <polygon points="22 2 15 22 11 13 2 9 22 2"/>
    </svg>
  );
}

function SpinnerIcon() {
  return (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round">
      <path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83"
        style={{ animation: 'spin 0.7s linear infinite', transformOrigin: 'center' }}
      />
      <style>{`@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }`}</style>
    </svg>
  );
}
