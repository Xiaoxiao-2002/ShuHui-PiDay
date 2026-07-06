import { useMemo, useState, type CSSProperties } from "react";
import { PuzzleBoard } from "./PuzzleBoard";
import { validateSolutionEdges } from "../validator";
import { loadTutorialProgress, piGuidedPuzzle, saveTutorialProgress, tutorialPuzzle, type TutorialProgressV1, type TutorialTrack } from "../tutorial";

interface TutorialPageProps {
  track: TutorialTrack;
  onBack: () => void;
  onExit: () => void;
  onComplete: () => void;
  onStartFirstPuzzle?: () => void;
}

interface TutorialHubProps {
  basic: TutorialProgressV1;
  pi: TutorialProgressV1;
  guided: TutorialProgressV1;
  onStart: (track: TutorialTrack) => void;
  onBack: () => void;
}

const basicLessons = [
  { title: "点一下，画出圆弧", kicker: "基本操作" },
  { title: "数字告诉你经过几条弧", kicker: "数字提示" },
  { title: "端点与分叉都不允许", kicker: "顶点规则" },
  { title: "所有曲线必须连成一个环", kicker: "单一闭环" },
  { title: "亲手完成一个小闭环", kicker: "综合练习" },
];

const piLessons = [
  { title: "一个圆周包含六类弧", kicker: "认识六类弧" },
  { title: "把重复类型改成缺失类型", kicker: "各类恰好一次" },
  { title: "公共弧只计算一次", kicker: "相邻 π 区域" },
];

const guidedLessons = [
  { title: "先找只有一种选择的弧", kicker: "π 的直接结论" },
  { title: "用顶点规则补完两处缺口", kicker: "连接端点" },
  { title: "逐项验证唯一闭环", kicker: "完成检查" },
];

function polar(cx: number, cy: number, radius: number, degrees: number) {
  const radians = (degrees * Math.PI) / 180;
  return { x: cx + radius * Math.cos(radians), y: cy + radius * Math.sin(radians) };
}

function circleArcPath(sector: number, cx = 150, cy = 100, radius = 62): string {
  const start = polar(cx, cy, radius, sector * 60);
  const end = polar(cx, cy, radius, (sector + 1) * 60);
  return `M ${start.x} ${start.y} A ${radius} ${radius} 0 0 1 ${end.x} ${end.y}`;
}

function ArcButton({ index, selected, onToggle, label, className = "" }: { index: number; selected: boolean; onToggle: () => void; label: string; className?: string }) {
  const path = circleArcPath(index);
  return (
    <g className={`tutorial-arc ${selected ? "selected" : ""} ${className}`} role="button" tabIndex={0} aria-label={label} aria-pressed={selected} onClick={onToggle} onKeyDown={(event) => {
      if (event.key === "Enter" || event.key === " ") { event.preventDefault(); onToggle(); }
    }}>
      <path className="tutorial-arc-visible" d={path} />
      <path className="tutorial-arc-hit" d={path} />
    </g>
  );
}

function SectorGlyph({ sector, active = true }: { sector: number; active?: boolean }) {
  return (
    <svg className="sector-glyph" viewBox="0 0 60 60" aria-hidden="true">
      <circle cx="30" cy="30" r="21" />
      <path d={circleArcPath(sector, 30, 30, 21)} className={active ? `active sector-color-${sector}` : ""} />
    </svg>
  );
}

function LessonOne({ onReady }: { onReady: (ready: boolean) => void }) {
  const [selected, setSelected] = useState(false);
  const toggle = () => { const next = !selected; setSelected(next); onReady(next); };
  return (
    <div className="tutorial-demo single-arc-demo">
      <svg viewBox="0 0 300 200" aria-label="点击圆弧练习">
        <circle cx="150" cy="100" r="62" className="tutorial-guide-circle" />
        <ArcButton index={4} selected={selected} onToggle={toggle} label="练习圆弧" className={!selected ? "attention" : ""} />
        {!selected && <text x="150" y="23" textAnchor="middle" className="tutorial-pointer">点击下方弧线 ↓</text>}
      </svg>
      <div className={`tutorial-feedback ${selected ? "good" : "neutral"}`}>{selected ? "很好！彩色粗线就是选中的曲线。再点一次可以删除它。" : "请点击正在闪烁的虚线圆弧。手机上直接用手指点即可。"}</div>
    </div>
  );
}

function LessonNumber({ onReady }: { onReady: (ready: boolean) => void }) {
  const [selected, setSelected] = useState<Set<number>>(new Set());
  const toggle = (index: number) => {
    const next = new Set(selected); next.has(index) ? next.delete(index) : next.add(index); setSelected(next); onReady(next.size === 2);
  };
  const count = selected.size;
  return (
    <div className="tutorial-demo">
      <svg viewBox="0 0 300 200" aria-label="数字二提示练习">
        <circle cx="150" cy="100" r="62" className="tutorial-guide-circle" />
        {[0, 1, 2, 3, 4, 5].map((index) => <ArcButton key={index} index={index} selected={selected.has(index)} onToggle={() => toggle(index)} label={`边界圆弧 ${index + 1}`} />)}
        <text x="150" y="100" className={`tutorial-big-clue ${count === 2 ? "satisfied" : count > 2 ? "over" : ""}`}>2</text>
      </svg>
      <div className={`count-meter ${count === 2 ? "good" : count > 2 ? "bad" : ""}`}><span>已选边界圆弧</span><strong>{count} / 2</strong></div>
      <div className={`tutorial-feedback ${count === 2 ? "good" : count > 2 ? "bad" : "neutral"}`}>{count === 2 ? "正好两条，数字 2 得到满足。弧的位置不限，数量正确即可。" : count > 2 ? "现在超过了数字要求。点掉多余圆弧，回到两条。" : "任意选择两条圆弧，让数字提示得到满足。"}</div>
    </div>
  );
}

function LessonVertex({ onReady }: { onReady: (ready: boolean) => void }) {
  const [third, setThird] = useState(false);
  const demonstrate = () => { setThird(true); onReady(true); };
  return (
    <div className="tutorial-demo vertex-demo">
      <svg viewBox="0 0 300 200" aria-label="分叉顶点演示">
        <path d="M 58 100 Q 102 46 150 100" className="demo-selected-line" /><path d="M 150 100 Q 204 154 248 100" className="demo-selected-line" />
        <g role="button" tabIndex={0} aria-label="添加第三条弧制造分叉" onClick={demonstrate} onKeyDown={(event) => { if (event.key === "Enter" || event.key === " ") demonstrate(); }}>
          <path d="M 150 100 Q 178 48 150 24" className={`demo-candidate-line ${third ? "selected bad" : "attention"}`} /><path d="M 150 100 Q 178 48 150 24" className="demo-candidate-hit" />
        </g>
        <circle cx="150" cy="100" r={third ? 12 : 7} className={third ? "bad-vertex" : "good-vertex"} /><text x="150" y="181" className="vertex-count">这个顶点连接了 {third ? 3 : 2} 条弧</text>
      </svg>
      <div className={`tutorial-feedback ${third ? "bad" : "neutral"}`}>{third ? "顶点变红了：三条弧在这里分叉。合法曲线经过一个顶点时只能一进一出。" : "目前两条弧在顶点处一进一出。请点击上方虚线，故意制造一次分叉。"}</div>
    </div>
  );
}

function LoopPicture({ double }: { double: boolean }) {
  return <svg viewBox="0 0 220 120" aria-hidden="true">{double ? <><ellipse cx="67" cy="60" rx="42" ry="34" className="loop-a" /><ellipse cx="153" cy="60" rx="42" ry="34" className="loop-b" /></> : <path d="M 30 60 C 30 18 82 18 110 48 C 138 18 190 18 190 60 C 190 102 138 102 110 72 C 82 102 30 102 30 60 Z" className="single-loop" />}</svg>;
}

function LessonLoop({ onReady }: { onReady: (ready: boolean) => void }) {
  const [answer, setAnswer] = useState<"single" | "double" | null>(null);
  const choose = (value: "single" | "double") => { setAnswer(value); onReady(value === "single"); };
  return (
    <div className="tutorial-demo"><p className="demo-question">哪一幅图满足“单一闭环”？</p><div className="loop-choice-grid">
      <button className={answer === "single" ? "chosen correct" : ""} onClick={() => choose("single")}><LoopPicture double={false} /><span>A · 一条连通曲线</span></button>
      <button className={answer === "double" ? "chosen wrong" : ""} onClick={() => choose("double")}><LoopPicture double /><span>B · 两个互不相连的小环</span></button>
    </div><div className={`tutorial-feedback ${answer === "single" ? "good" : answer === "double" ? "bad" : "neutral"}`}>{answer === "single" ? "正确！整条曲线首尾相接，而且所有部分互相连通。" : answer === "double" ? "两个图形分别闭合了，但合起来不是一个环。再看看 A。" : "闭环不仅要没有端点，还必须只有一个。"}</div></div>
  );
}

function LessonPractice({ onReady }: { onReady: (ready: boolean) => void }) {
  const [selected, setSelected] = useState<Set<string>>(new Set()); const [valid, setValid] = useState(false);
  const [message, setMessage] = useState("两个数字都是 5：请沿两个相邻单元格的外轮廓画出一条闭环。");
  const toggle = (edgeId: string) => { const next = new Set(selected); next.has(edgeId) ? next.delete(edgeId) : next.add(edgeId); setSelected(next); setValid(false); onReady(false); setMessage("继续观察数字和顶点；完成后点击“检查我的闭环”。"); };
  const check = () => { const result = validateSolutionEdges(tutorialPuzzle, selected); setValid(result.valid); onReady(result.valid); setMessage(result.valid ? "完成！两格各经过五条边，并且所有边连成一个闭环。" : result.message); };
  return <div className="tutorial-demo practice-demo"><PuzzleBoard puzzle={tutorialPuzzle} selected={selected} onToggle={toggle} /><button type="button" className="tutorial-check-button" onClick={check}>检查我的闭环</button><div className={`tutorial-feedback ${valid ? "good" : "neutral"}`}>{message}</div></div>;
}

function PiArcButton({ sector, selected, expected, onClick }: { sector: number; selected: boolean; expected: boolean; onClick: () => void }) {
  const path = circleArcPath(sector, 150, 108, 72);
  return <g role="button" tabIndex={0} aria-label={`点亮第 ${sector + 1} 类圆弧`} aria-pressed={selected} className={`pi-learn-arc ${selected ? `selected sector-color-${sector}` : ""} ${expected ? "expected" : ""}`} onClick={onClick} onKeyDown={(event) => { if (event.key === "Enter" || event.key === " ") onClick(); }}><path d={path} className="visible" /><path d={path} className="hit" /></g>;
}

function LessonPiArcTypes({ onReady }: { onReady: (ready: boolean) => void }) {
  const [lit, setLit] = useState(0); const [hint, setHint] = useState("请从闪烁的第一段开始，沿圆周依次点亮六段弧。");
  const choose = (sector: number) => {
    if (sector !== lit) { setHint(`现在轮到第 ${lit + 1} 类。请点击正在闪烁的圆弧。`); return; }
    const next = lit + 1; setLit(next); onReady(next === 6); setHint(next === 6 ? "六段弧拼成了一个完整圆周；它们就是 π 规则中的六类弧。" : `很好。接着点亮第 ${next + 1} 类。`);
  };
  return <div className="tutorial-demo pi-arc-types-demo"><div className="pi-isolated-note">本教程只解释 π 的额外约束；数字、顶点和闭环规则已放在“数回基础”教程中。</div><svg viewBox="0 0 300 220" aria-label="依次点亮圆周上的六类弧"><circle cx="150" cy="108" r="72" className="tutorial-guide-circle" />{[0,1,2,3,4,5].map((sector) => <PiArcButton key={sector} sector={sector} selected={sector < lit} expected={sector === lit} onClick={() => choose(sector)} />)}<text x="150" y="103" className="pi-type-center">{lit}/6</text><text x="150" y="126" className="pi-type-caption">已认识</text></svg><div className="pi-type-legend">{[0,1,2,3,4,5].map((sector) => <span key={sector} className={sector < lit ? `lit sector-bg-${sector}` : ""}>第 {sector + 1} 类</span>)}</div><div className={`tutorial-feedback ${lit === 6 ? "good" : "neutral"}`}>{hint}</div></div>;
}

function PiRegionCircle({ name, selected, editable, onToggle }: { name: string; selected: Set<number>; editable?: boolean; onToggle?: (sector: number) => void }) {
  return <div className={`pi-region ${editable ? "editable" : "fixed"}`}><div className="pi-region-title"><strong>{name}</strong><span>{editable ? "可以修改" : "固定，不能修改"}</span></div><svg viewBox="0 0 150 150" aria-label={`${name}${editable ? "可修改" : "固定"}`}><circle cx="75" cy="75" r="50" className="pi-region-circle" />{[0,1,2,3,4,5].map((sector) => <g key={sector} role={editable ? "button" : undefined} tabIndex={editable ? 0 : undefined} aria-label={editable ? `${name}第 ${sector + 1} 类圆弧` : undefined} aria-pressed={editable ? selected.has(sector) : undefined} onClick={editable ? () => onToggle?.(sector) : undefined} onKeyDown={editable ? (event) => { if (event.key === "Enter" || event.key === " ") onToggle?.(sector); } : undefined}><path d={circleArcPath(sector,75,75,50)} className="pi-region-candidate" />{selected.has(sector) && <path d={circleArcPath(sector,75,75,50)} className={`pi-region-selected sector-color-${sector}`} />}{editable && <path d={circleArcPath(sector,75,75,50)} className="pi-region-hit" />}</g>)}<text x="75" y="78" className="pi-region-symbol">π</text></svg></div>;
}

function LessonPiBalance({ onReady }: { onReady: (ready: boolean) => void }) {
  const fixedA = useMemo(() => new Set([0,1]), []); const fixedB = useMemo(() => new Set([2,3]), []); const [editable, setEditable] = useState(new Set([0,2]));
  const counts = [0,1,2,3,4,5].map((sector) => Number(fixedA.has(sector)) + Number(fixedB.has(sector)) + Number(editable.has(sector)));
  const ready = counts.every((count) => count === 1);
  const toggle = (sector: number) => { const next = new Set(editable); next.has(sector) ? next.delete(sector) : next.add(sector); const nextCounts = [0,1,2,3,4,5].map((item) => Number(fixedA.has(item)) + Number(fixedB.has(item)) + Number(next.has(item))); setEditable(next); onReady(nextCounts.every((count) => count === 1)); };
  const duplicates = counts.flatMap((count, sector) => count > 1 ? [sector + 1] : []); const missing = counts.flatMap((count, sector) => count === 0 ? [sector + 1] : []);
  return <div className="tutorial-demo pi-balance-demo"><div className="pi-isolated-note"><b>本步只检查 π：</b>暂时不考虑数字、端点、分叉或是否形成闭环。</div><div className="pi-region-grid"><PiRegionCircle name="π 区域 1" selected={fixedA} /><PiRegionCircle name="π 区域 2" selected={fixedB} /><PiRegionCircle name="π 区域 3" selected={editable} editable onToggle={toggle} /></div><div className="pi-balance-board">{counts.map((count, sector) => <div key={sector} className={count === 1 ? "ok" : count > 1 ? "duplicate" : "missing"}><SectorGlyph sector={sector} /><span>第 {sector + 1} 类</span><b>{count}/1</b></div>)}</div><div className={`tutorial-feedback ${ready ? "good" : "bad"}`}>{ready ? "完成！三个 π 区域合在一起，六类弧恰好各出现一次。" : <>区域 1、2 已固定。请只修改区域 3：{duplicates.length > 0 && <b> 删除重复的第 {duplicates.join("、")} 类；</b>}{missing.length > 0 && <b> 补上缺少的第 {missing.join("、")} 类。</b>}</>}</div></div>;
}

function LessonPiShared({ onReady }: { onReady: (ready: boolean) => void }) {
  const [selected, setSelected] = useState(false); const choose = () => { setSelected(true); onReady(true); };
  return <div className="tutorial-demo pi-shared-demo"><p className="pi-lesson-lead">最后看标准三圆密堆积中的情况：左上圆单元格和中间圆隙区域都有 π，它们共用一条边界弧。</p><svg viewBox="0 0 360 230" aria-label="三个相切圆形成的 π 圆隙区域"><circle cx="105" cy="70" r="50" className="pi-pack-circle" /><circle cx="205" cy="70" r="50" className="pi-pack-circle" /><circle cx="155" cy="156.6" r="50" className="pi-pack-circle" /><text x="105" y="72" className="pi-scope-symbol">π</text><text x="155" y="104" className="pi-scope-symbol small">π</text><g role="button" tabIndex={0} aria-label="两个 π 区域的公共弧" aria-pressed={selected} onClick={choose} onKeyDown={(event) => { if (event.key === "Enter" || event.key === " ") choose(); }}><path d={circleArcPath(0,105,70,50)} className={`pi-shared-visible ${selected ? "selected" : "attention"}`} /><path d={circleArcPath(0,105,70,50)} className="pi-shared-hit" /></g><text x="267" y="112" className="pi-scope-label">点击公共弧</text></svg><div className="pi-count-explanation"><span>邻接 π 区域 <b>2 个</b></span><strong>同一条圆弧</strong><span>计入对应类别 <b>{selected ? 1 : 0} 次</b></span></div><div className={`tutorial-feedback ${selected ? "good" : "neutral"}`}>{selected ? "正确。先把所有 π 区域的边界弧合并成一个集合，再按六类计数；同一条公共弧在集合中只有一份。" : "请点击公共弧。它虽然同时属于两个 π 区域的边界，但只是一条圆弧。"}</div></div>;
}

const guidedForcedEdges = new Set(["arc:0:0:0", "arc:0:0:1", "arc:0:0:3", "arc:0:0:5"]);
const guidedAnswerEdges = new Set([...guidedForcedEdges, "arc:0:0:2", "arc:0:0:4"]);

function GuidedStepOne({ selected, onChange, onReady }: { selected: Set<string>; onChange: (value: Set<string>) => void; onReady: (ready: boolean) => void }) {
  const [message, setMessage] = useState("先看六类统计：第 1、2、4、6 类都只有一条候选弧，因此它们必选。");
  const toggle = (edgeId: string) => {
    if (!guidedForcedEdges.has(edgeId)) { setMessage("这条弧属于尚有两种选择的类别，先暂缓。请点亮标着“只有 1 个候选”的四类弧。"); return; }
    const next = new Set(selected); next.has(edgeId) ? next.delete(edgeId) : next.add(edgeId); onChange(next);
    const ready = [...guidedForcedEdges].every((edge) => next.has(edge)); onReady(ready);
    setMessage(ready ? "很好。四类唯一候选已经确定，棋盘上出现了两个需要继续连接的缺口。" : `还需选中 ${[...guidedForcedEdges].filter((edge) => !next.has(edge)).length} 条唯一候选弧。`);
  };
  return <div className="tutorial-demo guided-demo"><div className="guided-intro"><b>题面只有两个 π，没有数字提示。</b>先只使用 π 的“六类各一次”，不要猜整条答案。</div><div className="guided-type-board">{[0,1,2,3,4,5].map((sector) => { const unique = [0,1,3,5].includes(sector); return <div key={sector} className={unique ? "unique" : "choice"}><SectorGlyph sector={sector} /><span>第 {sector + 1} 类</span><b>{unique ? "只有 1 个候选" : "有 2 个候选，暂缓"}</b></div>; })}</div><PuzzleBoard puzzle={piGuidedPuzzle} selected={selected} onToggle={toggle} /><div className={`tutorial-feedback ${[...guidedForcedEdges].every((edge) => selected.has(edge)) ? "good" : "neutral"}`}>{message}</div></div>;
}

function GuidedStepTwo({ selected, onChange, onReady }: { selected: Set<string>; onChange: (value: Set<string>) => void; onReady: (ready: boolean) => void }) {
  const [message, setMessage] = useState("第 3、5 类各剩两个候选。观察橙线端点：选择能让左上圆的曲线一进一出的圆弧。");
  const groups = [new Set(["arc:0:0:2", "arc:0:1:2"]), new Set(["arc:0:0:4", "arc:1:0:4"])];
  const toggle = (edgeId: string) => {
    const group = groups.find((items) => items.has(edgeId));
    if (!group) { setMessage("前一步确定的四条弧已经固定。本步只需处理第 3、5 类的四个候选。 "); return; }
    const next = new Set(selected); for (const item of group) next.delete(item); if (!selected.has(edgeId)) next.add(edgeId); onChange(next);
    const ready = [...guidedAnswerEdges].every((edge) => next.has(edge)) && !next.has("arc:0:1:2") && !next.has("arc:1:0:4"); onReady(ready);
    if (ready) setMessage("正确！两个缺口都被补上，左上圆周形成了完整曲线。现在还要验证它是不是合法答案。");
    else if (edgeId === "arc:0:1:2" || edgeId === "arc:1:0:4") setMessage("这条弧把路线引向另一个圆，却没有接上橙线的端点。试试同一类别的另一条候选弧。");
    else setMessage("这个选择接上了一个端点。继续处理另一个仍有缺口的类别。");
  };
  return <div className="tutorial-demo guided-demo"><div className="guided-rule-card"><span>第 3 类：二选一</span><span>第 5 类：二选一</span><strong>判断依据：每个经过的顶点必须恰好连接两条弧</strong></div><PuzzleBoard puzzle={piGuidedPuzzle} selected={selected} onToggle={toggle} /><div className={`tutorial-feedback ${[...guidedAnswerEdges].every((edge) => selected.has(edge)) ? "good" : "neutral"}`}>{message}</div></div>;
}

function GuidedStepThree({ selected, onReady }: { selected: Set<string>; onReady: (ready: boolean) => void }) {
  const [checked, setChecked] = useState(false);
  const result = validateSolutionEdges(piGuidedPuzzle, selected);
  const check = () => { setChecked(true); onReady(result.valid); };
  const counts = Array.from({ length: 6 }, (_, sector) => piGuidedPuzzle.topology.edges.filter((edge) => edge.sector === sector && selected.has(edge.id) && (piGuidedPuzzle.topology.cells.find((cell) => cell.id === "circle:0:0")!.edgeIds.includes(edge.id) || piGuidedPuzzle.topology.cells.find((cell) => cell.kind === "triangle")!.edgeIds.includes(edge.id))).length);
  return <div className="tutorial-demo guided-demo"><PuzzleBoard puzzle={piGuidedPuzzle} selected={selected} disabled onToggle={() => undefined} /><div className="guided-checklist"><div className={counts.every((count) => count === 1) ? "pass" : ""}><b>1</b><span>π 六类圆弧</span><strong>{counts.every((count) => count === 1) ? "各一次 ✓" : "尚未满足"}</strong></div><div className={result.code !== "degree" ? "pass" : ""}><b>2</b><span>顶点规则</span><strong>{result.code !== "degree" ? "无端点、无分叉 ✓" : "尚未满足"}</strong></div><div className={result.valid ? "pass" : ""}><b>3</b><span>整体结构</span><strong>{result.valid ? "单一闭环 ✓" : "等待验证"}</strong></div></div><button type="button" className="tutorial-check-button" onClick={check}>逐项验证我的答案</button><div className={`tutorial-feedback ${checked && result.valid ? "good" : "neutral"}`}>{checked ? result.valid ? "全部通过！你没有靠全提示，而是先用 π 确定四条弧，再用顶点规则补成了唯一闭环。" : result.message : "最后不要只凭外观看起来像圆：请同时检查 π、顶点和单一闭环。"}</div></div>;
}

export function TutorialHub({ basic, pi, guided, onStart, onBack }: TutorialHubProps) {
  const status = (progress: TutorialProgressV1, total: number) => progress.completed ? "✓ 已完成" : progress.step > 0 ? `继续第 ${progress.step + 1}/${total} 步` : "尚未开始";
  const action = (track: TutorialTrack, progress: TutorialProgressV1, initial: string) => <button onClick={() => onStart(track)}>{progress.completed ? "重新学习" : progress.step > 0 ? "继续教程" : initial} →</button>;
  return (
    <main className="tutorial-hub-page">
      <header className="tutorial-hub-header"><button className="back-button" onClick={onBack}>← 返回首页</button><div><p className="eyebrow dark">学习中心</p><h1>选择一个互动教程</h1><p>先分别理解基础规则与 π 约束，再到教程三把两者合起来使用。</p></div></header>
      <div className="tutorial-track-grid">
        <section className="tutorial-track-card basic-track"><span className="track-number">教程一</span><div className="track-icon">◯</div><h2>数回基础</h2><p>学习画线、数字提示、顶点规则和单一闭环，不包含 π。</p><ul><li>点击添加或删除曲线</li><li>数字表示边界弧数量</li><li>无端点、无分叉、只有一个环</li></ul><div className="track-footer"><b>{status(basic,5)}</b>{action("basic",basic,"开始教程")}</div></section>
        <section className="tutorial-track-card pi-track"><span className="track-number">教程二 · 特色重点</span><div className="track-icon">π</div><h2>π 约束专题</h2><p>暂时放下闭环，只用三个短练习弄清 π 到底怎样统计。</p><ul><li>在一个圆上认识六类弧</li><li>调整第三个 π 区域，做到各类一次</li><li>理解相邻 π 区域的公共弧</li></ul><div className="track-footer"><b>{status(pi,3)}</b>{action("pi",pi,"开始专题")}</div></section>
        <section className="tutorial-track-card guided-track"><span className="track-number">教程三 · 综合运用</span><div className="track-icon">✓</div><h2>π 小题引导</h2><p>一题只有两个 π 提示的三圆小题，跟着逻辑一步步完成，不直接展示答案。</p><ul><li>先用 π 找到四条唯一候选</li><li>再用顶点规则处理两处二选一</li><li>最后检查六类、顶点与单一闭环</li></ul><div className="track-footer"><b>{status(guided,3)}</b>{action("guided",guided,"开始综合题")}</div></section>
      </div>
    </main>
  );
}

export function TutorialPage({ track, onBack, onExit, onComplete, onStartFirstPuzzle }: TutorialPageProps) {
  const lessons = track === "basic" ? basicLessons : track === "pi" ? piLessons : guidedLessons; const stored = loadTutorialProgress(track);
  const [step, setStep] = useState(stored.completed ? 0 : stored.step); const [ready, setReady] = useState(false); const [finished, setFinished] = useState(false); const [guidedSelected, setGuidedSelected] = useState<Set<string>>(new Set()); const lesson = lessons[step];
  const move = (next: number) => { const bounded = Math.max(0, Math.min(lessons.length - 1, next)); setStep(bounded); setReady(false); saveTutorialProgress(track, bounded, false); };
  const complete = () => { saveTutorialProgress(track, lessons.length - 1, true); setFinished(true); onComplete(); };
  const labels = track === "basic" ? { orbit:"◯", eyebrow:"数回基础完成", title:"基础规则已经掌握！", summary:"现在你能识别数字、端点、分叉和单一闭环。还可以继续学习 π 专题。", header:"教程一 · 数回基础" } : track === "pi" ? { orbit:"π", eyebrow:"π 专题完成", title:"你已经掌握 π 约束了！", summary:"汇总所有 π 区域的边界已选弧，公共弧只留一份，再检查六类是否恰好各一条。", header:"教程二 · π 专题" } : { orbit:"✓", eyebrow:"综合教程完成", title:"你独立完成了 π 小题！", summary:"你已经把 π 的六类约束、顶点规则和单一闭环连接成了一条完整推理链。", header:"教程三 · 综合运用" };
  if (finished) return <main className="tutorial-page tutorial-finished"><div className="tutorial-finish-card"><div className="tutorial-finish-orbit">{labels.orbit}</div><p className="eyebrow dark">{labels.eyebrow}</p><h1>{labels.title}</h1><p>{labels.summary}</p><div className="tutorial-finish-actions">{onStartFirstPuzzle && <button className="primary-button" onClick={onStartFirstPuzzle}>挑战第一关</button>}<button onClick={() => { setFinished(false); setGuidedSelected(new Set()); move(0); }}>重新学习</button><button onClick={onBack}>返回教程中心</button></div></div></main>;
  return <main className={`tutorial-page tutorial-track-${track}`}><header className="tutorial-header"><button type="button" className="back-button" onClick={onBack}>← 教程中心</button><div className="tutorial-heading"><p>{labels.header} · {lesson.kicker}</p><h1>{lesson.title}</h1></div><button type="button" className="tutorial-skip" onClick={onExit}>稍后再学</button></header><div className="tutorial-progress" style={{ "--lesson-count": lessons.length } as CSSProperties} aria-label={`教程进度，第 ${step + 1} 步，共 ${lessons.length} 步`}>{lessons.map((item,index) => <span key={item.title} className={index < step ? "done" : index === step ? "current" : ""}><i>{index < step ? "✓" : index + 1}</i><b>{item.kicker}</b></span>)}</div><section className="tutorial-stage" key={`${track}-${step}`}>{track === "basic" && step === 0 && <LessonOne onReady={setReady} />}{track === "basic" && step === 1 && <LessonNumber onReady={setReady} />}{track === "basic" && step === 2 && <LessonVertex onReady={setReady} />}{track === "basic" && step === 3 && <LessonLoop onReady={setReady} />}{track === "basic" && step === 4 && <LessonPractice onReady={setReady} />}{track === "pi" && step === 0 && <LessonPiArcTypes onReady={setReady} />}{track === "pi" && step === 1 && <LessonPiBalance onReady={setReady} />}{track === "pi" && step === 2 && <LessonPiShared onReady={setReady} />}{track === "guided" && step === 0 && <GuidedStepOne selected={guidedSelected} onChange={setGuidedSelected} onReady={setReady} />}{track === "guided" && step === 1 && <GuidedStepTwo selected={guidedSelected} onChange={setGuidedSelected} onReady={setReady} />}{track === "guided" && step === 2 && <GuidedStepThree selected={guidedSelected} onReady={setReady} />}</section><nav className="tutorial-nav" aria-label="教程步骤导航"><button type="button" onClick={() => move(step - 1)} disabled={step === 0}>← 上一步</button><span>{step + 1} / {lessons.length}</span><button type="button" className="primary-button" onClick={() => step === lessons.length - 1 ? complete() : move(step + 1)} disabled={!ready}>{step === lessons.length - 1 ? "完成教程" : "我明白了，继续 →"}</button></nav></main>;
}
