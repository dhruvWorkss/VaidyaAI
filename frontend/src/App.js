import React, { useState, useRef, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Sidebar from './components/Sidebar';
import PatientPage from './pages/PatientPage';
import DoctorPage from './pages/DoctorPage';
import { warmUpApi } from './services/api';
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

  return (
    <Router>
      <div style={{ display: 'flex', height: '100vh' }}>
        <Sidebar
          convos={convos}
          activeId={activeId}
          onNew={newConvo}
          onSelect={setActiveId}
        />
        <Routes>
          <Route path="/" element={
            <PatientPage
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
