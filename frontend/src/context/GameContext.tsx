import { createContext, useContext } from 'react';
import type { GameState } from '../interfaces/WSMessage';

export type ViewState = 'hero' | 'queue' | 'game' | 'gameover';

export interface GameContextProps {
  userId: string | null;
  username: string | null;
  view: ViewState;
  playerAmount: number;
  game: GameState | null;

  login: (name: string) => void;
  setView: (view: ViewState) => void;
  leaveQueue: () => void;
}

export const GameContext = createContext<GameContextProps | undefined>(undefined);

export const useGame = () => {
  const context = useContext(GameContext);
  if (!context) {
    throw new Error('useGame must be used within a GameProvider');
  }
  return context;
};
