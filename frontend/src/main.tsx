import { createRoot } from 'react-dom/client';
import App from './App.tsx';
import './index.css';
import { GameProvider } from './context/GameProvider';
import { Toaster } from 'sonner';

createRoot(document.getElementById('root')!).render(
  <GameProvider>
    <App />
    <Toaster richColors position="top-center" />
  </GameProvider>
);
