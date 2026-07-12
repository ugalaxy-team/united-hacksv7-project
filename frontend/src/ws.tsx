import { io, Socket } from 'socket.io-client';
import { toast } from 'sonner';
import { type ServerMessage } from './interfaces/WSMessage';

export let socket: Socket | null = null;

export const initSocket = (username: string, userId: string): Socket => {
  if (socket) {
    socket.auth = { username, userId };
    socket.disconnect().connect();
    return socket;
  }

  socket = io('http://127.0.0.1:8000', {
    auth: { username, userId },
    transports: ['websocket', 'polling'],
    autoConnect: true,
  });

  socket.on('connect', () => {
    console.log('✅ Connected to the game server');
  });

  socket.on('connect_error', (err) => {
    console.error('❌ Connection error:', err.message);
    toast.error('Lost connection to the server. Please check your connection.');
  });

  socket.on('disconnect', (reason) => {
    console.warn('⚠️ Disconnected:', reason);
    if (reason === 'io server disconnect') {
      socket?.connect();
    }
  });

  socket.on('message', (data: ServerMessage) => {
    if (data.type === 'error') {
      toast.error(data.message);
    } else if (data.type === 'success') {
      toast.success(data.message);
    } else {
      toast.info(data.message);
    }
  });

  return socket;
};

export const disconnectSocket = () => {
  if (socket) {
    socket.disconnect();
    socket = null;
  }
};
