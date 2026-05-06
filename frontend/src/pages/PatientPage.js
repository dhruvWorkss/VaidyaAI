import React, { useState, useRef, useEffect } from 'react';
import { speakText, transcribeAudio, analyzeReport } from '../services/api';
import { FiMic, FiSquare, FiSend, FiPaperclip, FiGlobe } from 'react-icons/fi';
import ReactMarkdown from 'react-markdown';
import DnaLogo from '../components/DnaLogo';

const LANGS = [
  { code: 'en', label: 'English' },
  { code: 'hi', label: 'हिंदी' },
  { code: 'kn', label: 'ಕನ್ನಡ' },
];

const SUGGESTIONS = [
  { icon: '🩺', text: 'I have a headache and fever' },
  { icon: '💊', text: 'Explain my blood report' },
  { icon: '🫀', text: 'I have chest pain' },
  { icon: '🌡️', text: 'Symptoms of diabetes' },
];

export default function PatientPage({ sessionId, isHome, onFirstMessage, onUpdateTitle }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [isRecording, setIsRecording] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [language, setLanguage] = useState('en');
  const [showLang, setShowLang] = useState(false);
  const [recordSecs, setRecordSecs] = useState(0);
  const [activeSession, setActiveSession] = useState(sessionId);

  const recorderRef = useRef(null);
  const chunksRef = useRef([]);
  const bottomRef = useRef(null);
  const timerRef = useRef(null);
  const titleSet = useRef(false);
  const fileRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  useEffect(() => {
    if (isRecording) {
      timerRef.current = setInterval(() => setRecordSecs(s => s + 1), 1000);
    } else {
      clearInterval(timerRef.current);
      setRecordSecs(0);
    }
    return () => clearInterval(timerRef.current);
  }, [isRecording]);

  const addMsg = (role, content) => setMessages(p => [...p, { role, content }]);

  const send = async (text) => {
    if (!text.trim() || isLoading) return;

    let sid = activeSession;

    if (sid === 'home') {
      const newId = onFirstMessage();
      setActiveSession(newId);
      sid = newId;
    }

    if (!titleSet.current && onUpdateTitle) {
      onUpdateTitle(sid, text.slice(0, 35) + (text.length > 35 ? '...' : ''));
      titleSet.current = true;
    }

    addMsg('user', text);
    setInput('');
    setIsLoading(true);

    try {
      const response = await fetch('http://localhost:8000/api/triage/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: text,
          session_id: sid,
          language: language,
        }),
      });
      const data = await response.json();
      addMsg('assistant', data.response);
      try {
        const blob = await speakText(data.response, language);
        new Audio(URL.createObjectURL(blob)).play();
      } catch (_) {}
    } catch (err) {
      console.error('Error:', err);
      addMsg('assistant', 'Something went wrong. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleFile = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    addMsg('user', `📎 Uploaded: ${file.name}`);
    setIsLoading(true);

    try {
      const data = await analyzeReport(file, language);
      addMsg('assistant', data.analysis);
    } catch (err) {
      addMsg('assistant', 'Could not analyze the report. Please try again or type the values manually.');
    } finally {
      setIsLoading(false);
      e.target.value = '';
    }
  };

  const startRec = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      recorderRef.current = new MediaRecorder(stream);
      chunksRef.current = [];
      recorderRef.current.ondataavailable = e => chunksRef.current.push(e.data);
      recorderRef.current.onstop = async () => {
        const blob = new Blob(chunksRef.current, { type: 'audio/wav' });
        try {
          const data = await transcribeAudio(blob);
          if (data.text) send(data.text);
        } catch {
          addMsg('assistant', 'Could not transcribe. Please type instead.');
        }
        stream.getTracks().forEach(t => t.stop());
      };
      recorderRef.current.start();
      setIsRecording(true);
    } catch {
      alert('Microphone access denied.');
    }
  };

  const stopRec = () => { recorderRef.current?.stop(); setIsRecording(false); };
  const fmt = s => `${Math.floor(s / 60).toString().padStart(2, '0')}:${(s % 60).toString().padStart(2, '0')}`;

  const getRisk = (content) => {
    if (content.includes('EMERGENCY')) return '#ef4444';
    if (content.includes('HIGH RISK')) return '#f97316';
    if (content.includes('MEDIUM RISK')) return '#eab308';
    if (content.includes('LOW RISK')) return '#22c55e';
    return null;
  };

  const showHome = messages.length === 0;

  return (
    <div style={S.page}>
      {/* Top bar */}
      <div style={S.topbar}>
        <div style={S.planBadge}>
          Free plan · <span style={{ color: 'var(--accent)' }}>Upgrade</span>
        </div>
        <div style={{ position: 'relative' }}>
          <button style={S.langBtn} onClick={() => setShowLang(p => !p)}>
            <FiGlobe size={13} />
            <span>{LANGS.find(l => l.code === language)?.label}</span>
          </button>
          {showLang && (
            <div style={S.langDrop}>
              {LANGS.map(l => (
                <button
                  key={l.code}
                  style={{
                    ...S.langOpt,
                    color: l.code === language ? 'var(--accent)' : 'var(--text-sub)',
                  }}
                  onClick={() => { setLanguage(l.code); setShowLang(false); }}
                >
                  {l.label}
                </button>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Home screen */}
      {showHome && (
        <div style={S.home}>
          <div style={S.homeHero}>
            <DnaLogo size={56} />
            <h1 style={S.heroTitle}>How can I help you today?</h1>
            <p style={S.heroSub}>Describe your symptoms or upload a medical report</p>
          </div>
          <div style={S.inputWrap}>
            <InputBox
              input={input} setInput={setInput}
              onSend={() => send(input)}
              isRecording={isRecording} isLoading={isLoading}
              recordSecs={recordSecs} fmt={fmt}
              startRec={startRec} stopRec={stopRec}
              fileRef={fileRef} handleFile={handleFile}
            />
          </div>
          <div style={S.suggestions}>
            {SUGGESTIONS.map((s, i) => (
              <button key={i} style={S.sugBtn} onClick={() => send(s.text)}>
                <span style={{ fontSize: '16px' }}>{s.icon}</span>
                <span style={{ fontSize: '13px' }}>{s.text}</span>
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Chat messages */}
      {!showHome && (
        <div style={S.chat}>
          {messages.map((msg, i) => {
            const risk = msg.role === 'assistant' ? getRisk(msg.content) : null;

            if (msg.role === 'user') {
              return (
                <div key={i} className="msg-anim" style={S.userRow}>
                  <div style={S.userBubble}>
                    {msg.content}
                  </div>
                </div>
              );
            }

            return (
              <div key={i} className="msg-anim" style={S.aiRow}>
                <div style={S.aiAvatar}>
                  <DnaLogo size={28} />
                </div>
                <div style={{
                  ...S.aiContent,
                  borderLeft: risk ? `3px solid ${risk}` : undefined,
                  paddingLeft: risk ? '14px' : undefined,
                }}>
                  <div style={S.aiCard}>
                    <ReactMarkdown
                      components={{
                        p: ({ node, ...props }) => (
                          <p style={{ marginBottom: '10px', lineHeight: '1.75' }} {...props} />
                        ),
                        ul: ({ node, ...props }) => (
                          <ul style={{ paddingLeft: '18px', marginBottom: '10px' }} {...props} />
                        ),
                        ol: ({ node, ...props }) => (
                          <ol style={{ paddingLeft: '18px', marginBottom: '10px' }} {...props} />
                        ),
                        li: ({ node, ...props }) => (
                          <li style={{ marginBottom: '5px', lineHeight: '1.65' }} {...props} />
                        ),
                        strong: ({ node, ...props }) => (
                          <strong style={{ color: '#4ade80', fontWeight: '600' }} {...props} />
                        ),
                        h1: ({ node, ...props }) => (
                          <h1 style={{ fontSize: '16px', fontWeight: '700', marginBottom: '10px', color: 'var(--text)' }} {...props} />
                        ),
                        h2: ({ node, ...props }) => (
                          <h2 style={{ fontSize: '15px', fontWeight: '600', marginBottom: '8px', color: 'var(--text)' }} {...props} />
                        ),
                        h3: ({ node, ...props }) => (
                          <h3 style={{ fontSize: '14px', fontWeight: '600', marginBottom: '6px', color: 'var(--text)' }} {...props} />
                        ),
                        hr: ({ node, ...props }) => (
                          <hr style={{ border: 'none', borderTop: '1px solid var(--border)', margin: '12px 0' }} {...props} />
                        ),
                        blockquote: ({ node, ...props }) => (
                          <blockquote style={{
                            borderLeft: '3px solid var(--accent)',
                            paddingLeft: '12px',
                            color: 'var(--text-sub)',
                            fontStyle: 'italic',
                            margin: '10px 0',
                          }} {...props} />
                        ),
                      }}
                    >
                      {msg.content}
                    </ReactMarkdown>
                  </div>
                </div>
              </div>
            );
          })}

          {isLoading && (
            <div className="msg-anim" style={S.aiRow}>
              <div style={S.aiAvatar}>
                <DnaLogo size={28} spinning={true} />
              </div>
              <div style={S.aiCard}>
                <div className="typing">
                  <span /><span /><span />
                </div>
              </div>
            </div>
          )}
          <div ref={bottomRef} />
        </div>
      )}

      {/* Sticky input */}
      {!showHome && (
        <div style={S.stickyInput}>
          <InputBox
            input={input} setInput={setInput}
            onSend={() => send(input)}
            isRecording={isRecording} isLoading={isLoading}
            recordSecs={recordSecs} fmt={fmt}
            startRec={startRec} stopRec={stopRec}
            fileRef={fileRef} handleFile={handleFile}
          />
          <div style={S.disclaimer}>
            VaidyaAI provides triage guidance only — always consult a qualified doctor.
          </div>
        </div>
      )}
    </div>
  );
}

function InputBox({ input, setInput, onSend, isRecording, isLoading, recordSecs, fmt, startRec, stopRec, fileRef, handleFile }) {
  return (
    <div style={IB.box}>
      <textarea
        style={IB.ta}
        value={input}
        onChange={e => setInput(e.target.value)}
        onKeyDown={e => {
          if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            onSend();
          }
        }}
        placeholder={isRecording ? `Recording... ${fmt(recordSecs)}` : 'How can I help you today?'}
        rows={1}
        disabled={isLoading || isRecording}
      />
      <div style={IB.row}>
        <div style={IB.left}>
          <button style={IB.iconBtn} onClick={() => fileRef.current?.click()} title="Upload medical report">
            <FiPaperclip size={16} color="var(--text-muted)" />
          </button>
          <input
            ref={fileRef}
            type="file"
            accept=".pdf,.jpg,.png,.txt"
            style={{ display: 'none' }}
            onChange={handleFile}
          />
        </div>
        <div style={IB.right}>
          <button
            style={{ ...IB.iconBtn, color: isRecording ? '#ef4444' : 'var(--text-muted)' }}
            onClick={isRecording ? stopRec : startRec}
            disabled={isLoading}
            title="Voice input"
          >
            {isRecording ? <FiSquare size={16} /> : <FiMic size={16} />}
          </button>
          <button
            style={{
              ...IB.sendBtn,
              opacity: (!input.trim() || isLoading) ? 0.35 : 1,
            }}
            onClick={onSend}
            disabled={!input.trim() || isLoading}
          >
            <FiSend size={14} color="#fff" />
          </button>
        </div>
      </div>
    </div>
  );
}

const S = {
  page: {
    flex: 1, display: 'flex', flexDirection: 'column',
    height: '100vh', overflow: 'hidden',
  },
  topbar: {
    display: 'flex', alignItems: 'center',
    justifyContent: 'center', gap: '16px',
    padding: '10px 24px', flexShrink: 0,
    position: 'relative',
    borderBottom: '1px solid var(--border)',
  },
  planBadge: {
    fontSize: '12px', color: 'var(--text-muted)',
    background: 'var(--surface)', border: '1px solid var(--border)',
    padding: '4px 12px', borderRadius: '20px',
  },
  langBtn: {
    display: 'flex', alignItems: 'center', gap: '6px',
    fontSize: '12px', color: 'var(--text-muted)',
    background: 'var(--surface)', border: '1px solid var(--border)',
    padding: '4px 12px', borderRadius: '20px', cursor: 'pointer',
    position: 'absolute', right: '24px', top: '10px',
  },
  langDrop: {
    position: 'absolute', top: '110%', right: 0,
    background: 'var(--surface2)', border: '1px solid var(--border)',
    borderRadius: '10px', padding: '6px', zIndex: 100, minWidth: '130px',
  },
  langOpt: {
    display: 'block', width: '100%', padding: '8px 12px',
    borderRadius: '6px', fontSize: '13px', cursor: 'pointer',
    textAlign: 'left', background: 'none',
  },
  home: {
    flex: 1, display: 'flex', flexDirection: 'column',
    alignItems: 'center', justifyContent: 'center',
    padding: '0 24px 40px', gap: '28px',
  },
  homeHero: {
    display: 'flex', flexDirection: 'column',
    alignItems: 'center', gap: '14px',
  },
  heroTitle: {
    fontSize: '28px', fontWeight: '600',
    color: 'var(--text)', textAlign: 'center',
  },
  heroSub: {
    fontSize: '14px', color: 'var(--text-muted)',
    textAlign: 'center',
  },
  inputWrap: { width: '100%', maxWidth: '680px' },
  suggestions: {
    display: 'flex', flexWrap: 'wrap',
    gap: '8px', justifyContent: 'center',
    maxWidth: '680px',
  },
  sugBtn: {
    display: 'flex', alignItems: 'center', gap: '8px',
    padding: '10px 16px', borderRadius: '20px',
    border: '1px solid var(--border)', background: 'var(--surface)',
    fontSize: '13px', color: 'var(--text-sub)', cursor: 'pointer',
  },
  chat: {
    flex: 1, overflowY: 'auto',
    padding: '32px 24px 8px',
    display: 'flex', flexDirection: 'column', gap: '24px',
  },
  userRow: {
    display: 'flex',
    justifyContent: 'flex-end',
    width: '100%',
    maxWidth: '720px',
    margin: '0 auto',
  },
  userBubble: {
    background: 'var(--surface2)',
    padding: '10px 16px',
    borderRadius: '18px 18px 4px 18px',
    fontSize: '14px',
    lineHeight: '1.7',
    color: 'var(--text)',
    maxWidth: '65%',
    wordBreak: 'break-word',
  },
  aiRow: {
    display: 'flex',
    alignItems: 'flex-start',
    gap: '12px',
    width: '100%',
    maxWidth: '720px',
    margin: '0 auto',
  },
  aiAvatar: { flexShrink: 0, marginTop: '2px' },
  aiContent: { flex: 1, minWidth: 0 },
  aiCard: {
    background: 'var(--surface)',
    border: '1px solid var(--border)',
    borderRadius: '12px',
    padding: '16px 18px',
    fontSize: '14px',
    lineHeight: '1.75',
    color: 'var(--text)',
  },
  stickyInput: {
    padding: '12px 24px 16px', flexShrink: 0,
    maxWidth: '760px', width: '100%', margin: '0 auto',
  },
  disclaimer: {
    fontSize: '11px', color: 'var(--text-muted)',
    textAlign: 'center', marginTop: '8px',
  },
};

const IB = {
  box: {
    background: 'var(--surface)',
    border: '1px solid var(--border)',
    borderRadius: '14px',
    padding: '12px 12px 8px 16px',
  },
  ta: {
    width: '100%', background: 'transparent',
    border: 'none', outline: 'none',
    color: 'var(--text)', fontSize: '14px',
    lineHeight: '1.6', resize: 'none',
    maxHeight: '180px', overflowY: 'auto',
    marginBottom: '8px',
  },
  row: {
    display: 'flex', alignItems: 'center',
    justifyContent: 'space-between',
  },
  left: { display: 'flex', gap: '4px' },
  right: { display: 'flex', alignItems: 'center', gap: '6px' },
  iconBtn: {
    padding: '6px', borderRadius: '8px',
    background: 'none', cursor: 'pointer',
    display: 'flex', alignItems: 'center', justifyContent: 'center',
  },
  sendBtn: {
    width: '32px', height: '32px', borderRadius: '8px',
    background: 'var(--accent)', display: 'flex',
    alignItems: 'center', justifyContent: 'center',
    cursor: 'pointer', transition: 'opacity 0.15s',
  },
};