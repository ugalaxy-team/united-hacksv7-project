import { SOCKET_URL, socketConfig, onMessage } from "@/ws";
import { useEffect, useRef, useState } from "react";
import { io, Socket } from 'socket.io-client';
import Game from "./Game";
import QueueCard from "./QueueCard";

interface GameMode {
    name: string;
    player_count: number;
    rounds: number;
    messages_per_round: number;
    chatting_duration: number;
    voting_duration: number;
    results_duration: number;
}

const Queue = () => {
    const username = localStorage.getItem('username')!;
    const userId = localStorage.getItem('userId')!;
    const [gameModes, setGameModes] = useState<GameMode[]>([]);
    const [joinedQueue, setJoinedQueue] = useState<string | null>(null);
    const [playerCounts, setPlayerCounts] = useState<Record<string, number>>({});
    const [gameData, setGameData] = useState<any>(null);
    const socketRef = useRef<Socket>(null);

    useEffect(() => {
        if (!username || !userId) return;
        const socket = io(SOCKET_URL, { ...socketConfig, auth: { username, userId } });
        socketRef.current = socket;
        const cleanupMessage = onMessage(socket);

        socket.emit('queue:list');

        socket.on('queue:list', (data: GameMode[]) => {
            setGameModes(data);
        });

        socket.on('queue:player_left', (data: { id: string; game_mode: string; player_amount: number }) => {
            setPlayerCounts(prev => ({ ...prev, [data.game_mode]: data.player_amount }));
            if (data.id === userId) setJoinedQueue(null);
        });

        socket.on('queue:player_joined', (data: { id: string; game_mode: string; player_amount: number }) => {
            setPlayerCounts(prev => ({ ...prev, [data.game_mode]: data.player_amount }));
            if (data.id === userId) setJoinedQueue(data.game_mode);
        });

        socket.on('game:start', (data) => {
            setGameData(data);
        });

        return () => {
            cleanupMessage();
            socket.disconnect();
        };
    }, []);

    if (gameData && socketRef.current) {
        return <Game socket={socketRef.current} username={username} userId={userId} gameData={gameData} onGameEnd={() => setGameData(null)} />;
    }

    return <section>
        <h1>Queue</h1>
        {gameModes.map(gm => (
            <QueueCard
                key={gm.name}
                gameMode={gm}
                isJoined={joinedQueue === gm.name}
                playerCount={playerCounts[gm.name] ?? 0}
                onJoin={() => socketRef.current?.emit('queue:join', { queue: gm.name })}
                onLeave={() => socketRef.current?.emit('queue:leave', { queue: gm.name })}
            />
        ))}
    </section>;
}

export default Queue;
