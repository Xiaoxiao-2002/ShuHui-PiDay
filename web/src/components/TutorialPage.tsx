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
  { title: "先找出哪些弧归 π 管", kicker: "π · 范围" },
  { title: "认识六类圆弧", kicker: "π · 分类" },
  { title: "六类圆弧必须恰好各一条", kicker: "π · 规则" },
  { title: "亲手完成一个小闭环", kicker: "综合练习" },
];

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

function sectorPath(sector: number, cx = 30, cy = 30, radius = 21): string {
  const start = polar(cx, cy, radius, sector * 60);
  const end = polar(cx, cy, radius, (sector + 1) * 60);
  return `M ${start.x} ${start.y} A ${radius} ${radius} 0 0 1 ${end.x} ${end.y}`;
}

function SectorGlyph({ sector, active = true }: { sector: number; active?: boolean }) {
  return (
    <svg className="sector-glyph" viewBox="0 0 60 60" aria-hidden="true">
      <circle cx="30" cy="30" r="21" />
      <path d={sectorPath(sector)} className={active ? "active" : ""} />
    </svg>
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

function LessonPiScope({ onReady }: { onReady: (ready: boolean) => void }) {
  const [selected, setSelected] = useState(false);
  const chooseSharedArc = () => {
    setSelected(true);
    onReady(true);
  };
  return (
    <div className="tutorial-demo pi-scope-demo">
      <p className="pi-lesson-lead">先把所有带 π 的单元格放在一起看。只要一条已选弧与<strong>至少一个</strong> π 单元格相邻，它就进入 π 的统计范围。</p>
      <svg viewBox="0 0 360 220" aria-label="圆单元格与圆隙三角形共享一条物理圆弧">
        <circle cx="122" cy="108" r="70" className="pi-scope-circle" />
        <path d="M 192 108 Q 230 111 246 166 Q 197 185 157 169" className="pi-scope-triangle" />
        <text x="110" y="110" className="pi-scope-symbol">π</text>
        <text x="213" y="151" className="pi-scope-symbol small">π</text>
        <g role="button" tabIndex={0} aria-label="同时邻接两个 π 单元格的共享圆弧" aria-pressed={selected} onClick={chooseSharedArc} onKeyDown={(event) => { if (event.key === "Enter" || event.key === " ") chooseSharedArc(); }}>
          <path d={sectorPath(0, 122, 108, 70)} className={`pi-shared-visible ${selected ? "selected" : "attention"}`} />
          <path d={sectorPath(0, 122, 108, 70)} className="pi-shared-hit" />
        </g>
        <text x="270" y="93" className="pi-scope-label">点击共享弧</text>
      </svg>
      <div className="pi-count-explanation">
        <span>它邻接 π 单元格 <b>2 个</b></span><strong>但它是同一条物理弧</strong><span>进入统计集合 <b>{selected ? 1 : 0} 条</b></span>
      </div>
      <div className={`tutorial-feedback ${selected ? "good" : "neutral"}`}>
        {selected ? "正确。统计的是“不同的物理圆弧”，不是“它碰到了几个 π”。所以这条共享弧只出现一次。" : "请点击橙色共享弧，看看它究竟会被统计几次。"}
      </div>
    </div>
  );
}

function LessonPiSectors({ onReady }: { onReady: (ready: boolean) => void }) {
  const [seen, setSeen] = useState<Set<number>>(new Set());
  const inspect = (sector: number) => {
    const next = new Set(seen).add(sector);
    setSeen(next);
    onReady(next.size === 6);
  };
  return (
    <div className="tutorial-demo pi-sector-demo">
      <div className="pi-key-idea"><b>关键：</b>这里的“方向”不是箭头指向，而是圆周被六个相切点分成的<strong>六种固定位置</strong>。不同圆上处在同一位置的弧，属于同一类。</div>
      <div className="sector-library" aria-label="六类圆弧图例">
        {[0, 1, 2, 3, 4, 5].map((sector) => (
          <button key={sector} className={seen.has(sector) ? "seen" : ""} onClick={() => inspect(sector)} aria-label={`观察第 ${sector + 1} 类圆弧`}>
            <SectorGlyph sector={sector} /><span>第 {sector + 1} 类</span><i>{seen.has(sector) ? "已观察 ✓" : "点击观察"}</i>
          </button>
        ))}
      </div>
      <div className={`tutorial-feedback ${seen.size === 6 ? "good" : "neutral"}`}>
        {seen.size === 6 ? "六类圆弧合起来正好能拼成一个完整圆周。这就是 π 规则所说的“六种圆弧方向”。" : `请依次点击六张图，观察橙色弧在圆周上的位置。还剩 ${6 - seen.size} 类。`}
      </div>
    </div>
  );
}

function LessonPiRule({ onReady }: { onReady: (ready: boolean) => void }) {
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const edges = [0, 1, 2, 3, 4, 5].map((sector) => ({ id: `main-${sector}`, sector }));
  edges.push({ id: "duplicate-0", sector: 0 });
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
    <div className="tutorial-demo pi-rule-demo">
      <p className="pi-lesson-lead">现在只看“进入 π 统计范围的已选弧”。目标是让下面六个收集槽都<strong>恰好为 1/1</strong>。</p>
      <div className="sector-collection" aria-label="π 六类圆弧计数">
        {counts.map((count, sector) => (
          <div key={sector} className={`${count === 1 ? "filled" : count > 1 ? "over" : ""}`}>
            <SectorGlyph sector={sector} active={count > 0} /><span>第 {sector + 1} 类</span><b>{count}/1</b>
          </div>
        ))}
      </div>
      <div className="pi-candidate-heading"><span>下面每张卡代表一条不同的物理弧</span><small>最后一张是与第一张同类的干扰项</small></div>
      <div className="pi-candidate-edges">
        {edges.map((edge) => (
          <button key={edge.id} className={`${selected.has(edge.id) ? "selected" : ""} ${counts[edge.sector] > 1 ? "over" : ""}`} onClick={() => toggle(edge.id)} aria-pressed={selected.has(edge.id)}>
            <SectorGlyph sector={edge.sector} />
            <span>{edge.id === "duplicate-0" ? "另一个圆上的第 1 类" : `候选弧 · 第 ${edge.sector + 1} 类`}</span>
          </button>
        ))}
      </div>
      <div className={`tutorial-feedback ${ready ? "good" : counts.some((count) => count > 1) ? "bad" : "neutral"}`}>
        {ready ? "完成：六类圆弧各选一条。把这六段按类别摆在一起，正好组成一个完整圆周。" : counts.some((count) => count > 1) ? "某一类出现了两条。即使它们来自不同圆，也属于同一类；请删掉其中一条。" : "请选择候选弧，填满六个槽。可以故意选择最后的同类干扰项，看看为什么不能重复。"}
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
          <p>你已经掌握画线、数字、顶点、单一闭环和 π 六类圆弧规则。</p>
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
        {step === 4 && <LessonPiScope onReady={setReady} />}
        {step === 5 && <LessonPiSectors onReady={setReady} />}
        {step === 6 && <LessonPiRule onReady={setReady} />}
        {step === 7 && <LessonPractice onReady={setReady} />}
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
