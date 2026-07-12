import { useGame } from '../context/GameContext';
import { DotLottieReact } from '@lottiefiles/dotlottie-react';

const LOTTIE_VICTORY = '/shok.json';
const LOTTIE_DEFEAT = '/baraban.json';

export default function GameOver() {
  const { game, setView } = useGame();

  if (!game || !game.ai_player) return null;

  const isHumanVictory = game.victory;

  return (
    <div className={`flex flex-col items-center justify-center min-h-screen p-6 transition-colors duration-700 ${
      isHumanVictory ? 'bg-green-500 text-white' : 'bg-red-500 text-white'
    }`}>

      <div className="w-64 h-64 mb-8 drop-shadow-2xl cursor-default select-none">
        <DotLottieReact
          src={isHumanVictory ? LOTTIE_VICTORY : LOTTIE_DEFEAT}
          loop
          autoplay
          style={{ width: '100%', height: '100%' }}
        />
      </div>

      <h1 className="font-display text-4xl md:text-6xl font-black mb-6 text-center tracking-tight drop-shadow-md">
        {isHumanVictory ? 'Humans Win!' : 'The AI fooled everyone!'}
      </h1>

      <div className="bg-white/20 backdrop-blur-md p-8 rounded-3xl mb-12 text-center border border-white/30 shadow-xl w-full max-w-md">
        <p className="text-lg md:text-xl font-bold mb-3 opacity-90">
          The AI undercover was:
        </p>
        <div className="inline-block bg-white text-gray-900 px-6 py-3 rounded-2xl">
          <p className="font-display text-3xl md:text-4xl font-black drop-shadow-sm">
            {game.ai_player.username}
          </p>
        </div>
      </div>

      <button
        onClick={() => setView('hero')}
        className="bg-white text-gray-900 px-10 py-5 rounded-2xl font-black text-xl shadow-[0_8px_0_rgba(0,0,0,0.15)] hover:shadow-[0_4px_0_rgba(0,0,0,0.15)] hover:translate-y-[4px] active:shadow-none active:translate-y-[8px] transition-all"
      >
        Play again
      </button>

    </div>
  );
}
