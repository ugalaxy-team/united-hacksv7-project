import { useEffect, useState } from 'react';
import { useGame } from '../context/GameContext';
import { DotLottieReact } from '@lottiefiles/dotlottie-react';

const BACKEND_URL = import.meta.env.VITE_BACKEND_URL || 'http://127.0.0.1:8000';
const LOTTIE_MASCOT = '/write.json';

const RefreshIcon = ({ size = 18 }: { size?: number }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round">
    <path d="M3 12a9 9 0 0 1 15.3-6.4L21 8" />
    <path d="M21 3v5h-5" />
    <path d="M21 12a9 9 0 0 1-15.3 6.4L3 16" />
    <path d="M3 21v-5h5" />
  </svg>
);

export default function Hero() {
  const { enterQueue } = useGame();

  const [currentName, setCurrentName] = useState(localStorage.getItem('username') || 'Loading...');

  const fetchUsernameFromBackend = async () => {
    try {
      const res = await fetch(`${BACKEND_URL}/api/username`);
      const data = await res.json();
      setCurrentName(data.username);
      localStorage.setItem('username', data.username);
    } catch (error) {
      console.error(error);
    }
  };

  useEffect(() => {
    if (!localStorage.getItem('userId')) {
      localStorage.setItem('userId', crypto.randomUUID());
    }

    if (!localStorage.getItem('username')) {
      fetch(`${BACKEND_URL}/api/username`)
        .then(res => res.json())
        .then(data => {
          localStorage.setItem('username', data.username);
          setCurrentName(data.username);
        })
        .catch(console.error);
    }
  }, []);

  const handlePlay = () => {
    if (!localStorage.getItem('userId')) {
      localStorage.setItem('userId', crypto.randomUUID());
    }
    enterQueue();
  };

  return (
    <div className="flex flex-col items-center justify-center flex-1 p-6">
      <div className="w-40 h-40 mb-6 bg-green-100 rounded-full flex items-center justify-center shadow-inner overflow-hidden">
        <DotLottieReact src={LOTTIE_MASCOT} loop autoplay style={{ width: '75%', height: '75%' }} />
      </div>

      <h1 className="font-display text-4xl md:text-5xl font-extrabold text-green-700 mb-2 tracking-tight">
        Spot the AI
      </h1>
      <p className="text-gray-500 mb-8 text-center font-medium max-w-sm">
        Which of you is human, and which is the machine?
      </p>

      <div className="flex flex-col items-center gap-4 mb-8">
        <div className="flex items-center gap-3 bg-white px-5 py-3 rounded-2xl border-2 border-green-200 shadow-sm">
          <span className="font-bold text-gray-700 text-lg">{currentName}</span>
          <button
            type="button"
            onClick={fetchUsernameFromBackend}
            aria-label="Regenerate nickname"
            className="text-green-600 active:scale-90 transition-transform"
          >
            <RefreshIcon size={18} />
          </button>
        </div>
      </div>

      <button
        type="button"
        onClick={handlePlay}
        disabled={currentName === 'Loading...'}
        className="w-full max-w-xs bg-green-500 text-white font-bold py-4 text-lg rounded-2xl shadow-[0_6px_0_rgb(21,128,61)] hover:shadow-[0_4px_0_rgb(21,128,61)] hover:translate-y-[2px] active:shadow-none active:translate-y-[6px] transition-all disabled:opacity-50"
      >
        Play!
      </button>
    </div>
  );
}
