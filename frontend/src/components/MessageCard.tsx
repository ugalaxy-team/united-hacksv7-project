import Avatar from "boring-avatars";

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
        <div className={`flex flex-col ${isOwn ? 'items-end justify-items-end' : 'items-start justify-items-start'}`}>
            <div>
                <Avatar name={message.sender.user_id} variant="beam" size={30} />
                <p className="text-xs">{message.sender.username}</p>
            </div>
            <div className={`mb-2 w-fit border border-gray-300 rounded p-2`}>
                <p>{message.text}</p>
            </div>
        </div>
    );
};

export default MessageCard;
