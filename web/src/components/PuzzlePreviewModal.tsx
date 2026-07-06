import { useEffect, useState } from "react";
import { loadPuzzle } from "../api";
import { formatElapsed } from "../format";
import { loadAttempt } from "../storage";
import type { CompletedPuzzleV1, PlayablePuzzleV1, PuzzleIndexItem } from "../types";
import { PuzzleBoard } from "./PuzzleBoard";

interface Props {
  item: PuzzleIndexItem;
  record?: CompletedPuzzleV1;
  onClose: () => void;
  onConfirm: () => void;
}

const formatDate = (value: string) => new Intl.DateTimeFormat("zh-CN", {
  year: "numeric", month: "long", day: "numeric",
}).format(new Date(`${value}T00:00:00`));

export function PuzzlePreviewModal({ item, record, onClose, onConfirm }: Props) {
  const [puzzle, setPuzzle] = useState<PlayablePuzzleV1 | null>(null);
  const [hasAttempt, setHasAttempt] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    let mounted = true;
    loadPuzzle(item.file).then((loaded) => {
      if (!mounted) return;
      setPuzzle(loaded);
      setHasAttempt(Boolean(loadAttempt(loaded)));
    }).catch(() => setError("预览加载失败，请稍后重试。"));
    return () => { mounted = false; };
  }, [item.file]);

  return (
    <div className="modal-backdrop preview-backdrop" role="dialog" aria-modal="true" aria-label={`${item.id} 关卡预览`} onMouseDown={(event) => event.target === event.currentTarget && onClose()}>
      <section className={`puzzle-preview tier-${item.difficulty}`}>
        <button type="button" className="preview-close" aria-label="关闭预览" onClick={onClose}>×</button>
        <div className="preview-copy">
          <p className="eyebrow dark">关卡预览 · 修订版 v{item.revision}</p>
          <h2>{item.id}</h2>
          <span className="preview-difficulty">{item.difficultyLabel}</span>
          <dl className="preview-details">
            <div><dt>首次发布</dt><dd>{formatDate(item.publishedAt)}</dd></div>
            <div><dt>最近更新</dt><dd>{formatDate(item.updatedAt)}</dd></div>
            <div><dt>题面规模</dt><dd>{item.cellCount} 个区域</dd></div>
            <div><dt>提示数量</dt><dd>{item.clueCount} 个</dd></div>
            <div><dt>最佳记录</dt><dd>{record ? formatElapsed(record.bestElapsedMs) : "尚未通关"}</dd></div>
          </dl>
          {hasAttempt && <p className="preview-resume">检测到未完成的作答，进入后将继续原有计时。</p>}
          <div className="preview-actions">
            <button type="button" onClick={onClose}>再看看</button>
            <button type="button" className="primary-button" onClick={onConfirm}>{hasAttempt ? "继续作答" : "进入关卡"} →</button>
          </div>
        </div>
        <div className="preview-board" aria-label="题面缩略预览">
          {error ? <p>{error}</p> : puzzle ? <PuzzleBoard puzzle={puzzle} selected={new Set()} disabled onToggle={() => undefined} /> : <div className="spinner" />}
        </div>
      </section>
    </div>
  );
}
