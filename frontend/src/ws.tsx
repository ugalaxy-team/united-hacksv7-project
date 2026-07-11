import type { Socket } from 'socket.io-client';
import type { WSMessage } from "@/interfaces/WSMessage";
import { toast } from "sonner";

export const SOCKET_URL = import.meta.env.PROD ? undefined : import.meta.env.VITE_BACKEND_URL;

export const socketConfig = {
    withCredentials: true,
    transports: ['websocket'],
    upgrade: false, 
};

export const onMessage = (socket: Socket) => {
    const handler = (data: WSMessage) => {
        if (data.type === 'success') {
            toast.success(data.message);
        } else {
            toast.error(data.message);
        }
    };
    socket.on('message', handler);
    return () => socket.off('message', handler);
};