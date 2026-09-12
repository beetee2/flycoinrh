import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { App } from './App';
import { Lab } from './Lab';
import './styles.css';

createRoot(document.getElementById('root')!).render(<StrictMode>{window.location.pathname === '/lab' ? <Lab /> : <App />}</StrictMode>);
