import React, { useState, useRef, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Sidebar from './components/Sidebar';
import PatientPage from './pages/PatientPage';
import DoctorPage from './pages/DoctorPage';
import { clearSession, getSessions, warmUpApi } from './services/api';
import './index.css';

export default function App() {
  const [convos, setConvos] = useState([]);
  const [activeId, setActiveId] = useState('home');
  const currentSessionRef = useRef('home');
  const [serviceStatus, setServiceStatus] = useState('connecting');

  useEffect(() => {
    const controller = new AbortController();
    warmUpApi(controller.signal)
      .then(() => setServiceStatus('ready'))
      .catch(err => {
        if (err.name !== 'AbortError') setServiceStatus('offline');
      });
    return () => controller.abort();
  }, []);

  useEffect(() => {
    getSessions()
      .then(sessions => setConvos(current => {
        const saved = sessions.map(session => ({
          id: session.id,
          title: session.last_message
            ? session.last_message.slice(0, 35) + (session.last_message.length > 35 ? '...' : '')
            : 'Consultation',
        }));
        const savedIds = new Set(saved.map(session => session.id));
        return [...current.filter(session => !savedIds.has(session.id)), ...saved];
      }))
      .catch(err => console.error('Could not load consultations:', err));
  }, []);

  const newConvo = () => {
    const id = Date.now().toString();
    setConvos(prev => [{ id, title: 'New consultation' }, ...prev]);
    setActiveId(id);
    currentSessionRef.current = id;
    return id;
  };

  const updateTitle = (id, title) => {
    setConvos(prev => prev.map(c => c.id === id ? { ...c, title } : c));
  };

  const deleteConvo = async (id) => {
    await clearSession(id);
    setConvos(prev => prev.filter(c => c.id !== id));
    if (activeId === id) {
      setActiveId('home');
      currentSessionRef.current = 'home';
    }
  };

  return (
    <Router>
      <div style={{ display: 'flex', height: '100vh' }}>
        <Sidebar
          convos={convos}
          activeId={activeId}
          onNew={newConvo}
          onSelect={setActiveId}
          onDelete={deleteConvo}
        />
        <Routes>
          <Route path="/" element={
            <PatientPage
              key={activeId}
              sessionId={activeId}
              isHome={activeId === 'home'}
              onFirstMessage={newConvo}
              onUpdateTitle={updateTitle}
              serviceStatus={serviceStatus}
            />
          } />
          <Route path="/doctor" element={<DoctorPage />} />
        </Routes>
      </div>
    </Router>
  );
}
