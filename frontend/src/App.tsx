import { FormEvent, Fragment, useEffect, useState } from "react";
import {
  createTimelineSession,
  Difficulty,
  EraInfo,
  fetchEras,
  fetchEvents,
  fetchLeaderboard,
  HistoricalEra,
  HistoricalEventItem,
  LeaderboardEntry,
  PlacementAttemptItem,
  submitEventPlacement,
  TimelineSessionState,
} from "./api";

type ActiveTab = "play" | "archive" | "leaderboard";

export function App() {
  const [activeTab, setActiveTab] = useState<ActiveTab>("play");
  const [eras, setEras] = useState<EraInfo[]>([]);
  const [archiveEra, setArchiveEra] = useState<HistoricalEra | "">("");
  const [archiveEvents, setArchiveEvents] = useState<HistoricalEventItem[]>([]);
  const [leaderboardDifficulty, setLeaderboardDifficulty] = useState<Difficulty | "">("");
  const [leaderboard, setLeaderboard] = useState<LeaderboardEntry[]>([]);

  const [playerName, setPlayerName] = useState<string>("Ada Lovelace");
  const [difficulty, setDifficulty] = useState<Difficulty>("explorer");
  const [selectedEra, setSelectedEra] = useState<HistoricalEra | "">("");

  const [session, setSession] = useState<TimelineSessionState | null>(null);
  const [lastAttempt, setLastAttempt] = useState<PlacementAttemptItem | null>(null);
  const [isBusy, setIsBusy] = useState<boolean>(false);
  const [errorBanner, setErrorBanner] = useState<string | null>(null);

  useEffect(() => {
    void (async () => {
      try {
        const [erasData, eventsData, lbData] = await Promise.all([
          fetchEras(),
          fetchEvents(""),
          fetchLeaderboard(""),
        ]);
        setEras(erasData);
        setArchiveEvents(eventsData);
        setLeaderboard(lbData);
      } catch (err) {
        setErrorBanner(err instanceof Error ? err.message : "Failed to load catalog.");
      }
    })();
  }, []);

  useEffect(() => {
    if (activeTab === "archive") {
      void fetchEvents(archiveEra)
        .then(setArchiveEvents)
        .catch((err: unknown) =>
          setErrorBanner(err instanceof Error ? err.message : "Failed to load archive."),
        );
    } else if (activeTab === "leaderboard") {
      void fetchLeaderboard(leaderboardDifficulty)
        .then(setLeaderboard)
        .catch((err: unknown) =>
          setErrorBanner(
            err instanceof Error ? err.message : "Failed to load leaderboard.",
          ),
        );
    }
  }, [activeTab, archiveEra, leaderboardDifficulty]);

  async function handleStartSession(e?: FormEvent) {
    if (e) e.preventDefault();
    const trimmed = playerName.trim() || "Explorer";
    setIsBusy(true);
    setErrorBanner(null);
    setLastAttempt(null);
    try {
      const created = await createTimelineSession({
        player_name: trimmed,
        difficulty,
        era: selectedEra || null,
      });
      setSession(created);
      setActiveTab("play");
    } catch (err) {
      setErrorBanner(err instanceof Error ? err.message : "Could not start session.");
    } finally {
      setIsBusy(false);
    }
  }

  async function handlePlaceCard(positionIndex: number) {
    if (!session || !session.current_event || isBusy) return;
    setIsBusy(true);
    setErrorBanner(null);
    try {
      const outcome = await submitEventPlacement(session.id, {
        event_id: session.current_event.id,
        position_index: positionIndex,
      });
      setSession(outcome.session);
      setLastAttempt(outcome.attempt);
      if (outcome.session.status !== "in_progress") {
        const updatedLb = await fetchLeaderboard(leaderboardDifficulty);
        setLeaderboard(updatedLb);
      }
    } catch (err) {
      setErrorBanner(err instanceof Error ? err.message : "Placement failed.");
    } finally {
      setIsBusy(false);
    }
  }

  const isPlaying = session?.status === "in_progress" && session.current_event !== null;

  return (
    <div className="chrono-shell">
      <header className="chrono-header">
        <div className="chrono-brand">
          <span className="chrono-badge">CHRONOQUEST • WORLD HISTORY CHALLENGE</span>
          <h1>Chronicles of Human Civilization</h1>
          <p className="chrono-subtitle">
            Reconstruct the chronological order of pivotal milestones across six eras of world
            history.
          </p>
        </div>

        <nav className="chrono-tabs" role="tablist" aria-label="ChronoQuest Sections">
          <button
            type="button"
            role="tab"
            aria-selected={activeTab === "play"}
            data-testid="tab-play"
            className={`chrono-tab ${activeTab === "play" ? "active" : ""}`}
            onClick={() => setActiveTab("play")}
          >
            Play Timeline Challenge
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={activeTab === "archive"}
            data-testid="tab-archive"
            className={`chrono-tab ${activeTab === "archive" ? "active" : ""}`}
            onClick={() => setActiveTab("archive")}
          >
            Historical Archive ({eras.reduce((acc, item) => acc + item.event_count, 0) || 24})
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={activeTab === "leaderboard"}
            data-testid="tab-leaderboard"
            className={`chrono-tab ${activeTab === "leaderboard" ? "active" : ""}`}
            onClick={() => setActiveTab("leaderboard")}
          >
            Hall of Records Leaderboard
          </button>
        </nav>
      </header>

      {errorBanner && (
        <div className="chrono-alert error" role="alert" data-testid="error-banner">
          <strong>Notice:</strong> {errorBanner}
        </div>
      )}

      {activeTab === "play" && (
        <main className="chrono-main" data-testid="play-view">
          <form className="setup-bar" onSubmit={(e) => void handleStartSession(e)}>
            <div className="field-group">
              <label htmlFor="player-name-input">Historian Name</label>
              <input
                id="player-name-input"
                data-testid="player-name-input"
                type="text"
                maxLength={64}
                value={playerName}
                onChange={(e) => setPlayerName(e.target.value)}
                placeholder="Enter your name..."
                required
              />
            </div>

            <div className="field-group">
              <label htmlFor="difficulty-select">Challenge Tier</label>
              <select
                id="difficulty-select"
                data-testid="difficulty-select"
                value={difficulty}
                onChange={(e) => setDifficulty(e.target.value as Difficulty)}
              >
                <option value="explorer">Explorer (5 Cards • 3 Lives • 100 pts)</option>
                <option value="historian">Historian (8 Cards • 3 Lives • 150 pts)</option>
                <option value="chronomaster">Chronomaster (12 Cards • 2 Lives • 200 pts)</option>
              </select>
            </div>

            <div className="field-group">
              <label htmlFor="era-filter-select">Era Focus</label>
              <select
                id="era-filter-select"
                data-testid="era-filter-select"
                value={selectedEra}
                onChange={(e) => setSelectedEra(e.target.value as HistoricalEra | "")}
              >
                <option value="">All Six Historical Eras (3500 BCE – Present)</option>
                {eras.map((item) => (
                  <option key={item.era} value={item.era}>
                    {item.label} ({item.period_label})
                  </option>
                ))}
              </select>
            </div>

            <button
              type="submit"
              className="btn-primary"
              data-testid="start-session-btn"
              disabled={isBusy}
            >
              {session ? "Start New Expedition" : "Start Expedition"}
            </button>
          </form>

          {!session ? (
            <section className="empty-arena" data-testid="welcome-panel">
              <h2>Ready to Test Your Chronological Mastery?</h2>
              <p>
                Each expedition begins with one face-up <strong>Anchor Card</strong> on the
                timeline. Draw mystery historical events with their dates redacted, deduce whether
                they occurred before, between, or after the placed milestones, and build streaks to
                ascend the Hall of Records.
              </p>
              <button
                type="button"
                className="btn-primary"
                onClick={() => void handleStartSession()}
              >
                Launch Timeline Expedition
              </button>
            </section>
          ) : (
            <div className="game-arena" data-testid="game-arena">
              <section className="hud-strip" aria-label="Session Status HUD">
                <div className="hud-stat">
                  <span className="hud-label">Historian</span>
                  <strong data-testid="hud-player">{session.player_name}</strong>
                </div>
                <div className="hud-stat">
                  <span className="hud-label">Score</span>
                  <strong data-testid="hud-score">{session.score}</strong>
                </div>
                <div className="hud-stat">
                  <span className="hud-label">Streak</span>
                  <strong data-testid="hud-streak">
                    {session.streak} <small>(Best {session.max_streak})</small>
                  </strong>
                </div>
                <div className="hud-stat">
                  <span className="hud-label">Lives Remaining</span>
                  <strong data-testid="hud-lives">
                    {session.lives_remaining} / {session.initial_lives}
                  </strong>
                </div>
                <div className="hud-stat">
                  <span className="hud-label">Cards Remaining</span>
                  <strong data-testid="hud-cards-remaining">{session.cards_remaining}</strong>
                </div>
                <div className="hud-stat">
                  <span className="hud-label">Status</span>
                  <span
                    className={`status-pill status-${session.status}`}
                    data-testid="hud-status"
                  >
                    {session.status}
                  </span>
                </div>
              </section>

              {lastAttempt && (
                <section
                  className={`feedback-banner ${lastAttempt.is_correct ? "correct" : "misplaced"}`}
                  role="status"
                  aria-live="polite"
                  data-testid="placement-feedback"
                >
                  <div className="feedback-header">
                    <strong>
                      {lastAttempt.is_correct
                        ? `Correct Placement! (+${lastAttempt.points_awarded} pts)`
                        : "Chronological Misplacement (-1 Life)"}
                    </strong>
                    <span className="revealed-year" data-testid="feedback-revealed-year">
                      {lastAttempt.placed_event.title} — {lastAttempt.placed_event.year_label}
                    </span>
                  </div>
                  <p className="feedback-significance">
                    <strong>Historical Significance:</strong>{" "}
                    {lastAttempt.placed_event.significance}
                  </p>
                </section>
              )}

              {session.status !== "in_progress" && (
                <section
                  className={`session-complete-panel status-${session.status}`}
                  data-testid="session-summary-banner"
                >
                  <h2>
                    {session.status === "completed"
                      ? "Expedition Completed! Timeline Reconstructed"
                      : "Expedition Ended — Out of Lives"}
                  </h2>
                  <p>
                    Final Score: <strong>{session.score} pts</strong> • Best Streak:{" "}
                    <strong>{session.max_streak}</strong> • Timeline Milestones:{" "}
                    <strong>{session.timeline.length}</strong>
                  </p>
                  <div className="complete-actions">
                    <button
                      type="button"
                      className="btn-primary"
                      onClick={() => void handleStartSession()}
                    >
                      Play Another Expedition
                    </button>
                    <button
                      type="button"
                      className="btn-secondary"
                      onClick={() => setActiveTab("leaderboard")}
                    >
                      View Hall of Records
                    </button>
                  </div>
                </section>
              )}

              {session.current_event && (
                <section className="drawn-card-panel" data-testid="drawn-event-card">
                  <div className="drawn-card-header">
                    <span className="era-pill">{session.current_event.era_label}</span>
                    <span className="region-pill">{session.current_event.region}</span>
                    <span className="mystery-year-badge" data-testid="drawn-card-year-hidden">
                      Year: ????
                    </span>
                  </div>
                  <h2 className="drawn-card-title" data-testid="drawn-card-title">
                    {session.current_event.title}
                  </h2>
                  <p className="drawn-card-summary" data-testid="drawn-card-summary">
                    {session.current_event.summary}
                  </p>
                  <p className="drawn-card-prompt">
                    Select a chronological insertion slot on the timeline below to place this
                    milestone:
                  </p>
                </section>
              )}

              <section className="timeline-section" aria-label="Chronological Timeline Board">
                <div className="timeline-header">
                  <h3>Chronological Timeline Board ({session.timeline.length} Placed)</h3>
                  <span>Ordered Earliest (BCE) → Latest (CE)</span>
                </div>

                <div className="timeline-track" data-testid="timeline-track">
                  {isPlaying && (
                    <button
                      type="button"
                      className="slot-btn"
                      data-testid="placement-slot-0"
                      disabled={isBusy}
                      onClick={() => void handlePlaceCard(0)}
                    >
                      + Place Here (Slot #0 — Earliest)
                    </button>
                  )}

                  {session.timeline.map((card, index) => (
                    <Fragment key={card.id}>
                      <article
                        className="timeline-card"
                        data-testid={`timeline-card-${index}`}
                      >
                        <div className="timeline-card-top">
                          <span className="year-badge" data-testid={`timeline-card-year-${index}`}>
                            {card.year_label}
                          </span>
                          <span className="era-pill">{card.era_label}</span>
                          <span className="region-pill">{card.region}</span>
                        </div>
                        <h4>{card.title}</h4>
                        <p className="card-summary">{card.summary}</p>
                        <p className="card-significance">
                          <strong>Significance:</strong> {card.significance}
                        </p>
                      </article>

                      {isPlaying && (
                        <button
                          type="button"
                          className="slot-btn"
                          data-testid={`placement-slot-${index + 1}`}
                          disabled={isBusy}
                          onClick={() => void handlePlaceCard(index + 1)}
                        >
                          + Place Here (Slot #{index + 1} — After {card.year_label})
                        </button>
                      )}
                    </Fragment>
                  ))}
                </div>
              </section>
            </div>
          )}
        </main>
      )}

      {activeTab === "archive" && (
        <main className="chrono-main" data-testid="archive-view">
          <section className="archive-controls">
            <div className="era-filter-pills" role="group" aria-label="Filter by Historical Era">
              <button
                type="button"
                data-testid="archive-era-all"
                className={`filter-pill ${archiveEra === "" ? "active" : ""}`}
                onClick={() => setArchiveEra("")}
              >
                All Eras (24)
              </button>
              {eras.map((item) => (
                <button
                  key={item.era}
                  type="button"
                  data-testid={`archive-era-${item.era}`}
                  className={`filter-pill ${archiveEra === item.era ? "active" : ""}`}
                  onClick={() => setArchiveEra(item.era)}
                >
                  {item.label} ({item.event_count})
                </button>
              ))}
            </div>
          </section>

          <section className="era-overview-grid">
            {eras
              .filter((e) => !archiveEra || e.era === archiveEra)
              .map((eraItem) => (
                <article
                  key={eraItem.era}
                  className="era-summary-card"
                  data-testid={`era-card-${eraItem.era}`}
                >
                  <div className="era-card-header">
                    <h3>{eraItem.label}</h3>
                    <span className="period-badge">{eraItem.period_label}</span>
                  </div>
                  <p>{eraItem.description}</p>
                </article>
              ))}
          </section>

          <section className="archive-events-grid" data-testid="archive-events-list">
            {archiveEvents.map((ev) => (
              <article key={ev.id} className="archive-event-card" data-testid={`archive-event-${ev.id}`}>
                <div className="timeline-card-top">
                  <span className="year-badge">{ev.year_label}</span>
                  <span className="era-pill">{ev.era_label}</span>
                  <span className="region-pill">{ev.region}</span>
                </div>
                <h4>{ev.title}</h4>
                <p className="card-summary">{ev.summary}</p>
                <p className="card-significance">
                  <strong>Significance:</strong> {ev.significance}
                </p>
              </article>
            ))}
          </section>
        </main>
      )}

      {activeTab === "leaderboard" && (
        <main className="chrono-main" data-testid="leaderboard-view">
          <div className="leaderboard-header">
            <div>
              <h2>Hall of Records Leaderboard</h2>
              <p>Top completed and finished historical timeline expeditions ranked by score.</p>
            </div>
            <div className="field-group">
              <label htmlFor="lb-difficulty-filter">Filter Difficulty</label>
              <select
                id="lb-difficulty-filter"
                data-testid="leaderboard-difficulty-select"
                value={leaderboardDifficulty}
                onChange={(e) => setLeaderboardDifficulty(e.target.value as Difficulty | "")}
              >
                <option value="">All Difficulties</option>
                <option value="explorer">Explorer</option>
                <option value="historian">Historian</option>
                <option value="chronomaster">Chronomaster</option>
              </select>
            </div>
          </div>

          {leaderboard.length === 0 ? (
            <section className="empty-arena" data-testid="leaderboard-empty">
              <h3>No Expeditions Recorded Yet</h3>
              <p>Complete a Timeline Challenge expedition to claim the #1 rank in the archives.</p>
              <button
                type="button"
                className="btn-primary"
                onClick={() => setActiveTab("play")}
              >
                Start Your First Expedition
              </button>
            </section>
          ) : (
            <table className="leaderboard-table" data-testid="leaderboard-table">
              <thead>
                <tr>
                  <th>Rank</th>
                  <th>Historian</th>
                  <th>Difficulty</th>
                  <th>Score</th>
                  <th>Best Streak</th>
                  <th>Cards Placed</th>
                  <th>Outcome</th>
                </tr>
              </thead>
              <tbody>
                {leaderboard.map((entry) => (
                  <tr key={entry.session_id} data-testid={`leaderboard-row-${entry.rank}`}>
                    <td>#{entry.rank}</td>
                    <td>
                      <strong>{entry.player_name}</strong>
                    </td>
                    <td>{entry.difficulty}</td>
                    <td>
                      <strong>{entry.score} pts</strong>
                    </td>
                    <td>{entry.max_streak}</td>
                    <td>{entry.cards_placed}</td>
                    <td>
                      <span className={`status-pill status-${entry.status}`}>{entry.status}</span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </main>
      )}
    </div>
  );
}
