interface GameMode {
    name: string;
    player_count: number;
    rounds: number;
    messages_per_round: number;
    chatting_duration: number;
    voting_duration: number;
    results_duration: number;
}

interface QueueCardProps {
    gameMode: GameMode;
    isJoined: boolean;
    playerCount: number;
    onJoin: () => void;
    onLeave: () => void;
}

const QueueCard = ({ gameMode, isJoined, playerCount, onJoin, onLeave }: QueueCardProps) => {
    return (
        <div className="border border-gray-300 rounded p-4 mb-4">
            <h2 className="text-xl font-bold mb-2">{gameMode.name}</h2>
            <p>Players: {gameMode.player_count}</p>
            <p>Rounds: {gameMode.rounds}</p>
            <p>Messages per round: {gameMode.messages_per_round}</p>
            {isJoined ? (
                <div>
                    <p>Players in queue: {playerCount}</p>
                    <button className="bg-red-500 mt-2" onClick={onLeave}>Leave queue!</button>
                </div>
            ) : (
                <button className="bg-green-500 mt-2" onClick={onJoin}>Join queue!</button>
            )}
        </div>
    );
};

export default QueueCard;
