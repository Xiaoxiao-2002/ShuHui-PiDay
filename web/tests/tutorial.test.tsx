import { fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { TutorialPage } from "../src/components/TutorialPage";
import { loadTutorialProgress, piGuidedPuzzle, saveTutorialProgress, tutorialPuzzle } from "../src/tutorial";
import { validateSolutionEdges } from "../src/validator";

const outerEdges = ["a-lower-right", "a-bottom-left", "a-left", "a-top-left", "a-upper-right", "b-upper-left", "b-top-right", "b-right", "b-bottom-right", "b-lower-left"];
const callbacks = () => ({ onBack: vi.fn(), onExit: vi.fn(), onComplete: vi.fn() });

describe("tutorial data", () => {
  it("persists the two tutorial tracks independently", () => {
    saveTutorialProgress("basic", 3);
    saveTutorialProgress("pi", 1, true);
    saveTutorialProgress("guided", 2);
    expect(loadTutorialProgress("basic")).toMatchObject({ step: 3, completed: false });
    expect(loadTutorialProgress("pi")).toMatchObject({ step: 1, completed: true });
    expect(loadTutorialProgress("guided")).toMatchObject({ step: 2, completed: false });
  });

  it("has a valid guided-practice solution", () => {
    expect(validateSolutionEdges(tutorialPuzzle, outerEdges).valid).toBe(true);
    expect(validateSolutionEdges(tutorialPuzzle, [...outerEdges, "shared"]).valid).toBe(false);
  });

  it("uses a sparse, valid pi puzzle for the combined tutorial", () => {
    const answer = Array.from({ length: 6 }, (_, sector) => `arc:0:0:${sector}`);
    expect(piGuidedPuzzle.clues).toHaveLength(2);
    expect(piGuidedPuzzle.clues.every((clue) => clue.kind === "pi")).toBe(true);
    expect(validateSolutionEdges(piGuidedPuzzle, answer).valid).toBe(true);
  });
});

describe("TutorialPage", () => {
  it("can complete the five-step basic tutorial without pi", async () => {
    const user = userEvent.setup();
    const props = callbacks();
    const { container } = render(<TutorialPage track="basic" {...props} />);
    const next = () => screen.getByRole("button", { name: /我明白了|完成教程/ });

    await user.click(screen.getByRole("button", { name: "练习圆弧" })); await user.click(next());
    await user.click(screen.getByRole("button", { name: "边界圆弧 1" })); await user.click(screen.getByRole("button", { name: "边界圆弧 2" })); await user.click(next());
    await user.click(screen.getByRole("button", { name: "添加第三条弧制造分叉" })); await user.click(next());
    await user.click(screen.getByRole("button", { name: /A · 一条连通曲线/ })); await user.click(next());
    for (const edgeId of outerEdges) {
      const edge = container.querySelector<SVGPathElement>(`[data-edge-id="${edgeId}"]`)!;
      fireEvent.pointerDown(edge, { pointerId: 1, clientX: 10, clientY: 10 }); fireEvent.pointerUp(edge, { pointerId: 1, clientX: 10, clientY: 10 });
    }
    await user.click(screen.getByRole("button", { name: "检查我的闭环" })); await user.click(next());

    expect(props.onComplete).toHaveBeenCalledOnce();
    expect(screen.getByRole("heading", { name: "基础规则已经掌握！" })).toBeVisible();
    expect(loadTutorialProgress("basic").completed).toBe(true);
  });

  it("teaches pi arc types, repairs overlaps, and deduplicates a shared arc", async () => {
    const user = userEvent.setup();
    const props = callbacks();
    render(<TutorialPage track="pi" {...props} />);
    const next = () => screen.getByRole("button", { name: /我明白了|完成教程/ });

    for (let sector = 1; sector <= 6; sector += 1) await user.click(screen.getByRole("button", { name: `点亮第 ${sector} 类圆弧` }));
    expect(screen.getByText(/六段弧拼成了一个完整圆周/)).toBeVisible(); await user.click(next());

    expect(screen.getByText(/删除重复的第 1、3 类/)).toBeVisible();
    await user.click(screen.getByRole("button", { name: "π 区域 3第 1 类圆弧" }));
    await user.click(screen.getByRole("button", { name: "π 区域 3第 3 类圆弧" }));
    await user.click(screen.getByRole("button", { name: "π 区域 3第 5 类圆弧" }));
    await user.click(screen.getByRole("button", { name: "π 区域 3第 6 类圆弧" }));
    expect(screen.getByText(/三个 π 区域合在一起/)).toBeVisible(); await user.click(next());

    await user.click(screen.getByRole("button", { name: "两个 π 区域的公共弧" }));
    expect(screen.getByText(/计入对应类别/).closest("span")).toHaveTextContent("1 次"); await user.click(next());

    expect(props.onComplete).toHaveBeenCalledOnce();
    expect(screen.getByRole("heading", { name: "你已经掌握 π 约束了！" })).toBeVisible();
    expect(loadTutorialProgress("pi").completed).toBe(true);
  });

  it("guides the combined pi puzzle through forced arcs and vertex choices", async () => {
    const user = userEvent.setup(); const props = callbacks();
    const { container } = render(<TutorialPage track="guided" {...props} />);
    const next = () => screen.getByRole("button", { name: /我明白了|完成教程/ });
    const toggle = (edgeId: string) => {
      const edge = container.querySelector<SVGPathElement>(`[data-edge-id="${edgeId}"]`)!;
      fireEvent.pointerDown(edge, { pointerId: 1, clientX: 10, clientY: 10 }); fireEvent.pointerUp(edge, { pointerId: 1, clientX: 10, clientY: 10 });
    };

    for (const edgeId of ["arc:0:0:0", "arc:0:0:1", "arc:0:0:3", "arc:0:0:5"]) toggle(edgeId);
    expect(next()).toBeEnabled(); await user.click(next());
    toggle("arc:0:1:2");
    expect(screen.getByText(/把路线引向另一个圆/)).toBeVisible();
    toggle("arc:0:0:2"); toggle("arc:0:0:4");
    expect(next()).toBeEnabled(); await user.click(next());
    await user.click(screen.getByRole("button", { name: "逐项验证我的答案" }));
    expect(screen.getByText(/全部通过/)).toBeVisible(); await user.click(next());

    expect(screen.getByRole("heading", { name: "你独立完成了 π 小题！" })).toBeVisible();
    expect(loadTutorialProgress("guided").completed).toBe(true);
  });
});
