import { type Player } from '../interfaces/WSMessage';
import Avatar from "boring-avatars";
import { DotLottieReact } from '@lottiefiles/dotlottie-react';

const LOTTIE_TARGET = './hiops.json';

interface PlayerSidebarCardProps {
  player: Player;
  isMe: boolean;
  isDone: boolean;
  isVotingPhase: boolean;
  onVote: () => void;
}

export default function PlayerSidebarCard({
  player,
  isMe,
  isDone,
  isVotingPhase,
  onVote
}: PlayerSidebarCardProps) {
  const isClickable = isVotingPhase && !isMe;

  return (
    <div
      onClick={isClickable ? onVote : undefined}
      className={`relative flex items-center p-3 rounded-2xl min-w-[150px] transition-all duration-200 border-2
        ${isClickable
          ? 'cursor-pointer border-transparent hover:border-red-400 hover:shadow-lg hover:-translate-y-1 bg-white'
          : 'border-transparent bg-white/60'
        }
        ${isMe ? 'opacity-80 grayscale-[20%]' : ''}
      `}
    >
      <div className={`w-12 h-12 rounded-full flex items-center justify-center shrink-0 mr-3 shadow-inner overflow-hidden ${
        isVotingPhase && !isMe ? 'bg-red-50' : 'bg-transparent'
      }`}>
        {isVotingPhase && !isMe ? (
          <DotLottieReact src={LOTTIE_TARGET} loop autoplay style={{ width: '70%', height: '70%' }} />
        ) : (
          <Avatar name={player.user_id} variant="beam" size={48} />
        )}
      </div>

      <div className="flex-1 min-w-0 overflow-hidden">
        <div className="font-extrabold text-gray-800 truncate text-[15px]">
          {player.username} {isMe && <span className="text-gray-400 font-normal">(You)</span>}
        </div>
        <div className={`text-xs font-semibold truncate ${isDone ? 'text-green-500' : 'text-gray-400'}`}>
          {isVotingPhase
            ? (isDone ? 'Vote cast' : 'Choosing...')
            : (isDone ? 'Waiting...' : 'Typing...')
          }
        </div>
      </div>

      {isDone && (
        <div className="w-3 h-3 bg-green-500 rounded-full shrink-0 ml-2 shadow-[0_0_8px_rgba(34,197,94,0.6)]"></div>
      )}

      {player.is_ai && (
        <div className="absolute -top-2 -right-2 bg-purple-600 text-white text-[10px] font-black px-2 py-1 rounded-full shadow-md z-10 rotate-12">
          BOT
        </div>
      )}
    </div>
  );
}
