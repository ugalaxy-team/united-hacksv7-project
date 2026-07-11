import type { Socket } from 'socket.io-client';
import { useEffect, useState } from "react";
import { onMessage } from "@/ws";

interface GameProps {
    socket: Socket;
    username: string;
    userId: string;
}

const Game = ({ socket, username, userId }: GameProps) => {
    const [gameState, setGameState] = useState<string>('connected');

    useEffect(() => {
        const cleanupMessage = onMessage(socket);

        return () => {
            cleanupMessage();
        };
    }, [socket]);

    return <section className="flex justify-center items-center">
        <h1>Game</h1>
        <p>Game started! Waiting for game logic to be implemented...</p>
        <p>Playing as: {username}</p>
    </section>;
}

export default Game;
