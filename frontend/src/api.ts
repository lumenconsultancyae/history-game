export type HistoricalEra =
  | "ancient"
  | "classical"
  | "medieval"
  | "early_modern"
  | "industrial"
  | "modern";

export type Difficulty = "explorer" | "historian" | "chronomaster";

export type SessionStatus = "in_progress" | "completed" | "game_over";

export interface EraInfo {
  era: HistoricalEra;
  label: string;
  start_year: number;
  end_year: number;
  period_label: string;
  description: string;
  event_count: number;
}

export interface HistoricalEventItem {
  id: string;
  title: string;
  year: number;
  year_label: string;
  era: HistoricalEra;
  era_label: string;
  region: string;
  summary: string;
  significance: string;
}

export interface RedactedEventItem {
  id: string;
  title: string;
  era: HistoricalEra;
  era_label: string;
  region: string;
  summary: string;
}

export interface PlacementAttemptItem {
  id: string;
  event_id: string;
  placed_event: HistoricalEventItem;
  submitted_position: number;
  correct_position: number;
  is_correct: boolean;
  points_awarded: number;
  streak_after: number;
  lives_after: number;
  recorded_at: string;
}

export interface TimelineSessionState {
  id: string;
  player_name: string;
  difficulty: Difficulty;
  era_filter: HistoricalEra | null;
  status: SessionStatus;
  score: number;
  streak: number;
  max_streak: number;
  lives_remaining: number;
  initial_lives: number;
  cards_remaining: number;
  timeline: HistoricalEventItem[];
  current_event: RedactedEventItem | null;
  attempts: PlacementAttemptItem[];
  created_at: string;
  completed_at: string | null;
}

export interface PlacementOutcome {
  attempt: PlacementAttemptItem;
  session: TimelineSessionState;
}

export interface LeaderboardEntry {
  rank: number;
  id: string;
  session_id: string;
  player_name: string;
  difficulty: Difficulty;
  era_filter: HistoricalEra | null;
  status: SessionStatus;
  score: number;
  max_streak: number;
  cards_placed: number;
  completed_at: string | null;
}

async function requestJson<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(url, {
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
    ...init,
  });
  if (!response.ok) {
    let detail = `Request failed with status ${response.status}`;
    try {
      const problem = (await response.json()) as { detail?: string; title?: string };
      detail = problem.detail ?? problem.title ?? detail;
    } catch {
      // ignore JSON parse error on non-JSON error responses
    }
    throw new Error(detail);
  }
  return (await response.json()) as T;
}

export function fetchEras(): Promise<EraInfo[]> {
  return requestJson<EraInfo[]>("/api/v1/eras");
}

export function fetchEvents(era?: HistoricalEra | ""): Promise<HistoricalEventItem[]> {
  const query = era ? `?era=${encodeURIComponent(era)}` : "";
  return requestJson<HistoricalEventItem[]>(`/api/v1/events${query}`);
}

export function createTimelineSession(payload: {
  player_name: string;
  difficulty: Difficulty;
  era: HistoricalEra | null;
}): Promise<TimelineSessionState> {
  return requestJson<TimelineSessionState>("/api/v1/sessions", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function submitEventPlacement(
  sessionId: string,
  payload: { event_id: string; position_index: number },
): Promise<PlacementOutcome> {
  return requestJson<PlacementOutcome>(
    `/api/v1/sessions/${encodeURIComponent(sessionId)}/placements`,
    {
      method: "POST",
      body: JSON.stringify(payload),
    },
  );
}

export function fetchLeaderboard(
  difficulty?: Difficulty | "",
): Promise<LeaderboardEntry[]> {
  const query = difficulty ? `?difficulty=${encodeURIComponent(difficulty)}` : "";
  return requestJson<LeaderboardEntry[]>(`/api/v1/leaderboard${query}`);
}
