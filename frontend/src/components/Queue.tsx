import { useEffect, useState } from 'react';
import { useGame } from '../context/GameContext';
import { socket } from '../ws';
import { DotLottieReact } from '@lottiefiles/dotlottie-react';

const LOTTIE_WAITING = '/sleep.json';

interface GameMode {
  name: string;
  player_count: number;
  rounds: number;
  messages_per_round: number;
  chatting_duration: number;
  voting_duration: number;
  results_duration: number;
}

export default function Queue() {
  const { playerAmount, resetPlayerAmount } = useGame();
  const [gameModes, setGameModes] = useState<GameMode[]>([]);
  const [joinedQueue, setJoinedQueue] = useState<string | null>(null);

  useEffect(() => {
    socket?.emit('queue:list');

    socket?.on('queue:list', (data: GameMode[]) => {
      setGameModes(data);
    });

    return () => {
      socket?.off('queue:list');
    };
  }, []);

  const handleJoin = (queueName: string) => {
    resetPlayerAmount();
    socket?.emit('queue:join', { queue: queueName });
    setJoinedQueue(queueName);
  };

  const handleLeave = () => {
    if (joinedQueue) {
      socket?.emit('queue:leave', { queue: joinedQueue });
      setJoinedQueue(null);
      resetPlayerAmount();
    }
  };

  return (
    <div className="flex flex-col items-center flex-1 p-6 overflow-y-auto w-full max-w-md mx-auto custom-scrollbar">
      <div className="w-32 h-32 mt-4 mb-6 flex items-center justify-center cursor-default select-none drop-shadow-md">
        <DotLottieReact src={LOTTIE_WAITING} loop autoplay style={{ width: '100%', height: '100%' }} />
      </div>

      <h2 className="font-display text-3xl font-black text-gray-800 mb-8 tracking-tight">Choose a mode</h2>

      {gameModes.length === 0 ? (
        <p className="text-gray-400 animate-pulse font-bold text-lg">Loading rooms...</p>
      ) : (
        <div className="w-full flex flex-col gap-5 mb-8">
          {gameModes.map((gm) => {
            const isThisJoined = joinedQueue === gm.name;
            const currentPlayers = isThisJoined ? Math.max(playerAmount, 1) : 0;

            return (
              <div
                key={gm.name}
                className={`bg-white p-5 rounded-3xl border-2 transition-all duration-300 shadow-sm flex flex-col ${
                  isThisJoined ? 'border-green-500 shadow-[0_0_15px_rgba(34,197,94,0.15)] scale-[1.02]' : 'border-green-100 hover:border-green-300'
                }`}
              >
                <div className="flex justify-between items-center mb-4">
                  <h3 className="font-display text-xl font-extrabold text-gray-800 capitalize tracking-wide">{gm.name}</h3>
                  <span className={`text-sm font-bold px-3 py-1 rounded-full ${isThisJoined ? 'bg-green-500 text-white' : 'bg-green-50 text-green-600'}`}>
                    {currentPlayers} / {gm.player_count} found
                  </span>
                </div>

                <div className="flex flex-wrap gap-2 mb-5 text-xs font-bold text-gray-500">
                  <span className="bg-gray-100 px-2 py-1.5 rounded-lg border border-gray-200">Rounds: {gm.rounds}</span>
                  <span className="bg-gray-100 px-2 py-1.5 rounded-lg border border-gray-200">Messages: {gm.messages_per_round}</span>
                </div>

                {joinedQueue ? (
                  isThisJoined ? (
                    <button
                      onClick={handleLeave}
                      className="w-full bg-red-50 text-red-500 font-bold py-3 rounded-2xl hover:bg-red-100 active:scale-95 transition-all"
                    >
                      Cancel search
                    </button>
                  ) : (
                    <button disabled className="w-full bg-gray-50 text-gray-400 font-bold py-3 rounded-2xl cursor-not-allowed border border-gray-100">
                      Waiting...
                    </button>
                  )
                ) : (
                  <button
                    onClick={() => handleJoin(gm.name)}
                    className="w-full bg-green-500 text-white font-bold py-3.5 rounded-2xl active:scale-95 transition-all shadow-[0_4px_0_rgb(21,128,61)] hover:shadow-[0_2px_0_rgb(21,128,61)] hover:translate-y-[2px]"
                  >
                    Join
                  </button>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
