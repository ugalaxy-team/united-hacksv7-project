import React, { useState, useEffect, type ReactNode } from 'react';
import { GameContext, type ViewState } from './GameContext';
import { type GameState, type Message, type Vote, type QueueUpdateResponse } from '../interfaces/WSMessage';
import { socket, initSocket } from '../ws';

export const GameProvider = ({ children }: { children: ReactNode }) => {
  const [userId, setUserId] = useState<string | null>(localStorage.getItem('userId'));
  const [username, setUsername] = useState<string | null>(localStorage.getItem('username'));
  const [view, setView] = useState<ViewState>('hero');
  const [playerAmount, setPlayerAmount] = useState<number>(0);
  const [game, setGame] = useState<GameState | null>(null);

  const login = (name: string) => {
    const newId = crypto.randomUUID();
    localStorage.setItem('userId', newId);
    localStorage.setItem('username', name);
    setUserId(newId);
    setUsername(name);

    initSocket(name, newId);
    setView('queue');
  };

  const leaveQueue = () => {
    socket?.emit('queue:leave', { queue: 'standard' });
    setView('hero');
    setPlayerAmount(0);
  };

  useEffect(() => {
    if (userId && username && !socket) {
      initSocket(username, userId);
    }

    if (!socket) return;

    const onQueueUpdate = (data: QueueUpdateResponse) => setPlayerAmount(data.player_amount);

    socket.on('queue:player_joined', onQueueUpdate);
    socket.on('queue:player_left', onQueueUpdate);
    socket.on('game:start', (newGame: GameState) => { setGame(newGame); setView('game'); });
    socket.on('game:message_sent', (msg: Message) => setGame((prev) => prev ? { ...prev, messages: [...prev.messages, msg] } : prev));
    socket.on('game:voting', () => setGame((prev) => prev ? { ...prev, phase: 'voting' } : prev));
    socket.on('game:vote_casted', (vote: Vote) => setGame((prev) => prev ? { ...prev, current_votes: [...prev.current_votes, vote] } : prev));
    socket.on('game:results', (votes: Vote[]) => setGame((prev) => prev ? { ...prev, phase: 'results', current_votes: votes } : prev));
    socket.on('game:new_round', (updatedGame: GameState) => setGame((prev) => prev ? { ...prev, phase: 'chatting', round: updatedGame.round, current_votes: [] } : prev));
    socket.on('game:end', (finalGame: GameState) => { setGame(finalGame); setView('gameover'); });

    return () => {
      socket?.off('queue:player_joined', onQueueUpdate);
      socket?.off('queue:player_left', onQueueUpdate);
      socket?.off('game:start');
      socket?.off('game:message_sent');
      socket?.off('game:voting');
      socket?.off('game:vote_casted');
      socket?.off('game:results');
      socket?.off('game:new_round');
      socket?.off('game:end');
    };
  }, [userId, username]);

  return (
    <GameContext.Provider value={{ userId, username, view, playerAmount, game, login, setView, leaveQueue }}>
      {children}
    </GameContext.Provider>
  );
};
