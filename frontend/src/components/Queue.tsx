import { SOCKET_URL, socketConfig } from "@/ws";
import { useEffect, useState } from "react";
import { io } from 'socket.io-client';

const Queue = () => {
    const username = localStorage.getItem('username');
    const userId = localStorage.getItem('userId');
    const [isJoined, setIsJoined] = useState(false);

    useEffect(() => {
        if (!username || !userId) return;
        if (!isJoined) return;

        const queue = io(SOCKET_URL, { ...socketConfig, auth: { username, userId } });

        return () => {
            queue.disconnect();
            setIsJoined(false);
        }
    }, [isJoined, username, userId]);

    return <section className="flex justify-center items-center">
        <h1>Queue</h1>
        {isJoined ? 
        <div>Queue joined. Waiting for players!</div>
        : <button onClick={() => setIsJoined(true)}>Join queue!</button>}
    </section>;
}
 
export default Queue;