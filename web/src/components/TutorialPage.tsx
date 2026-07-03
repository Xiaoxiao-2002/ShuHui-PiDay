import { useMemo, useState } from "react";
import { PuzzleBoard } from "./PuzzleBoard";
import { validateSolutionEdges } from "../validator";
import { loadTutorialProgress, saveTutorialProgress, tutorialPuzzle } from "../tutorial";

interface Props {
  onBack: () => void;
  onComplete: () => void;
  onStartFirstPuzzle?: () => void;
}

const lessons = [
  { title: "点一下，画出圆弧", kicker: "基本操作" },
  { title: "数字告诉你经过几条弧", kicker: "数字提示" },
  { title: "端点与分叉都不允许", kicker: "顶点规则" },
  { title: "所有曲线必须连成一个环", kicker: "单一闭环" },
  { title: "让 π 的六种方向各出现一次", kicker: "π 提示" },
  { title: "亲手完成一个小闭环", kicker: "综合练习" },
];

const directionLabels = ["→", "↘", "↙", "←", "↖", "↗"];

function polar(cx: number, cy: number, radius: number, degrees: number) {
  const radians = (degrees * Math.PI) / 180;
  return { x: cx + radius * Math.cos(radians), y: cy + radius * Math.sin(radians) };
}

function arcPath(index: number, radius = 62): string {
  const start = polar(150, 100, radius, index * 60 - 28);
  const end = polar(150, 100, radius, index * 60 + 28);
  return `M ${start.x} ${start.y} A ${radius} ${radius} 0 0 1 ${end.x} ${end.y}`;
}

function ArcButton({ index, selected, onToggle, label, className = "" }: { index: number; selected: boolean; onToggle: () => void; label: string; className?: string }) {
  const path = arcPath(index);
  return (
    <g
      className={`tutorial-arc ${selected ? "selected" : ""} ${className}`}
      role="button"
      tabIndex={0}
      aria-label={label}
      aria-pressed={selected}
      onClick={onToggle}
      onKeyDown={(event) => {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          onToggle();
        }
      }}
    >
      <path className="tutorial-arc-visible" d={path} />
      <path className="tutorial-arc-hit" d={path} />
    </g>
  );
}

function LessonOne({ onReady }: { onReady: (ready: boolean) => void }) {
  const [selected, setSelected] = useState(false);
  const toggle = () => {
    const next = !selected;
    setSelected(next);
    onReady(next);
  };
  return (
    <div className="tutorial-demo single-arc-demo">
      <svg viewBox="0 0 300 200" aria-label="点击圆弧练习">
        <circle cx="150" cy="100" r="62" className="tutorial-guide-circle" />
        <ArcButton index={4} selected={selected} onToggle={toggle} label="练习圆弧" className={!selected ? "attention" : ""} />
        {!selected && <text x="80" y="56" className="tutorial-pointer">点击这里 ↘</text>}
      </svg>
      <div className={`tutorial-feedback ${selected ? "good" : "neutral"}`}>
        {selected ? "很好！彩色粗线就是你选中的曲线。再点一次可以删除它。" : "请点击正在闪烁的虚线圆弧。手机上直接用手指点即可。"}
      </div>
    </div>
  );
}

function LessonNumber({ onReady }: { onReady: (ready: boolean) => void }) {
  const [selected, setSelected] = useState<Set<number>>(new Set());
  const toggle = (index: number) => {
    const next = new Set(selected);
    next.has(index) ? next.delete(index) : next.add(index);
    setSelected(next);
    onReady(next.size === 2);
  };
  const count = selected.size;
  return (
    <div className="tutorial-demo">
      <svg viewBox="0 0 300 200" aria-label="数字二提示练习">
        <circle cx="150" cy="100" r="62" className="tutorial-guide-circle" />
        {[0, 1, 2, 3, 4, 5].map((index) => (
          <ArcButton key={index} index={index} selected={selected.has(index)} onToggle={() => toggle(index)} label={`边界圆弧 ${index + 1}`} />
        ))}
        <text x="150" y="100" className={`tutorial-big-clue ${count === 2 ? "satisfied" : count > 2 ? "over" : ""}`}>2</text>
      </svg>
      <div className={`count-meter ${count === 2 ? "good" : count > 2 ? "bad" : ""}`}>
        <span>已选边界圆弧</span><strong>{count} / 2</strong>
      </div>
      <div className={`tutorial-feedback ${count === 2 ? "good" : count > 2 ? "bad" : "neutral"}`}>
        {count === 2 ? "正好两条，数字 2 变绿了！弧的位置不限，数量正确即可。" : count > 2 ? "现在超过了数字要求。点掉多余圆弧，回到两条。" : "任意选择两条圆弧，让数字提示得到满足。"}
      </div>
    </div>
  );
}

function LessonVertex({ onReady }: { onReady: (ready: boolean) => void }) {
  const [third, setThird] = useState(false);
  const demonstrate = () => {
    setThird(true);
    onReady(true);
  };
  return (
    <div className="tutorial-demo vertex-demo">
      <svg viewBox="0 0 300 200" aria-label="分叉顶点演示">
        <path d="M 58 100 Q 102 46 150 100" className="demo-selected-line" />
        <path d="M 150 100 Q 204 154 248 100" className="demo-selected-line" />
        <g role="button" tabIndex={0} aria-label="添加第三条弧制造分叉" onClick={demonstrate} onKeyDown={(event) => { if (event.key === "Enter" || event.key === " ") demonstrate(); }}>
          <path d="M 150 100 Q 178 48 150 24" className={`demo-candidate-line ${third ? "selected bad" : "attention"}`} />
          <path d="M 150 100 Q 178 48 150 24" className="demo-candidate-hit" />
        </g>
        <circle cx="150" cy="100" r={third ? 12 : 7} className={third ? "bad-vertex" : "good-vertex"} />
        <text x="150" y="181" className="vertex-count">这个顶点连接了 {third ? 3 : 2} 条弧</text>
      </svg>
      <div className={`tutorial-feedback ${third ? "bad" : "neutral"}`}>
        {third ? "看，顶点变红了：三条弧在这里分叉。合法曲线经过一个顶点时只能一进一出。" : "目前两条弧在顶点处一进一出，是合法的。请点击上方虚线，故意制造一次分叉。"}
      </div>
    </div>
  );
}

function LoopPicture({ double }: { double: boolean }) {
  return (
    <svg viewBox="0 0 220 120" aria-hidden="true">
      {double ? (
        <><ellipse cx="67" cy="60" rx="42" ry="34" className="loop-a" /><ellipse cx="153" cy="60" rx="42" ry="34" className="loop-b" /></>
      ) : (
        <path d="M 30 60 C 30 18 82 18 110 48 C 138 18 190 18 190 60 C 190 102 138 102 110 72 C 82 102 30 102 30 60 Z" className="single-loop" />
      )}
    </svg>
  );
}

function LessonLoop({ onReady }: { onReady: (ready: boolean) => void }) {
  const [answer, setAnswer] = useState<"single" | "double" | null>(null);
  const choose = (value: "single" | "double") => {
    setAnswer(value);
    onReady(value === "single");
  };
  return (
    <div className="tutorial-demo">
      <p className="demo-question">哪一幅图满足“单一闭环”？请选一选。</p>
      <div className="loop-choice-grid">
        <button className={answer === "single" ? "chosen correct" : ""} onClick={() => choose("single")}><LoopPicture double={false} /><span>A · 一条连通曲线</span></button>
        <button className={answer === "double" ? "chosen wrong" : ""} onClick={() => choose("double")}><LoopPicture double /><span>B · 两个互不相连的小环</span></button>
      </div>
      <div className={`tutorial-feedback ${answer === "single" ? "good" : answer === "double" ? "bad" : "neutral"}`}>
        {answer === "single" ? "正确！形状可以弯弯绕绕，但整条曲线必须首尾相接并且全部连通。" : answer === "double" ? "两个图形分别闭合了，但合起来不是一个环，所以不能作为答案。再看看 A。" : "闭环不仅要没有端点，还必须只有一个。"}
      </div>
    </div>
  );
}

function LessonPi({ onReady }: { onReady: (ready: boolean) => void }) {
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const edges = [0, 1, 2, 3, 4, 5].map((sector) => ({ id: `main-${sector}`, sector, label: directionLabels[sector] }));
  edges.push({ id: "duplicate-0", sector: 0, label: "→" });
  const counts = useMemo(() => Array.from({ length: 6 }, (_, sector) => edges.filter((edge) => edge.sector === sector && selected.has(edge.id)).length), [selected]);
  const ready = counts.every((count) => count === 1);
  const toggle = (id: string) => {
    const next = new Set(selected);
    next.has(id) ? next.delete(id) : next.add(id);
    const nextCounts = Array.from({ length: 6 }, (_, sector) => edges.filter((edge) => edge.sector === sector && next.has(edge.id)).length);
    setSelected(next);
    onReady(nextCounts.every((count) => count === 1));
  };
  return (
    <div className="tutorial-demo pi-demo">
      <div className="pi-visual-row">
        <div className="pi-cells" aria-label="相邻的两个 π 单元格共享一条弧">
          <span>π</span><i className="shared-pi-arc" /><span>π</span>
          <small>同一条物理弧，只计算一次</small>
        </div>
        <div className="direction-compass" aria-label="π 六方向计数罗盘">
          <div className="pi-center">π</div>
          {counts.map((count, sector) => (
            <div key={sector} className={`direction-slot slot-${sector} ${count === 1 ? "filled" : count > 1 ? "over" : ""}`}>
              <span>{directionLabels[sector]}</span><b>{count}/1</b>
            </div>
          ))}
        </div>
      </div>
      <div className="direction-edge-buttons">
        {edges.map((edge) => (
          <button key={edge.id} className={`${selected.has(edge.id) ? "selected" : ""} ${counts[edge.sector] > 1 ? "over" : ""}`} onClick={() => toggle(edge.id)} aria-pressed={selected.has(edge.id)}>
            <span>{edge.label}</span>{edge.id === "duplicate-0" ? "额外的同方向弧" : `方向 ${edge.label}`}
          </button>
        ))}
      </div>
      <div className={`tutorial-feedback ${ready ? "good" : counts.some((count) => count > 1) ? "bad" : "neutral"}`}>
        {ready ? "六种方向恰好各一条，π 罗盘全部点亮！" : counts.some((count) => count > 1) ? "有一个方向出现了两次。删除该方向的一条弧，使每格回到 1/1。" : "点击方向弧，把六个方向槽依次点亮。留意：最右边还有一条重复方向的干扰弧。"}
      </div>
    </div>
  );
}

function LessonPractice({ onReady }: { onReady: (ready: boolean) => void }) {
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [message, setMessage] = useState("两个数字都是 5：请沿两个相邻单元格的外轮廓画出一条闭环。");
  const [valid, setValid] = useState(false);
  const toggle = (edgeId: string) => {
    const next = new Set(selected);
    next.has(edgeId) ? next.delete(edgeId) : next.add(edgeId);
    setSelected(next);
    setValid(false);
    onReady(false);
    setMessage("继续观察数字和顶点；完成后点击“检查我的闭环”。");
  };
  const check = () => {
    const result = validateSolutionEdges(tutorialPuzzle, selected);
    setValid(result.valid);
    onReady(result.valid);
    setMessage(result.valid ? "完成！两格各经过五条边，而且所有边首尾相连成一个闭环。" : result.message);
  };
  return (
    <div className="tutorial-demo practice-demo">
      <PuzzleBoard puzzle={tutorialPuzzle} selected={selected} onToggle={toggle} />
      <button type="button" className="tutorial-check-button" onClick={check}>检查我的闭环</button>
      <div className={`tutorial-feedback ${valid ? "good" : "neutral"}`}>{message}</div>
    </div>
  );
}

export function TutorialPage({ onBack, onComplete, onStartFirstPuzzle }: Props) {
  const stored = loadTutorialProgress();
  const [step, setStep] = useState(stored.completed ? 0 : stored.step);
  const [ready, setReady] = useState(false);
  const [finished, setFinished] = useState(false);
  const lesson = lessons[step];

  const move = (next: number) => {
    const bounded = Math.max(0, Math.min(lessons.length - 1, next));
    setStep(bounded);
    setReady(false);
    saveTutorialProgress(bounded, false);
  };

  const complete = () => {
    saveTutorialProgress(lessons.length - 1, true);
    setFinished(true);
    onComplete();
  };

  if (finished) {
    return (
      <main className="tutorial-page tutorial-finished">
        <div className="tutorial-finish-card">
          <div className="tutorial-finish-orbit">π</div>
          <p className="eyebrow dark">互动教程完成</p>
          <h1>你已经准备好挑战了！</h1>
          <p>你已经掌握画线、数字、顶点、单一闭环和 π 六方向规则。</p>
          <div className="finish-rule-badges"><span>数字 ✓</span><span>顶点 ✓</span><span>闭环 ✓</span><span>π ✓</span></div>
          <div className="tutorial-finish-actions">
            {onStartFirstPuzzle && <button className="primary-button" onClick={onStartFirstPuzzle}>挑战 TSH-01</button>}
            <button onClick={() => { setFinished(false); move(0); }}>重新学习</button>
            <button onClick={onBack}>返回选关</button>
          </div>
        </div>
      </main>
    );
  }

  return (
    <main className="tutorial-page">
      <header className="tutorial-header">
        <button type="button" className="back-button" onClick={onBack}>← 返回</button>
        <div className="tutorial-heading">
          <p>{lesson.kicker}</p><h1>{lesson.title}</h1>
        </div>
        <button type="button" className="tutorial-skip" onClick={onBack}>稍后再学</button>
      </header>
      <div className="tutorial-progress" aria-label={`教程进度，第 ${step + 1} 步，共 ${lessons.length} 步`}>
        {lessons.map((item, index) => <span key={item.title} className={index < step ? "done" : index === step ? "current" : ""}><i>{index < step ? "✓" : index + 1}</i><b>{item.kicker}</b></span>)}
      </div>

      <section className="tutorial-stage" key={step}>
        {step === 0 && <LessonOne onReady={setReady} />}
        {step === 1 && <LessonNumber onReady={setReady} />}
        {step === 2 && <LessonVertex onReady={setReady} />}
        {step === 3 && <LessonLoop onReady={setReady} />}
        {step === 4 && <LessonPi onReady={setReady} />}
        {step === 5 && <LessonPractice onReady={setReady} />}
      </section>

      <nav className="tutorial-nav" aria-label="教程步骤导航">
        <button type="button" onClick={() => move(step - 1)} disabled={step === 0}>← 上一步</button>
        <span>{step + 1} / {lessons.length}</span>
        <button type="button" className="primary-button" onClick={() => step === lessons.length - 1 ? complete() : move(step + 1)} disabled={!ready}>
          {step === lessons.length - 1 ? "完成教程" : "我明白了，继续 →"}
        </button>
      </nav>
    </main>
  );
}
