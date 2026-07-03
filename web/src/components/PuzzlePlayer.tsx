import { useEffect, useMemo, useState } from "react";
import { loadPuzzle } from "../api";
import { formatElapsed } from "../format";
import type { AttemptStateV1, CompletionReceiptV1, PlayablePuzzleV1, PuzzleIndexItem } from "../types";
import type { ReceiptIssuer } from "../receipt";
import { clearAttempt, loadAttempt, saveAttempt, saveCompletion } from "../storage";
import { validateSolutionEdges } from "../validator";
import { PuzzleBoard } from "./PuzzleBoard";
import { ReceiptModal } from "./ReceiptModal";

interface Props {
  item: PuzzleIndexItem;
  issuer: ReceiptIssuer;
  onBack: () => void;
  onCompletion: () => void;
}

const newId = () => globalThis.crypto?.randomUUID?.() ?? `${Date.now()}-${Math.random()}`;

export function PuzzlePlayer({ item, issuer, onBack, onCompletion }: Props) {
  const [puzzle, setPuzzle] = useState<PlayablePuzzleV1 | null>(null);
  const [attempt, setAttempt] = useState<AttemptStateV1 | null>(null);
  const [receipt, setReceipt] = useState<CompletionReceiptV1 | null>(null);
  const [now, setNow] = useState(Date.now());
  const [message, setMessage] = useState<string>("");
  const [loadingError, setLoadingError] = useState<string>("");

  useEffect(() => {
    let active = true;
    loadPuzzle(item.file)
      .then((loaded) => {
        if (!active) return;
        setPuzzle(loaded);
        setAttempt(loadAttempt(loaded));
      })
      .catch((error: unknown) => setLoadingError(error instanceof Error ? error.message : "题目加载失败"));
    return () => {
      active = false;
    };
  }, [item.file]);

  useEffect(() => {
    if (!attempt || receipt) return;
    const timer = window.setInterval(() => setNow(Date.now()), 250);
    return () => window.clearInterval(timer);
  }, [attempt, receipt]);

  const selected = useMemo(() => new Set(attempt?.selectedEdgeIds ?? []), [attempt]);
  const elapsed = attempt ? Math.max(0, now - attempt.startedAt) : 0;

  const persist = (next: AttemptStateV1) => {
    setAttempt(next);
    saveAttempt(next);
  };

  const start = () => {
    if (!puzzle) return;
    const startedAt = Date.now();
    const next: AttemptStateV1 = {
      schemaVersion: 1,
      dataVersion: puzzle.dataVersion,
      puzzleId: puzzle.id,
      sourceHash: puzzle.sourceHash,
      attemptId: newId(),
      selectedEdgeIds: [],
      history: [],
      startedAt,
      updatedAt: startedAt,
    };
    setNow(startedAt);
    setMessage("");
    persist(next);
  };

  const toggle = (edgeId: string) => {
    if (!attempt) return;
    const edges = new Set(attempt.selectedEdgeIds);
    edges.has(edgeId) ? edges.delete(edgeId) : edges.add(edgeId);
    persist({ ...attempt, selectedEdgeIds: [...edges].sort(), history: [...attempt.history, edgeId] });
    setMessage("");
  };

  const undo = () => {
    if (!attempt?.history.length) return;
    const history = attempt.history.slice(0, -1);
    const edgeId = attempt.history.at(-1)!;
    const edges = new Set(attempt.selectedEdgeIds);
    edges.has(edgeId) ? edges.delete(edgeId) : edges.add(edgeId);
    persist({ ...attempt, selectedEdgeIds: [...edges].sort(), history });
  };

  const clear = () => {
    if (!attempt?.selectedEdgeIds.length || !window.confirm("确定清空当前画线吗？计时不会停止。")) return;
    persist({ ...attempt, selectedEdgeIds: [], history: [] });
    setMessage("");
  };

  const restart = () => {
    if (!window.confirm("确定重新开始吗？当前画线和计时都会清零。")) return;
    if (puzzle) clearAttempt(puzzle.id);
    setReceipt(null);
    start();
  };

  const submit = async () => {
    if (!puzzle || !attempt) return;
    const result = validateSolutionEdges(puzzle, attempt.selectedEdgeIds);
    setMessage(result.message);
    if (!result.valid) return;
    const completedAt = Date.now();
    const issued = await issuer.issue({
      puzzle,
      attempt,
      selectedEdgeIds: attempt.selectedEdgeIds,
      completedAt,
      elapsedMs: completedAt - attempt.startedAt,
    });
    clearAttempt(puzzle.id);
    saveCompletion(issued, puzzle.dataVersion);
    onCompletion();
    setReceipt(issued);
  };

  if (loadingError) return <main className="center-state"><p>{loadingError}</p><button onClick={onBack}>返回选关</button></main>;
  if (!puzzle) return <main className="center-state"><div className="spinner" /><p>正在加载 {item.id}…</p></main>;

  return (
    <main className={`player-page tier-${puzzle.difficulty}`}>
      <div className="player-topbar">
        <button type="button" className="back-button" onClick={onBack}>← 选关</button>
        <div>
          <h1>{puzzle.id}</h1>
          <span className="difficulty-pill">{puzzle.difficultyLabel}</span>
        </div>
        <div className="timer" aria-label="当前用时">{attempt ? formatElapsed(elapsed) : "--:--"}</div>
      </div>

      {!attempt ? (
        <section className="start-panel">
          <div className="start-symbol">π</div>
          <h2>准备开始</h2>
          <p>沿圆弧画出一条满足全部数字与 π 提示的单一闭环。</p>
          <p>计时从点击“开始挑战”后启动，刷新页面仍会继续。</p>
          <button className="primary-button large-button" type="button" onClick={start}>开始挑战</button>
        </section>
      ) : (
        <>
          <PuzzleBoard puzzle={puzzle} selected={selected} disabled={Boolean(receipt)} onToggle={toggle} />
          <div className="player-tools">
            <button type="button" onClick={undo} disabled={!attempt.history.length}>撤销</button>
            <button type="button" onClick={clear} disabled={!attempt.selectedEdgeIds.length}>清空画线</button>
            <button type="button" onClick={restart}>重新开始</button>
            <button className="primary-button submit-button" type="button" onClick={submit}>提交验证</button>
          </div>
          {message && <div className={`validation-message ${message.startsWith("恭喜") ? "success" : "error"}`}>{message}</div>}
        </>
      )}

      {receipt && (
        <ReceiptModal
          receipt={receipt}
          onReplay={() => {
            setReceipt(null);
            start();
          }}
          onBack={onBack}
        />
      )}
    </main>
  );
}
