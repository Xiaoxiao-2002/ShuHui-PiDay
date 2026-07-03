import { fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { TutorialPage } from "../src/components/TutorialPage";
import { loadTutorialProgress, saveTutorialProgress, tutorialPuzzle } from "../src/tutorial";
import { validateSolutionEdges } from "../src/validator";

const outerEdges = ["a-lower-right", "a-bottom-left", "a-left", "a-top-left", "a-upper-right", "b-upper-left", "b-top-right", "b-right", "b-bottom-right", "b-lower-left"];

describe("tutorial data", () => {
  it("persists progress and completion locally", () => {
    expect(loadTutorialProgress()).toMatchObject({ step: 0, completed: false });
    saveTutorialProgress(3);
    expect(loadTutorialProgress()).toMatchObject({ step: 3, completed: false });
    saveTutorialProgress(5, true);
    expect(loadTutorialProgress()).toMatchObject({ step: 5, completed: true });
  });

  it("has a valid guided-practice solution", () => {
    expect(validateSolutionEdges(tutorialPuzzle, outerEdges).valid).toBe(true);
    expect(validateSolutionEdges(tutorialPuzzle, [...outerEdges, "shared"]).valid).toBe(false);
  });
});

describe("TutorialPage", () => {
  it("can be completed through all six interactive lessons", async () => {
    const user = userEvent.setup();
    const onComplete = vi.fn();
    const { container } = render(<TutorialPage onBack={vi.fn()} onComplete={onComplete} />);
    const next = () => screen.getByRole("button", { name: /我明白了|完成教程/ });

    await user.click(screen.getByRole("button", { name: "练习圆弧" }));
    expect(next()).toBeEnabled();
    await user.click(next());

    await user.click(screen.getByRole("button", { name: "边界圆弧 1" }));
    await user.click(screen.getByRole("button", { name: "边界圆弧 2" }));
    expect(next()).toBeEnabled();
    await user.click(next());

    await user.click(screen.getByRole("button", { name: "添加第三条弧制造分叉" }));
    expect(next()).toBeEnabled();
    await user.click(next());

    await user.click(screen.getByRole("button", { name: /A · 一条连通曲线/ }));
    expect(next()).toBeEnabled();
    await user.click(next());

    const directionButtons = container.querySelectorAll<HTMLButtonElement>(".direction-edge-buttons button");
    for (const button of Array.from(directionButtons).slice(0, 6)) await user.click(button);
    expect(next()).toBeEnabled();
    await user.click(next());

    for (const edgeId of outerEdges) {
      const edge = container.querySelector<SVGPathElement>(`[data-edge-id="${edgeId}"]`)!;
      fireEvent.pointerDown(edge, { pointerId: 1, clientX: 10, clientY: 10 });
      fireEvent.pointerUp(edge, { pointerId: 1, clientX: 10, clientY: 10 });
    }
    await user.click(screen.getByRole("button", { name: "检查我的闭环" }));
    expect(next()).toBeEnabled();
    await user.click(next());

    expect(onComplete).toHaveBeenCalledOnce();
    expect(screen.getByRole("heading", { name: "你已经准备好挑战了！" })).toBeVisible();
    expect(loadTutorialProgress().completed).toBe(true);
  });
});
