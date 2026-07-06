import { useEffect, useMemo, useState } from "react";
import { loadPuzzleIndex } from "./api";
import { PuzzlePlayer } from "./components/PuzzlePlayer";
import { PuzzlePreviewModal } from "./components/PuzzlePreviewModal";
import { TutorialHub, TutorialPage } from "./components/TutorialPage";
import { UpdateBanner } from "./components/UpdateBanner";
import { formatElapsed } from "./format";
import { LocalReceiptIssuer } from "./receipt";
import { loadCompleted, storageAvailable } from "./storage";
import type { CompletedPuzzleV1, Difficulty, PuzzleIndexItem, PuzzleIndexV1 } from "./types";
import { loadTutorialProgress, type TutorialTrack } from "./tutorial";

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
  const [preview, setPreview] = useState<PuzzleIndexItem | null>(null);
  const [tutorialRoute, setTutorialRoute] = useState<"hub" | TutorialTrack | null>(null);
  const [tutorialProgress, setTutorialProgress] = useState(() => ({ basic: loadTutorialProgress("basic"), pi: loadTutorialProgress("pi"), guided: loadTutorialProgress("guided") }));
  const [completed, setCompleted] = useState<Record<string, CompletedPuzzleV1>>(() => loadCompleted());
  const [canStore] = useState(storageAvailable);
  const isEmbedded = /MicroMessenger|QQ\//i.test(navigator.userAgent);

  useEffect(() => {
    loadPuzzleIndex().then(setIndex).catch((reason: unknown) => setError(reason instanceof Error ? reason.message : "加载失败"));
  }, []);

  useEffect(() => {
    const syncFromUrl = () => {
      const tutorialMatch = window.location.hash.match(/^#tutorial(?:\/(basic|pi|guided))?$/);
      if (tutorialMatch) {
        setTutorialRoute((tutorialMatch[1] as TutorialTrack | undefined) ?? "hub");
        setActive(null);
        return;
      }
      setTutorialRoute(null);
      const match = window.location.hash.match(/^#play\/(TSH-(?:\d{4}-)?\d{2})$/);
      setActive(match && index ? index.puzzles.find((item) => item.id === match[1]) ?? null : null);
    };
    syncFromUrl();
    window.addEventListener("hashchange", syncFromUrl);
    return () => window.removeEventListener("hashchange", syncFromUrl);
  }, [index]);

  const openPuzzle = (item: PuzzleIndexItem) => {
    window.location.hash = `play/${item.id}`;
    setTutorialRoute(null);
    setActive(item);
  };

  const openTutorial = (track?: TutorialTrack) => {
    window.location.hash = track ? `tutorial/${track}` : "tutorial";
    setActive(null);
    setTutorialRoute(track ?? "hub");
  };

  const closePuzzle = () => {
    history.replaceState(null, "", `${window.location.pathname}${window.location.search}`);
    setActive(null);
    setTutorialRoute(null);
  };

  const visible = useMemo(
    () => (index?.puzzles.filter((item) => selectedDifficulty === "all" || item.difficulty === selectedDifficulty) ?? [])
      .sort((left, right) => right.updatedAt.localeCompare(left.updatedAt) || left.id.localeCompare(right.id)),
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

  if (tutorialRoute) {
    return (
      <>
        <UpdateBanner />
        {tutorialRoute === "hub" ? (
          <TutorialHub basic={tutorialProgress.basic} pi={tutorialProgress.pi} guided={tutorialProgress.guided} onStart={openTutorial} onBack={closePuzzle} />
        ) : (
          <TutorialPage
            track={tutorialRoute}
            onBack={() => openTutorial()}
            onExit={closePuzzle}
            onComplete={() => setTutorialProgress({ basic: loadTutorialProgress("basic"), pi: loadTutorialProgress("pi"), guided: loadTutorialProgress("guided") })}
            onStartFirstPuzzle={index?.puzzles[0] ? () => openPuzzle(index.puzzles[0]) : undefined}
          />
        )}
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
          <strong>{Object.keys(completed).length}</strong><span>/ {index?.puzzles.length ?? 0} 已完成</span>
        </div>
      </header>

      <main className="home-content">
        <section className="tutorial-callout">
          <div className="tutorial-callout-art" aria-hidden="true">
            <b>π</b><small>互动教程</small>
          </div>
          <div className="tutorial-callout-copy">
            <p className="eyebrow">第一次玩特色数回？</p>
            <h2>{tutorialProgress.basic.completed && tutorialProgress.pi.completed && tutorialProgress.guided.completed ? "随时重温三个互动教程" : "从规则入门，到亲手完成 π 小题"}</h2>
            <p>基础规则、π 专题、综合运用分开学习，最后用一题把逻辑串起来。</p>
            <div className="tutorial-callout-meta">
              <span>数回基础 {tutorialProgress.basic.completed ? "✓" : `${tutorialProgress.basic.step + 1}/5`}</span>
              <span>π 专题 {tutorialProgress.pi.completed ? "✓" : `${tutorialProgress.pi.step + 1}/3`}</span>
              <span>综合题 {tutorialProgress.guided.completed ? "✓" : `${tutorialProgress.guided.step + 1}/3`}</span>
              <span>不计时</span><span>可随时退出</span>
            </div>
          </div>
          <button type="button" onClick={() => openTutorial()}>打开教程中心<span>→</span></button>
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
            <button className={selectedDifficulty === "all" ? "active-filter" : ""} onClick={() => setSelectedDifficulty("all")}>全部 {index?.puzzles.length ?? 0} 题</button>
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
          <div className="puzzle-list-heading"><h2>{selectedDifficulty === "all" ? "全部关卡" : labels[selectedDifficulty]}</h2><span>按最近更新时间排序</span></div>
          {error && <div className="error-panel">{error}</div>}
          {!index && !error && <div className="center-state"><div className="spinner" /><p>正在加载关卡…</p></div>}
          <div className="puzzle-grid">
            {visible.map((item) => {
              const record = completed[item.id];
              return (
                <button key={item.id} className={`puzzle-card tier-${item.difficulty}`} onClick={() => setPreview(item)}>
                  <span className="puzzle-card-main"><span className="puzzle-code">{item.id}</span><small>更新于 {item.updatedAt} · v{item.revision}</small></span>
                  <span className="puzzle-card-state">{record ? <small>✓ 最佳 {formatElapsed(record.bestElapsedMs)}</small> : <small>查看题面</small>}<strong>{item.difficultyLabel}</strong></span>
                </button>
              );
            })}
          </div>
        </section>
      </main>
      {preview && <PuzzlePreviewModal item={preview} record={completed[preview.id]} onClose={() => setPreview(null)} onConfirm={() => { setPreview(null); openPuzzle(preview); }} />}
      <footer className="site-footer">πDay - 特色数回 · 持续更新的唯一解挑战</footer>
    </div>
  );
}
