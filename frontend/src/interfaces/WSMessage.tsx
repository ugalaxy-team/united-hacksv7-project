export interface Player {
  user_id: string;
  username: string;
  current_game?: string | null;
  current_queue?: string | null;
  is_ai?: boolean;
}

export interface Message {
  text: string;
  created_at: string;
  room_id: string;
  round: number;
  sender: Player;
}

export interface Vote {
  vote_for: Player;
  vote_by: Player;
}

export interface GameState {
  room_id: string;
  round: number;
  max_rounds: number;
  messages_per_round: number;
  phase: 'chatting' | 'voting' | 'results';
  players: Player[];
  messages: Message[];
  current_votes: Vote[];
  all_votes: Vote[];
  game_mode: string;
  chatting_duration: number;
  voting_duration: number;
  results_duration: number;
  victory?: boolean;
  ai_player?: Player;
}

export interface QueueJoinResponse {
  ok?: boolean;
  player_amount?: number;
}

export interface QueueUpdateResponse {
  id: string;
  player_amount: number;
}

export interface ServerMessage {
  message: string;
  type: 'error' | 'info' | 'success';
}
