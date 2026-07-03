import { useEffect, useMemo, useState } from "react";
import { loadPuzzleIndex } from "./api";
import { PuzzlePlayer } from "./components/PuzzlePlayer";
import { TutorialPage } from "./components/TutorialPage";
import { UpdateBanner } from "./components/UpdateBanner";
import { formatElapsed } from "./format";
import { LocalReceiptIssuer } from "./receipt";
import { loadCompleted, storageAvailable } from "./storage";
import type { CompletedPuzzleV1, Difficulty, PuzzleIndexItem, PuzzleIndexV1 } from "./types";
import { loadTutorialProgress } from "./tutorial";

const difficultyOrder: Difficulty[] = ["beginner", "medium", "difficult", "expert"];
const labels: Record<Difficulty, string> = {
  beginner: "初级 Beginner",
  medium: "中级 Medium",
  difficult: "高级 Difficult",
  expert: "专家 Expert",
};
const issuer = new LocalReceiptIssuer();

export default function App() {
  const [index, setIndex] = useState<PuzzleIndexV1 | null>(null);
  const [error, setError] = useState("");
  const [selectedDifficulty, setSelectedDifficulty] = useState<Difficulty | "all">("all");
  const [active, setActive] = useState<PuzzleIndexItem | null>(null);
  const [tutorialActive, setTutorialActive] = useState(false);
  const [tutorialProgress, setTutorialProgress] = useState(loadTutorialProgress);
  const [completed, setCompleted] = useState<Record<string, CompletedPuzzleV1>>(() => loadCompleted());
  const [canStore] = useState(storageAvailable);
  const isEmbedded = /MicroMessenger|QQ\//i.test(navigator.userAgent);

  useEffect(() => {
    loadPuzzleIndex().then(setIndex).catch((reason: unknown) => setError(reason instanceof Error ? reason.message : "加载失败"));
  }, []);

  useEffect(() => {
    const syncFromUrl = () => {
      if (window.location.hash === "#tutorial") {
        setTutorialActive(true);
        setActive(null);
        return;
      }
      setTutorialActive(false);
      const match = window.location.hash.match(/^#play\/(TSH-\d{2})$/);
      setActive(match && index ? index.puzzles.find((item) => item.id === match[1]) ?? null : null);
    };
    syncFromUrl();
    window.addEventListener("hashchange", syncFromUrl);
    return () => window.removeEventListener("hashchange", syncFromUrl);
  }, [index]);

  const openPuzzle = (item: PuzzleIndexItem) => {
    window.location.hash = `play/${item.id}`;
    setTutorialActive(false);
    setActive(item);
  };

  const openTutorial = () => {
    window.location.hash = "tutorial";
    setActive(null);
    setTutorialActive(true);
  };

  const closePuzzle = () => {
    history.replaceState(null, "", `${window.location.pathname}${window.location.search}`);
    setActive(null);
    setTutorialActive(false);
  };

  const visible = useMemo(
    () => index?.puzzles.filter((item) => selectedDifficulty === "all" || item.difficulty === selectedDifficulty) ?? [],
    [index, selectedDifficulty],
  );

  if (active) {
    return (
      <>
        <UpdateBanner />
        <PuzzlePlayer item={active} issuer={issuer} onBack={closePuzzle} onCompletion={() => setCompleted(loadCompleted())} />
      </>
    );
  }

  if (tutorialActive) {
    return (
      <>
        <UpdateBanner />
        <TutorialPage
          onBack={closePuzzle}
          onComplete={() => setTutorialProgress(loadTutorialProgress())}
          onStartFirstPuzzle={index?.puzzles[0] ? () => openPuzzle(index.puzzles[0]) : undefined}
        />
      </>
    );
  }

  return (
    <div className="app-shell">
      <UpdateBanner />
      {(isEmbedded || !canStore) && (
        <div className="environment-warning">
          {isEmbedded ? "建议使用系统浏览器打开，以获得离线缓存和稳定的自动保存。" : "当前浏览器限制了本地存储，刷新后可能无法恢复作答。"}
        </div>
      )}
      <header className="hero">
        <div className="hero-orbit orbit-one" />
        <div className="hero-orbit orbit-two" />
        <p className="eyebrow">数学文化科普活动</p>
        <h1>πDay - 特色数回</h1>
        <p>在密铺的圆之间，寻找唯一闭环</p>
        <div className="progress-summary">
          <strong>{Object.keys(completed).length}</strong><span>/ 20 已完成</span>
        </div>
      </header>

      <main className="home-content">
        <section className="tutorial-callout">
          <div className="tutorial-callout-art" aria-hidden="true">
            <span className="orbit-arc arc-a" /><span className="orbit-arc arc-b" /><b>π</b>
          </div>
          <div className="tutorial-callout-copy">
            <p className="eyebrow">第一次玩特色数回？</p>
            <h2>{tutorialProgress.completed ? "随时重温互动教程" : "亲手操作，几分钟学会规则"}</h2>
            <p>画一条弧、故意制造分叉、点亮 π 六方向，最后完成一题小练习。</p>
            <div className="tutorial-callout-meta">
              <span>{tutorialProgress.completed ? "✓ 已完成" : `进度 ${tutorialProgress.step + 1} / 6`}</span>
              <span>不计时</span><span>可随时退出</span>
            </div>
          </div>
          <button type="button" onClick={openTutorial}>{tutorialProgress.completed ? "重新学习" : tutorialProgress.step > 0 ? "继续教程" : "开始互动教程"}<span>→</span></button>
        </section>
        <section className="rules-card">
          <div>
            <span>1</span><p>沿候选圆弧画出一条非空的单一闭环，不能交叉、分叉或形成多个小环。</p>
          </div>
          <div>
            <span>2</span><p>数字表示闭环经过该单元格边界的圆弧数量，空白单元格没有数量限制。</p>
          </div>
          <div>
            <span>π</span><p>至少与一个 π 单元格相邻的已选圆弧，必须在六种方向上各有且仅有一条。</p>
          </div>
        </section>

        <section className="level-section">
          <div className="section-heading">
            <div><p className="eyebrow dark">选择难度</p><h2>开始挑战</h2></div>
            <button className={selectedDifficulty === "all" ? "active-filter" : ""} onClick={() => setSelectedDifficulty("all")}>全部 20 题</button>
          </div>
          <div className="difficulty-grid">
            {difficultyOrder.map((difficulty) => {
              const total = index?.puzzles.filter((item) => item.difficulty === difficulty).length ?? 0;
              const done = index?.puzzles.filter((item) => item.difficulty === difficulty && completed[item.id]).length ?? 0;
              return (
                <button
                  key={difficulty}
                  className={`difficulty-card tier-${difficulty} ${selectedDifficulty === difficulty ? "selected" : ""}`}
                  onClick={() => setSelectedDifficulty(difficulty)}
                >
                  <span className="difficulty-name">{labels[difficulty]}</span>
                  <span>{done} / {total} 完成</span>
                </button>
              );
            })}
          </div>
        </section>

        <section className="puzzle-section">
          <h2>{selectedDifficulty === "all" ? "全部关卡" : labels[selectedDifficulty]}</h2>
          {error && <div className="error-panel">{error}</div>}
          {!index && !error && <div className="center-state"><div className="spinner" /><p>正在加载关卡…</p></div>}
          <div className="puzzle-grid">
            {visible.map((item) => {
              const record = completed[item.id];
              return (
                <button key={item.id} className={`puzzle-card tier-${item.difficulty}`} onClick={() => openPuzzle(item)}>
                  <span className="puzzle-code">{item.id}</span>
                  <span className="puzzle-level">{item.difficultyLabel}</span>
                  {record ? (
                    <span className="completion-badge">✓ 最佳 {formatElapsed(record.bestElapsedMs)}</span>
                  ) : (
                    <span className="not-started">开始作答 →</span>
                  )}
                </button>
              );
            })}
          </div>
        </section>
      </main>
      <footer className="site-footer">πDay - 特色数回 · 20 道唯一解挑战</footer>
    </div>
  );
}
