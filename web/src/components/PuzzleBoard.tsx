import { useMemo, useRef, useState } from "react";
import type { EdgeV1, PlayablePuzzleV1 } from "../types";

interface Props {
  puzzle: PlayablePuzzleV1;
  selected: Set<string>;
  disabled?: boolean;
  onToggle: (edgeId: string) => void;
}

interface ViewBox {
  x: number;
  y: number;
  width: number;
  height: number;
}

function edgePath(edge: EdgeV1, vertices: Map<string, { x: number; y: number }>): string {
  const start = vertices.get(edge.vertices[0])!;
  const end = vertices.get(edge.vertices[1])!;
  if (!edge.circle) return `M ${start.x} ${start.y} L ${end.x} ${end.y}`;
  return `M ${start.x} ${start.y} A ${edge.circle.radius} ${edge.circle.radius} 0 0 1 ${end.x} ${end.y}`;
}

export function PuzzleBoard({ puzzle, selected, disabled = false, onToggle }: Props) {
  const vertices = useMemo(
    () => new Map(puzzle.topology.vertices.map((vertex) => [vertex.id, vertex])),
    [puzzle],
  );
  const cells = useMemo(() => new Map(puzzle.topology.cells.map((cell) => [cell.id, cell])), [puzzle]);
  const base = useMemo<ViewBox>(() => {
    const bounds = puzzle.topology.bounds;
    const padding = 0.42;
    return {
      x: bounds.minX - padding,
      y: bounds.minY - padding,
      width: bounds.maxX - bounds.minX + padding * 2,
      height: bounds.maxY - bounds.minY + padding * 2,
    };
  }, [puzzle]);
  const [view, setView] = useState<ViewBox>(base);
  const svgRef = useRef<SVGSVGElement>(null);
  const pointers = useRef(new Map<number, { x: number; y: number }>());
  const drag = useRef<{
    pointerId: number;
    startX: number;
    startY: number;
    lastX: number;
    lastY: number;
    moved: boolean;
    edgeId?: string;
  } | null>(null);
  const pinch = useRef<{ distance: number; view: ViewBox } | null>(null);

  const zoomBy = (factor: number) => {
    setView((current) => {
      const width = Math.min(base.width, Math.max(base.width / 6, current.width * factor));
      const height = width * (base.height / base.width);
      return {
        x: current.x + (current.width - width) / 2,
        y: current.y + (current.height - height) / 2,
        width,
        height,
      };
    });
  };

  const handlePointerDown = (event: React.PointerEvent<SVGSVGElement>) => {
    if (disabled) return;
    event.currentTarget.setPointerCapture?.(event.pointerId);
    pointers.current.set(event.pointerId, { x: event.clientX, y: event.clientY });
    const target = event.target as SVGElement;
    drag.current = {
      pointerId: event.pointerId,
      startX: event.clientX,
      startY: event.clientY,
      lastX: event.clientX,
      lastY: event.clientY,
      moved: false,
      edgeId: target.dataset.edgeId,
    };
    if (pointers.current.size === 2) {
      const [a, b] = [...pointers.current.values()];
      pinch.current = { distance: Math.hypot(a.x - b.x, a.y - b.y), view: { ...view } };
    }
  };

  const handlePointerMove = (event: React.PointerEvent<SVGSVGElement>) => {
    if (!pointers.current.has(event.pointerId) || !svgRef.current) return;
    pointers.current.set(event.pointerId, { x: event.clientX, y: event.clientY });
    if (pointers.current.size >= 2 && pinch.current) {
      const [a, b] = [...pointers.current.values()];
      const distance = Math.max(1, Math.hypot(a.x - b.x, a.y - b.y));
      const factor = pinch.current.distance / distance;
      const width = Math.min(base.width, Math.max(base.width / 6, pinch.current.view.width * factor));
      const height = width * (base.height / base.width);
      setView({
        x: pinch.current.view.x + (pinch.current.view.width - width) / 2,
        y: pinch.current.view.y + (pinch.current.view.height - height) / 2,
        width,
        height,
      });
      if (drag.current) drag.current.moved = true;
      return;
    }
    if (!drag.current || drag.current.pointerId !== event.pointerId) return;
    const rect = svgRef.current.getBoundingClientRect();
    const dx = event.clientX - drag.current.lastX;
    const dy = event.clientY - drag.current.lastY;
    if (Math.hypot(event.clientX - drag.current.startX, event.clientY - drag.current.startY) > 6) {
      drag.current.moved = true;
    }
    if (drag.current.moved) {
      setView((current) => ({
        ...current,
        x: current.x - (dx / Math.max(1, rect.width)) * current.width,
        y: current.y - (dy / Math.max(1, rect.height)) * current.height,
      }));
    }
    drag.current.lastX = event.clientX;
    drag.current.lastY = event.clientY;
  };

  const handlePointerUp = (event: React.PointerEvent<SVGSVGElement>) => {
    pointers.current.delete(event.pointerId);
    if (pointers.current.size < 2) pinch.current = null;
    if (drag.current?.pointerId === event.pointerId) {
      if (!drag.current.moved && drag.current.edgeId) onToggle(drag.current.edgeId);
      drag.current = null;
    }
  };

  const clueMap = useMemo(() => new Map(puzzle.clues.map((clue) => [clue.cellId, clue])), [puzzle]);
  const fontSize = Math.max(0.12, Math.min(0.23, base.width / 42));

  return (
    <div className="board-shell">
      <svg
        ref={svgRef}
        className="puzzle-board"
        viewBox={`${view.x} ${view.y} ${view.width} ${view.height}`}
        role="application"
        aria-label={`${puzzle.id} 特色数回棋盘`}
        onPointerDown={handlePointerDown}
        onPointerMove={handlePointerMove}
        onPointerUp={handlePointerUp}
        onPointerCancel={handlePointerUp}
        onWheel={(event) => {
          event.preventDefault();
          zoomBy(event.deltaY < 0 ? 0.82 : 1.22);
        }}
      >
        <rect x={view.x} y={view.y} width={view.width} height={view.height} className="board-background" />
        <g className="candidate-edges">
          {puzzle.topology.edges.map((edge) => (
            <path key={edge.id} d={edgePath(edge, vertices)} />
          ))}
        </g>
        <g className="selected-edges">
          {puzzle.topology.edges
            .filter((edge) => selected.has(edge.id))
            .map((edge) => (
              <path key={edge.id} d={edgePath(edge, vertices)} />
            ))}
        </g>
        <g className="clues" style={{ fontSize }}>
          {[...clueMap.entries()].map(([cellId, clue]) => {
            const cell = cells.get(cellId);
            if (!cell) return null;
            return (
              <text key={cellId} x={cell.center[0]} y={cell.center[1]}>
                {clue.kind === "pi" ? "π" : clue.value}
              </text>
            );
          })}
        </g>
        {!disabled && (
          <g className="edge-hit-areas">
            {puzzle.topology.edges.map((edge) => (
              <path key={edge.id} d={edgePath(edge, vertices)} data-edge-id={edge.id} />
            ))}
          </g>
        )}
      </svg>
      <div className="zoom-controls" aria-label="棋盘缩放">
        <button type="button" onClick={() => zoomBy(0.8)} aria-label="放大">＋</button>
        <button type="button" onClick={() => zoomBy(1.25)} aria-label="缩小">－</button>
        <button type="button" onClick={() => setView(base)}>复位</button>
      </div>
    </div>
  );
}
