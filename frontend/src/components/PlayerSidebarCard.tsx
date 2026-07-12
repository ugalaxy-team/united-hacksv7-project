import Avatar from "boring-avatars";

interface PlayerSidebarCardProps {
    player: {
        user_id: string;
        username: string;
    };
    phase: string;
    isSelf: boolean;
    hasVoted: boolean;
    onVote: () => void;
    votedBy: string[];
}

const PlayerSidebarCard = ({ player, phase, isSelf, hasVoted, onVote, votedBy }: PlayerSidebarCardProps) => {
    return (
        <div className="border border-gray-300 rounded p-2 mb-2">
            <Avatar name={player.user_id} variant="beam" size={50} />
            <p>{player.username}</p>
            {phase === 'voting' && !isSelf && !hasVoted && (
                <button className="border border-gray-300 px-2 mt-1" onClick={onVote}>Vote</button>
            )}
            {phase === 'results' && votedBy.map((name, i) => (
                <p key={i} className="text-xs">{name} voted for this player</p>
            ))}
        </div>
    );
};

export default PlayerSidebarCard;
