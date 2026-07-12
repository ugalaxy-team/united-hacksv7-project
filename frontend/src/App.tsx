import { useGame } from './context/GameContext';
import Hero from './components/Hero';
import Queue from './components/Queue';
import Game from './components/Game';
import GameOver from './components/GameOver';
import './App.css';

export default function App() {
  const { view } = useGame();

  return (
    <div className="app-shell min-h-screen text-gray-800 antialiased flex flex-col">
      <div className="app-blobs">
        <div className="app-blob app-blob-1" />
        <div className="app-blob app-blob-2" />
        <div className="app-blob app-blob-3" />
      </div>
      {view === 'hero' && <Hero />}
      {view === 'queue' && <Queue />}
      {view === 'game' && <Game />}
      {view === 'gameover' && <GameOver />}
    </div>
  );
}
