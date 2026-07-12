import { type Message } from '../interfaces/WSMessage';
import Avatar from "boring-avatars";

interface MessageCardProps {
  message: Message;
  isMe: boolean;
}

export default function MessageCard({ message, isMe }: MessageCardProps) {
  return (
    <div className={`flex flex-col mb-4 w-full ${isMe ? 'items-end' : 'items-start'}`}>
      {!isMe && (
        <div className="flex items-center mb-1 ml-2">
          <Avatar name={message.sender.user_id} variant="beam" size={20} />
          <span className="text-xs text-gray-500 ml-2 font-bold">
            {message.sender.username}
          </span>
        </div>
      )}

      <div
        className={`max-w-[85%] md:max-w-[75%] px-5 py-3 text-[15px] leading-relaxed shadow-sm transform transition-all duration-300 translate-y-0 opacity-100 ${
          isMe
            ? 'bg-green-500 text-white rounded-2xl rounded-br-sm'
            : 'bg-white text-gray-800 border border-gray-100 rounded-2xl rounded-bl-sm'
        }`}
      >
        {message.text}
      </div>
    </div>
  );
}
