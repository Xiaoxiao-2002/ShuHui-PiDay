import { expect, test } from "@playwright/test";
import fs from "node:fs/promises";
import path from "node:path";

const source = JSON.parse(
  await fs.readFile(path.resolve(import.meta.dirname, "../../output/puzzles/easy/01.json"), "utf8"),
) as { target_solution_edges: string[] };

async function startFirstPuzzle(page: import("@playwright/test").Page) {
  await page.goto("./");
  await expect(page.getByRole("heading", { name: "πDay - 特色数回" })).toBeVisible();
  await page.getByRole("button", { name: /TSH-2026-01/ }).click();
  const preview = page.getByRole("dialog", { name: /TSH-2026-01 关卡预览/ });
  await expect(preview).toBeVisible();
  await expect(preview).toContainText("2026年7月6日");
  await expect(preview).toContainText("修订版 v1");
  await expect(preview).toContainText("尚未通关");
  await page.getByRole("button", { name: /进入关卡/ }).click();
  await page.getByRole("button", { name: "开始挑战" }).click();
  await expect(page.getByRole("application")).toBeVisible();
}

async function toggleEdge(page: import("@playwright/test").Page, edgeId: string) {
  const edge = page.locator(`[data-edge-id="${edgeId}"]`);
  await edge.dispatchEvent("pointerdown", { pointerId: 1, clientX: 10, clientY: 10 });
  await edge.dispatchEvent("pointerup", { pointerId: 1, clientX: 10, clientY: 10 });
}

test("automatically saves and restores an in-progress answer", async ({ page }) => {
  await startFirstPuzzle(page);
  await toggleEdge(page, source.target_solution_edges[0]);
  await expect(page.locator(".selected-edges path")).toHaveCount(1);
  await page.reload();
  await expect(page.locator(".selected-edges path")).toHaveCount(1);
  await expect(page.getByLabel("当前用时")).not.toHaveText("--:--");
});

test("accepts the official answer and generates a completion receipt", async ({ page }) => {
  await startFirstPuzzle(page);
  for (const edgeId of source.target_solution_edges) await toggleEdge(page, edgeId);
  await page.getByRole("button", { name: "提交验证" }).click();
  const dialog = page.getByRole("dialog", { name: "完成凭证" });
  await expect(dialog).toBeVisible();
  await expect(dialog).toContainText("TSH-2026-01");
  await expect(dialog).toContainText("初级 Beginner");
  await expect(dialog).toContainText("本地验证通过");
});

test("opens every cached level while offline after the first visit", async ({ page, context }, testInfo) => {
  test.skip(testInfo.project.name !== "desktop-chromium");
  await page.goto("./");
  await page.evaluate(async () => navigator.serviceWorker.ready);
  await page.reload();
  await expect(page.getByRole("heading", { name: "πDay - 特色数回" })).toBeVisible();
  await context.setOffline(true);
  await page.reload();
  await expect(page.getByRole("button", { name: /TSH-2026-20/ })).toBeVisible();
  await page.getByRole("button", { name: /TSH-2026-20/ }).click();
  await page.getByRole("button", { name: /进入关卡/ }).click();
  await expect(page.getByRole("button", { name: "开始挑战" })).toBeVisible();
});

test("supports touch pinch zoom on an expert board", async ({ page, context }, testInfo) => {
  test.skip(testInfo.project.name !== "mobile-chromium");
  await page.goto("./");
  await page.getByRole("button", { name: /TSH-2026-20/ }).click();
  await page.getByRole("button", { name: /进入关卡/ }).click();
  await page.getByRole("button", { name: "开始挑战" }).click();
  const board = page.getByRole("application");
  const before = await board.getAttribute("viewBox");
  const box = (await board.boundingBox())!;
  const session = await context.newCDPSession(page);
  const y = box.y + box.height / 2;
  const left = box.x + box.width * 0.35;
  const right = box.x + box.width * 0.65;
  await session.send("Input.dispatchTouchEvent", {
    type: "touchStart",
    touchPoints: [{ x: left, y }, { x: right, y }],
  });
  await session.send("Input.dispatchTouchEvent", {
    type: "touchMove",
    touchPoints: [{ x: left - 30, y }, { x: right + 30, y }],
  });
  await session.send("Input.dispatchTouchEvent", { type: "touchEnd", touchPoints: [] });
  await expect.poll(() => board.getAttribute("viewBox")).not.toBe(before);
});
