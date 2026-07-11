interface MessageCardProps {
    message: {
        text: string;
        sender: {
            user_id: string;
            username: string;
        };
    };
    isOwn: boolean;
}

const MessageCard = ({ message, isOwn }: MessageCardProps) => {
    return (
        <div className={`mb-2 ${isOwn ? 'text-right ml-auto' : 'text-left mr-auto'} w-fit border border-gray-300 rounded p-2`}>
            <p className="text-xs">{message.sender.username}</p>
            <p>{message.text}</p>
        </div>
    );
};

export default MessageCard;
