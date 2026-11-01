import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';
import { ToastProvider } from './context/ToastContext';
import { ModeProvider } from './context/ModeContext';
import './index.css';

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <ToastProvider>
      <ModeProvider>
        <App />
      </ModeProvider>
    </ToastProvider>
  </React.StrictMode>,
);
