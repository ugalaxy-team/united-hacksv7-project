
export const SOCKET_URL = import.meta.env.PROD ? undefined : import.meta.env.VITE_BACKEND_URL;

export const socketConfig = {
    withCredentials: true,
    transports: ['websocket'],
    upgrade: false, 
};