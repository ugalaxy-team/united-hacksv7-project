import { SOCKET_URL, socketConfig, onMessage } from "@/ws";
import { useEffect, useRef, useState } from "react";
import { io, Socket } from 'socket.io-client';
import Game from "./Game";

const Queue = () => {
    const username = localStorage.getItem('username')!;
    const userId = localStorage.getItem('userId')!;
    const [isJoined, setIsJoined] = useState(false);
    const [playerCount, setPlayerCount] = useState(0);
    const [gameData, setGameData] = useState<any>(null);
    const socketRef = useRef<Socket>(null);

    useEffect(() => {
        if (!username || !userId) return;
        socketRef.current = io(SOCKET_URL, { ...socketConfig, auth: { username, userId } });
        const cleanupMessage = onMessage(socketRef.current);

        socketRef.current.on('queue:player_left', (data: { player_amount: number }) => {
            setPlayerCount(data.player_amount);
        });

        socketRef.current.on('queue:player_joined', (data: { player_amount: number }) => {
            setPlayerCount(data.player_amount);
        });

        socketRef.current.on('game:start', (data) => {
            setGameData(data);
        });

        return () => {
            cleanupMessage();
            if (socketRef.current) {
                socketRef.current.disconnect();
            }
        };
    }, []);

    if (gameData && socketRef.current) {
        return <Game socket={socketRef.current} username={username} userId={userId} gameData={gameData} onGameEnd={() => setGameData(null)} />;
    }

    const handleJoin = () => {
        if (!socketRef.current || !socketRef.current.connected) return;
        socketRef.current.emit('queue:join', { queue: 'standard' }, (data?: { ok: boolean; player_amount: number }) => {
            if (!data?.ok) return;
            setIsJoined(true);
            setPlayerCount(data.player_amount);
        });
    };
    const handleLeave = () => {
        if (!socketRef.current || !socketRef.current.connected) return;
        socketRef.current.emit('queue:leave', { queue: 'standard' }, (data?: { ok: boolean }) => {
            if (!data?.ok) return;
            setIsJoined(false);
            setPlayerCount(0);
        });
    };

    return <section className="flex justify-center items-center">
        <h1>Queue</h1>
        {isJoined ?
        <div>
            <p>Players in queue: {playerCount}</p>
            <p>Waiting for players!</p>
            <button className="bg-red-500" onClick={handleLeave}>Leave queue!</button>
        </div>
        : <button className="bg-green-500" onClick={handleJoin}>Join queue!</button>}
    </section>;
}

export default Queue;