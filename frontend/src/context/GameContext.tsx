import { createContext, useContext } from 'react';
import type { GameState } from '../interfaces/WSMessage';

export type ViewState = 'hero' | 'queue' | 'game' | 'gameover';

export interface GameContextProps {
  userId: string;
  username: string;
  avatarSeed: string;
  view: ViewState;
  playerAmount: number;
  game: GameState | null;

  regenerateUsername: () => void;
  regenerateAvatar: () => void;
  enterQueue: () => void;
  setView: (view: ViewState) => void;
  leaveQueue: () => void;
  resetPlayerAmount: () => void;
}

export const GameContext = createContext<GameContextProps | undefined>(undefined);

export const useGame = () => {
  const context = useContext(GameContext);
  if (!context) {
    throw new Error('useGame must be used within a GameProvider');
  }
  return context;
};
