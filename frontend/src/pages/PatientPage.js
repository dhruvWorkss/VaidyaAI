import React, { useState, useRef, useEffect, useLayoutEffect } from 'react';
import { speakText, transcribeAudio, analyzeReport, getSession, sendMessage } from '../services/api';
import { FiMic, FiSquare, FiSend, FiPaperclip, FiGlobe, FiVolume2 } from 'react-icons/fi';
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

export default function PatientPage({ sessionId, isHome, onFirstMessage, onUpdateTitle, serviceStatus = 'ready' }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [isRecording, setIsRecording] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [language, setLanguage] = useState('en');
  const [showLang, setShowLang] = useState(false);
  const [recordSecs, setRecordSecs] = useState(0);
  const [activeSession, setActiveSession] = useState(sessionId);
  const [speakingMessage, setSpeakingMessage] = useState(null);

  const recorderRef = useRef(null);
  const chunksRef = useRef([]);
  const chatRef = useRef(null);
  const timerRef = useRef(null);
  const titleSet = useRef(false);
  const fileRef = useRef(null);
  const requestControllerRef = useRef(null);
  const requestIdRef = useRef(0);
  const audioRef = useRef(null);
  const speechControllerRef = useRef(null);

  useLayoutEffect(() => {
    // Browsers can restore the document's old scroll offset across a deploy or
    // refresh. Reset it before paint; the app shell itself must never scroll.
    window.scrollTo(0, 0);
    document.documentElement.scrollTop = 0;
    document.body.scrollTop = 0;
  }, []);

  useEffect(() => () => {
    requestControllerRef.current?.abort();
    speechControllerRef.current?.abort();
    audioRef.current?.pause();
  }, []);

  useEffect(() => {
    if (sessionId === 'home') {
      setMessages([]);
      setActiveSession('home');
      titleSet.current = false;
      return undefined;
    }

    const controller = new AbortController();
    setActiveSession(sessionId);
    getSession(sessionId)
      .then(session => {
        if (controller.signal.aborted) return;
        setMessages(session.messages || []);
        if (session.language) setLanguage(session.language);
        titleSet.current = Boolean(session.messages?.length);
      })
      .catch(err => {
        // A newly-created consultation does not exist on the backend until its
        // first message is sent. That is an expected empty chat, not an error.
        if (!controller.signal.aborted && err.status !== 404) {
          console.error('Could not load consultation:', err);
        }
      });
    return () => controller.abort();
  }, [sessionId]);

  useEffect(() => {
    const chat = chatRef.current;
    if (!chat) return undefined;

    // Scroll only the message pane. scrollIntoView can also move the document
    // viewport, which pushed the top bar and newest reply above the screen.
    const frame = requestAnimationFrame(() => {
      if (typeof chat.scrollTo === 'function') {
        chat.scrollTo({ top: chat.scrollHeight, behavior: 'smooth' });
      } else {
        chat.scrollTop = chat.scrollHeight;
      }
    });
    return () => cancelAnimationFrame(frame);
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
      sid = onFirstMessage();
      setActiveSession(sid);
    }

    if (!titleSet.current && onUpdateTitle) {
      onUpdateTitle(sid, text.slice(0, 35) + (text.length > 35 ? '...' : ''));
      titleSet.current = true;
    }

    addMsg('user', text);
    setInput('');
    setIsLoading(true);
    const controller = new AbortController();
    const requestId = ++requestIdRef.current;
    requestControllerRef.current = controller;

    try {
      const data = await sendMessage(text, sid, language, controller.signal);
      if (requestId !== requestIdRef.current) return;
      addMsg('assistant', data.response);

    } catch (err) {
      if (err.name === 'AbortError') return;
      console.error('Error:', err);
      const message = err.status === 504
        ? 'The medical assistant took too long to respond. Please try again.'
        : err.status === 503
          ? 'The medical assistant is temporarily unavailable. Please try again shortly.'
          : 'I could not reach the medical assistant. Please check your connection and try again.';
      addMsg('assistant', message);
    } finally {
      if (requestId === requestIdRef.current) {
        requestControllerRef.current = null;
        setIsLoading(false);
      }
    }
  };

  const stopResponse = () => {
    if (!requestControllerRef.current) return;
    requestIdRef.current += 1;
    requestControllerRef.current.abort();
    requestControllerRef.current = null;
    setIsLoading(false);
  };

  const stopSpeaking = () => {
    speechControllerRef.current?.abort();
    speechControllerRef.current = null;
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current.currentTime = 0;
      URL.revokeObjectURL(audioRef.current.src);
      audioRef.current = null;
    }
    setSpeakingMessage(null);
  };

  const readAloud = async (content, messageIndex) => {
    if (speakingMessage === messageIndex) {
      stopSpeaking();
      return;
    }

    stopSpeaking();
    const controller = new AbortController();
    speechControllerRef.current = controller;
    setSpeakingMessage(messageIndex);

    try {
      const blob = await speakText(content, language, controller.signal);
      if (controller.signal.aborted) return;

      const audioUrl = URL.createObjectURL(blob);
      const audio = new Audio(audioUrl);
      audioRef.current = audio;
      audio.onended = () => {
        URL.revokeObjectURL(audioUrl);
        audioRef.current = null;
        speechControllerRef.current = null;
        setSpeakingMessage(null);
      };
      audio.onerror = audio.onended;
      await audio.play();
    } catch (err) {
      if (err.name !== 'AbortError') console.error('Speech playback failed:', err);
      if (!controller.signal.aborted) setSpeakingMessage(null);
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
    <div className="patient-page" style={S.page}>
      <div className="aurora aurora-one" />
      <div className="aurora aurora-two" />
      <div className="medical-grid" />
      {/* Top bar */}
      <div className="topbar-glass" style={S.topbar}>
        <div className={`live-status service-${serviceStatus}`}>
          <span className="live-dot" />
          {serviceStatus === 'connecting'
            ? 'Starting secure service'
            : serviceStatus === 'offline'
              ? 'Service reconnecting'
              : 'AI health companion ready'}
        </div>
        <div style={S.planBadge}>
          <span className="shield-mark">✦</span> Private by design
        </div>
        <div style={S.langWrap}>
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
        <div className="home-stage" style={S.home}>
          <div className="hero-orbit" aria-hidden="true">
            <span className="orbit-dot orbit-dot-one" />
            <span className="orbit-dot orbit-dot-two" />
            <div className="hero-logo"><DnaLogo size={64} /></div>
          </div>
          <div style={S.homeHero}>
            <div className="hero-eyebrow">MEET YOUR AI HEALTH COMPANION</div>
            <h1 style={S.heroTitle}>Care, <span className="gradient-text">decoded.</span></h1>
            <p style={S.heroSub}>Tell me how you feel. I’ll help you understand what matters<br className="desktop-break" /> and what to do next.</p>
          </div>
          <div className="hero-input" style={S.inputWrap}>
            <InputBox
              input={input} setInput={setInput}
              onSend={() => send(input)}
              isRecording={isRecording} isLoading={isLoading}
              recordSecs={recordSecs} fmt={fmt}
              startRec={startRec} stopRec={stopRec}
              stopResponse={stopResponse}
              fileRef={fileRef} handleFile={handleFile}
            />
          </div>
          <div className="suggestion-grid" style={S.suggestions}>
            {SUGGESTIONS.map((s, i) => (
              <button key={i} className="suggestion-card" style={S.sugBtn} onClick={() => send(s.text)}>
                <span style={{ fontSize: '16px' }}>{s.icon}</span>
                <span style={{ fontSize: '13px' }}>{s.text}</span>
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Chat messages */}
      {!showHome && (
        <div ref={chatRef} className="chat-stream" style={S.chat}>
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
                  <div className="ai-answer" style={S.aiCard}>
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
                        h1: ({ node, children, ...props }) => (
                          <h1 style={{ fontSize: '16px', fontWeight: '700', marginBottom: '10px', color: 'var(--text)' }} {...props}>{children}</h1>
                        ),
                        h2: ({ node, children, ...props }) => (
                          <h2 style={{ fontSize: '15px', fontWeight: '600', marginBottom: '8px', color: 'var(--text)' }} {...props}>{children}</h2>
                        ),
                        h3: ({ node, children, ...props }) => (
                          <h3 style={{ fontSize: '14px', fontWeight: '600', marginBottom: '6px', color: 'var(--text)' }} {...props}>{children}</h3>
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
                  <button
                    style={S.readBtn}
                    onClick={() => readAloud(msg.content, i)}
                    title={speakingMessage === i ? 'Stop reading' : 'Read aloud'}
                    aria-label={speakingMessage === i ? 'Stop reading' : 'Read aloud'}
                  >
                    {speakingMessage === i
                      ? <FiSquare size={12} />
                      : <FiVolume2 size={15} />}
                    <span>{speakingMessage === i ? 'Stop' : 'Read aloud'}</span>
                  </button>
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
                <div className="loading-copy">
                  {serviceStatus === 'connecting'
                    ? 'Starting the secure medical service…'
                    : 'Reviewing your message…'}
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Sticky input */}
      {!showHome && (
        <div className="sticky-composer" style={S.stickyInput}>
          <InputBox
            input={input} setInput={setInput}
            onSend={() => send(input)}
            isRecording={isRecording} isLoading={isLoading}
            recordSecs={recordSecs} fmt={fmt}
            startRec={startRec} stopRec={stopRec}
            stopResponse={stopResponse}
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

function InputBox({ input, setInput, onSend, isRecording, isLoading, recordSecs, fmt, startRec, stopRec, stopResponse, fileRef, handleFile }) {
  return (
    <div className="composer-box" style={IB.box}>
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
              opacity: (!input.trim() && !isLoading) ? 0.35 : 1,
            }}
            onClick={isLoading ? stopResponse : onSend}
            disabled={!input.trim() && !isLoading}
            title={isLoading ? 'Stop response' : 'Send message'}
            aria-label={isLoading ? 'Stop response' : 'Send message'}
          >
            {isLoading ? <FiSquare size={13} color="#fff" /> : <FiSend size={14} color="#fff" />}
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
    minHeight: '62px', padding: '10px 28px', flexShrink: 0,
    position: 'relative',
    borderBottom: '1px solid var(--border)',
  },
  planBadge: {
    fontSize: '11px', color: 'var(--text-sub)', letterSpacing: '0.03em',
    background: 'rgba(11, 26, 32, 0.72)', border: '1px solid rgba(113, 255, 204, 0.16)',
    padding: '7px 13px', borderRadius: '20px',
  },
  // Pinned to the top bar's right edge. The button itself stays in normal flow
  // so it can't overlap the centred plan badge; the dropdown anchors to this.
  langWrap: {
    position: 'absolute', right: '24px', top: '50%',
    transform: 'translateY(-50%)',
  },
  langBtn: {
    display: 'flex', alignItems: 'center', gap: '6px',
    fontSize: '12px', color: 'var(--text-muted)',
    background: 'var(--surface)', border: '1px solid var(--border)',
    padding: '4px 12px', borderRadius: '20px', cursor: 'pointer',
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
    padding: '30px 24px 54px', gap: '22px',
  },
  homeHero: {
    display: 'flex', flexDirection: 'column',
    alignItems: 'center', gap: '10px',
  },
  heroTitle: {
    fontSize: 'clamp(42px, 6vw, 76px)', fontWeight: '720',
    letterSpacing: '-0.055em', lineHeight: '0.98',
    color: 'var(--text)', textAlign: 'center',
  },
  heroSub: {
    fontSize: 'clamp(14px, 1.5vw, 17px)', color: 'var(--text-sub)',
    textAlign: 'center', lineHeight: '1.7', maxWidth: '620px',
  },
  inputWrap: { width: '100%', maxWidth: '720px' },
  suggestions: {
    display: 'flex', flexWrap: 'wrap',
    gap: '8px', justifyContent: 'center',
    maxWidth: '760px',
  },
  sugBtn: {
    display: 'flex', alignItems: 'center', gap: '8px',
    padding: '11px 16px', borderRadius: '16px',
    border: '1px solid var(--border)', background: 'rgba(10, 25, 31, 0.64)',
    fontSize: '13px', color: 'var(--text-sub)', cursor: 'pointer',
  },
  chat: {
    flex: 1, minHeight: 0, overflowY: 'auto',
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
  readBtn: {
    display: 'flex', alignItems: 'center', gap: '6px',
    marginTop: '7px', padding: '5px 7px', borderRadius: '7px',
    color: 'var(--text-muted)', fontSize: '11px', cursor: 'pointer',
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
    background: 'rgba(11, 27, 34, 0.82)',
    border: '1px solid rgba(116, 255, 205, 0.19)',
    borderRadius: '22px',
    padding: '16px 14px 10px 19px',
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
