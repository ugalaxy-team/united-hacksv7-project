import React, { useState } from 'react';
import { useGame } from '../context/GameContext';
import generateRandomUsername from 'generate-random-username';
import { DotLottieReact } from '@lottiefiles/dotlottie-react';

const LOTTIE_MASCOT = '/write.json';

export default function Hero() {
  const [name, setName] = useState('');
  const { login } = useGame();

  const handlePlay = (e: React.FormEvent) => {
    e.preventDefault();

    const finalName = name.trim() || generateRandomUsername();
    login(finalName);
  };

  return (
    <div className="flex flex-col items-center justify-center flex-1 p-6">
      <div className="w-44 h-44 mb-8 bg-green-100 rounded-full flex items-center justify-center shadow-inner transform transition-transform hover:scale-105 duration-300 overflow-hidden">
        <DotLottieReact src={LOTTIE_MASCOT} loop autoplay style={{ width: '75%', height: '75%' }} />
      </div>

      <h1 className="font-display text-4xl md:text-5xl font-extrabold text-green-700 mb-2 tracking-tight">
        AI-Spy
      </h1>
      <p className="text-gray-500 mb-10 text-center font-medium max-w-sm">
        Which of you is human, and which is the machine?
      </p>

      <form onSubmit={handlePlay} className="w-full max-w-xs flex flex-col items-center">
        <input
          type="text"
          placeholder="Your nickname..."
          value={name}
          onChange={(e) => setName(e.target.value)}
          className="w-full px-6 py-4 text-lg rounded-2xl bg-white border-2 border-green-200 focus:outline-none focus:border-green-500 focus:ring-4 focus:ring-green-500/20 shadow-sm mb-6 transition-all placeholder:text-gray-400 text-center font-semibold text-gray-700"
        />

        <button
          type="submit"
          className="w-full bg-green-500 text-white font-bold py-4 text-lg rounded-2xl shadow-[0_6px_0_rgb(21,128,61)] hover:shadow-[0_4px_0_rgb(21,128,61)] hover:translate-y-[2px] active:shadow-none active:translate-y-[6px] transition-all"
        >
          Play!
        </button>
      </form>
    </div>
  );
}
