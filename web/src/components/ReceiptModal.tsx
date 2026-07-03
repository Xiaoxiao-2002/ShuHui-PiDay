import { useRef, useState } from "react";
import { toPng } from "html-to-image";
import { formatCompletedAt, formatElapsed } from "../format";
import type { CompletionReceiptV1 } from "../types";

interface Props {
  receipt: CompletionReceiptV1;
  onReplay: () => void;
  onBack: () => void;
}

export function ReceiptModal({ receipt, onReplay, onBack }: Props) {
  const cardRef = useRef<HTMLDivElement>(null);
  const [saving, setSaving] = useState(false);
  const saveImage = async () => {
    if (!cardRef.current) return;
    setSaving(true);
    try {
      const url = await toPng(cardRef.current, { pixelRatio: 2, backgroundColor: "#f8f6f1" });
      const link = document.createElement("a");
      link.download = `${receipt.puzzleId}-完成凭证.png`;
      link.href = url;
      link.click();
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="modal-backdrop" role="dialog" aria-modal="true" aria-label="完成凭证">
      <div className="receipt-wrap">
        <div className={`receipt-card tier-${receipt.difficulty}`} ref={cardRef}>
          <div className="receipt-brand">πDay - 特色数回</div>
          <div className="receipt-check">✓</div>
          <div className="receipt-status">挑战完成</div>
          <div className="receipt-puzzle">{receipt.puzzleId}</div>
          <div className="receipt-difficulty">{receipt.difficultyLabel}</div>
          <div className="receipt-time-label">完成用时</div>
          <div className="receipt-time">{formatElapsed(receipt.elapsedMs)}</div>
          <dl className="receipt-meta">
            <div><dt>完成时间</dt><dd>{formatCompletedAt(receipt.completedAt)}</dd></div>
            <div><dt>凭证短码</dt><dd>{receipt.shortCode}</dd></div>
          </dl>
          <div className="receipt-verified">本地验证通过</div>
        </div>
        <p className="receipt-hint">请保存图片或截屏，并向活动工作人员出示。</p>
        <div className="modal-actions">
          <button className="primary-button" type="button" onClick={saveImage} disabled={saving}>
            {saving ? "正在生成…" : "保存凭证图片"}
          </button>
          <button type="button" onClick={onReplay}>重新挑战</button>
          <button type="button" onClick={onBack}>返回选关</button>
        </div>
      </div>
    </div>
  );
}
