import React, { useState, useRef, useEffect } from 'react';
import { useGame } from '../context/GameContext';
import { socket } from '../ws';
import MessageCard from './MessageCard';
import PlayerSidebarCard from './PlayerSidebarCard';
import { DotLottieReact } from '@lottiefiles/dotlottie-react';

const LOTTIE_DETECTIVE = '/hiops.json';
const LOTTIE_RESULTS = 'blabla.json';
const LOTTIE_SEND = '/run.json';

export default function Game() {
  const { game, userId } = useGame();
  const [text, setText] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [game?.messages, game?.phase]);

  if (!game || !userId) return null;

  const myMessageCount = game.messages.filter(
    (m) => m.sender.user_id === userId && m.round === game.round
  ).length;

  const canChat = game.phase === 'chatting' && myMessageCount < game.messages_per_round;

  const sendMessage = (e: React.FormEvent) => {
    e.preventDefault();
    if (!text.trim() || !canChat) return;
    socket?.emit('game:message', { message: text });
    setText('');
  };

  const castVote = (suspectId: string) => {
    if (game.phase !== 'voting') return;
    socket?.emit('game:vote', { user_id: suspectId });
  };

  return (
    <div className="flex flex-col h-[100dvh] md:flex-row bg-transparent overflow-hidden">

      <div className="bg-white p-3 md:w-72 md:h-full flex flex-row md:flex-col gap-3 overflow-x-auto md:overflow-y-auto shrink-0 border-b md:border-b-0 md:border-r border-green-100 shadow-sm z-20 sticky top-0 custom-scrollbar">

        <div className="hidden md:flex flex-col items-center p-4 bg-green-50 rounded-2xl mb-4 border border-green-100">
          <span className="text-sm text-green-600 font-bold uppercase tracking-wider">Round</span>
          <span className="font-display text-3xl font-black text-green-800">{game.round} <span className="text-xl text-green-400">/ {game.max_rounds}</span></span>
        </div>

        <div className="md:hidden flex items-center justify-center min-w-[80px] bg-green-50 rounded-2xl border border-green-100 font-bold text-green-800 flex-col leading-tight">
          <span className="text-[10px] text-green-600 uppercase">Round</span>
          <span>{game.round}/{game.max_rounds}</span>
        </div>

        {game.players.map((p) => {
          const msgCount = game.messages.filter(
            (m) => m.sender.user_id === p.user_id && m.round === game.round
          ).length;
          const hasVoted = game.current_votes.some((v) => v.vote_by.user_id === p.user_id);

          return (
            <PlayerSidebarCard
              key={p.user_id}
              player={p}
              isMe={p.user_id === userId}
              isDone={game.phase === 'chatting' ? msgCount >= game.messages_per_round : hasVoted}
              isVotingPhase={game.phase === 'voting'}
              onVote={() => castVote(p.user_id)}
            />
          );
        })}
      </div>

      <div className="flex-1 flex flex-col relative overflow-hidden">

        <div className={`flex-1 p-4 md:p-8 overflow-y-auto custom-scrollbar transition-all duration-500 ${
          game.phase !== 'chatting' ? 'blur-md scale-95 opacity-40 pointer-events-none' : ''
        }`}>
          {game.messages.map((m, idx) => (
            <MessageCard key={idx} message={m} isMe={m.sender.user_id === userId} />
          ))}
          <div ref={messagesEndRef} />
        </div>

        {game.phase === 'chatting' && (
          <div className="p-3 md:p-6 bg-white border-t border-gray-100 shadow-[0_-4px_20px_rgba(0,0,0,0.02)] z-10">
            <form onSubmit={sendMessage} className="flex gap-2 max-w-4xl mx-auto relative">
              <input
                type="text"
                value={text}
                onChange={(e) => setText(e.target.value)}
                disabled={!canChat}
                placeholder={canChat ? "Type a message..." : "Waiting for other players..."}
                className="flex-1 px-5 py-4 bg-gray-50 border border-gray-200 rounded-2xl focus:outline-none focus:ring-2 focus:ring-green-400 focus:bg-white disabled:opacity-60 transition-all font-medium text-gray-700"
              />
              <button
                type="submit"
                disabled={!canChat || !text.trim()}
                className="bg-green-500 text-white px-6 md:px-8 py-4 rounded-2xl font-bold disabled:opacity-50 disabled:cursor-not-allowed hover:bg-green-600 active:scale-95 transition-all shadow-sm flex items-center justify-center"
              >
                <span className="hidden md:inline">Send</span>
                <span className="md:hidden w-6 h-6">
                  <DotLottieReact src={LOTTIE_SEND} loop autoplay style={{ width: '100%', height: '100%' }} />
                </span>
              </button>
            </form>

            <div className="text-center mt-2 text-xs font-bold text-gray-400">
              Messages: {myMessageCount} / {game.messages_per_round}
            </div>
          </div>
        )}

        {game.phase === 'voting' && (
          <div className="absolute inset-0 bg-white/60 backdrop-blur-sm flex flex-col items-center justify-center p-6 z-10">
            <div className="w-40 h-40 mb-6 drop-shadow-lg">
              <DotLottieReact src={LOTTIE_DETECTIVE} loop autoplay style={{ width: '100%', height: '100%' }} />
            </div>
            <h2 className="font-display text-3xl md:text-5xl font-black text-red-500 mb-4 text-center tracking-tight">
              Who among them is the AI?
            </h2>
            <p className="text-gray-600 font-bold text-lg md:text-xl text-center bg-white px-6 py-3 rounded-2xl shadow-sm border border-gray-100">
              Tap a player in the list to cast your vote!
            </p>
          </div>
        )}

        {game.phase === 'results' && (
           <div className="absolute inset-0 bg-green-500 flex flex-col items-center justify-center p-6 z-20 text-white">
             <div className="w-32 h-32 mb-6">
               <DotLottieReact src={LOTTIE_RESULTS} loop autoplay style={{ width: '100%', height: '100%' }} />
             </div>
             <h2 className="font-display text-3xl font-black mb-8">Round Results</h2>

             <div className="w-full max-w-md bg-white/10 rounded-3xl p-6 backdrop-blur-md border border-white/20">
               {game.current_votes.length === 0 ? (
                 <p className="text-center font-bold text-xl">No one voted</p>
               ) : (
                 game.current_votes.map((v, i) => (
                   <div key={i} className="flex justify-between items-center text-lg mb-3 last:mb-0 border-b border-white/10 pb-2 last:border-0 last:pb-0">
                     <span className="font-bold">{v.vote_by.username}</span>
                     <span className="text-white/60 mx-2 text-sm">→</span>
                     <span className="font-black text-red-200">{v.vote_for.username}</span>
                   </div>
                 ))
               )}
             </div>

             <p className="mt-10 font-bold opacity-80 animate-pulse text-lg">
               Preparing the next round...
             </p>
           </div>
        )}
      </div>
    </div>
  );
}
