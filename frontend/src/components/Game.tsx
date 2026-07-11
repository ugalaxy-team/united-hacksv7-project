import type { Socket } from 'socket.io-client';
import { useEffect, useRef, useState } from "react";
import { onMessage } from "@/ws";
import MessageCard from "./MessageCard";
import PlayerSidebarCard from "./PlayerSidebarCard";

interface PlayerData {
    user_id: string;
    username: string;
}

interface MessageData {
    text: string;
    sender: PlayerData;
    round?: number;
}

interface VoteData {
    vote_for: PlayerData;
    vote_by: PlayerData;
}

interface GameEndData {
    victory: boolean;
    ai_player: PlayerData;
}

interface GameProps {
    socket: Socket;
    username: string;
    userId: string;
    gameData: any;
    onGameEnd: () => void;
}

const Game = ({ socket, userId, gameData, onGameEnd }: GameProps) => {
    const [phase, setPhase] = useState<string>(gameData?.phase ?? 'chatting');
    const [messages, setMessages] = useState<MessageData[]>(gameData?.messages ?? []);
    const [players, setPlayers] = useState<PlayerData[]>(gameData?.players ?? []);
    const [myMessageCount, setMyMessageCount] = useState(0);
    const [hasVoted, setHasVoted] = useState(false);
    const [currentVotes, setCurrentVotes] = useState<VoteData[]>([]);
    const [inputValue, setInputValue] = useState('');
    const [round, setRound] = useState(gameData?.round ?? 1);
    const [messagesPerRound, setMessagesPerRound] = useState(gameData?.messages_per_round ?? 0);
    const [maxRounds, setMaxRounds] = useState(gameData?.max_rounds ?? 0);
    const [gameEndData, setGameEndData] = useState<GameEndData | null>(null);
    const [chattingDuration, setChattingDuration] = useState(gameData?.chatting_duration ?? 60);
    const [votingDuration, setVotingDuration] = useState(gameData?.voting_duration ?? 30);
    const [resultsDuration, setResultsDuration] = useState(gameData?.results_duration ?? 10);
    const [timeRemaining, setTimeRemaining] = useState(0);
    const phaseStartRef = useRef(0);

    useEffect(() => {
        if (!gameData) return;
        setPhase(gameData.phase ?? 'chatting');
        setMessages(gameData.messages ?? []);
        setPlayers(gameData.players ?? []);
        setMyMessageCount(0);
        setHasVoted(false);
        setCurrentVotes([]);
        setRound(gameData.round ?? 1);
        setMessagesPerRound(gameData.messages_per_round ?? 0);
        setMaxRounds(gameData.max_rounds ?? 0);
        setChattingDuration(gameData.chatting_duration ?? 60);
        setVotingDuration(gameData.voting_duration ?? 30);
        setResultsDuration(gameData.results_duration ?? 10);
    }, [gameData]);

    useEffect(() => {
        if (!phase) return;
        let duration: number;
        if (phase === 'chatting') duration = chattingDuration;
        else if (phase === 'voting') duration = votingDuration;
        else if (phase === 'results') duration = resultsDuration;
        else return;

        setTimeRemaining(duration);
        phaseStartRef.current = Date.now();

        const interval = setInterval(() => {
            const elapsed = Math.floor((Date.now() - phaseStartRef.current) / 1000);
            const remaining = duration - elapsed;
            if (remaining <= 0) {
                setTimeRemaining(0);
                clearInterval(interval);
            } else {
                setTimeRemaining(remaining);
            }
        }, 1000);

        return () => clearInterval(interval);
    }, [phase, chattingDuration, votingDuration, resultsDuration]);

    useEffect(() => {
        const cleanupMessage = onMessage(socket);

        const onMessageSent = (data: MessageData) => {
            console.log(data)
            setMessages(prev => [...prev, data]);
        };

        const onVoting = () => {
            setPhase('voting');
        };

        const onVoteCasted = (data: VoteData) => {
            setCurrentVotes(prev => [...prev, data]);
        };

        const onResults = () => {
            setPhase('results');
        };

        const onNewRound = (data: any) => {
            setCurrentVotes([]);
            setMyMessageCount(0);
            setHasVoted(false);
            setPhase('chatting');
            setRound(data.round ?? round + 1);
            setMessagesPerRound(data.messages_per_round ?? messagesPerRound);
            setMaxRounds(data.max_rounds ?? maxRounds);
            setChattingDuration(data.chatting_duration ?? chattingDuration);
            setVotingDuration(data.voting_duration ?? votingDuration);
            setResultsDuration(data.results_duration ?? resultsDuration);
        };

        const onGameEnd = (data: GameEndData) => {
            setGameEndData(data);
        };

        socket.on('game:message_sent', onMessageSent);
        socket.on('game:voting', onVoting);
        socket.on('game:vote_casted', onVoteCasted);
        socket.on('game:results', onResults);
        socket.on('game:new_round', onNewRound);
        socket.on('game:end', onGameEnd);

        return () => {
            cleanupMessage();
            socket.off('game:message_sent', onMessageSent);
            socket.off('game:voting', onVoting);
            socket.off('game:vote_casted', onVoteCasted);
            socket.off('game:results', onResults);
            socket.off('game:new_round', onNewRound);
            socket.off('game:end', onGameEnd);
        };
    }, [socket]);

    const sendMessage = () => {
        if (!inputValue.trim()) return;
        socket.emit('game:message', { message: inputValue.trim() });
        setMyMessageCount(prev => prev + 1);
        setInputValue('');
    };

    const castVote = (targetUserId: string) => {
        socket.emit('game:vote', { user_id: targetUserId });
        setHasVoted(true);
    };

    const getVotedBy = (playerId: string): string[] => {
        return currentVotes
            .filter(v => v.vote_for.user_id === playerId)
            .map(v => v.vote_by.username);
    };

    const inputDisabled = phase !== 'chatting' || myMessageCount >= messagesPerRound;

    return (
        <section className="relative">
            <div className="flex">
                <div className="flex-1">
                    <p>Round {round}/{maxRounds} <span className="ml-4 text-sm text-gray-500">Time: {timeRemaining}s</span></p>
                    <div className="h-96 overflow-y-auto border border-gray-300 p-2">
                        {(() => {
                            let lastRound = 0;
                            const elements: React.ReactNode[] = [];
                            messages.forEach((msg, i) => {
                                const msgRound = msg.round ?? 1;
                                if (msgRound !== lastRound) {
                                    elements.push(
                                        <div key={`round-${msgRound}`} className="text-center text-gray-400 text-xs my-2 font-semibold">
                                            --- Round {msgRound} ---
                                        </div>
                                    );
                                    lastRound = msgRound;
                                }
                                elements.push(
                                    <MessageCard
                                        key={i}
                                        message={msg}
                                        isOwn={msg.sender.user_id === userId}
                                    />
                                );
                            });
                            return elements;
                        })()}
                    </div>
                    <div className="flex gap-2 mt-2">
                        <input
                            className="flex-1 border border-gray-300 p-1"
                            value={inputValue}
                            onChange={e => setInputValue(e.target.value)}
                            disabled={inputDisabled}
                            onKeyDown={e => e.key === 'Enter' && sendMessage()}
                        />
                        <button
                            className="border border-gray-300 p-1"
                            onClick={sendMessage}
                            disabled={inputDisabled}
                        >
                            Send
                        </button>
                    </div>
                </div>

                <div className="w-64 ml-4">
                    {players.map(p => (
                        <PlayerSidebarCard
                            key={p.user_id}
                            player={p}
                            phase={phase}
                            isSelf={p.user_id === userId}
                            hasVoted={hasVoted}
                            onVote={() => castVote(p.user_id)}
                            votedBy={getVotedBy(p.user_id)}
                        />
                    ))}
                </div>
            </div>

            {gameEndData && (
                <div className="absolute inset-0 bg-black/50 flex items-center justify-center">
                    <div className="bg-white p-8 rounded shadow-lg text-center">
                        <h2 className="text-2xl font-bold mb-4">
                            {gameEndData.victory ? 'You Win!' : 'You Lose!'}
                        </h2>
                        <p className="mb-2">The AI was: <strong>{gameEndData.ai_player.username}</strong></p>
                        <button
                            className="mt-4 bg-blue-500 text-white px-4 py-2 rounded"
                            onClick={onGameEnd}
                        >
                            Back to Queue
                        </button>
                    </div>
                </div>
            )}
        </section>
    );
};

export default Game;
