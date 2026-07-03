import { expect, test } from "@playwright/test";

const outerEdges = ["a-lower-right", "a-bottom-left", "a-left", "a-top-left", "a-upper-right", "b-upper-left", "b-top-right", "b-right", "b-bottom-right", "b-lower-left"];

async function toggleEdge(page: import("@playwright/test").Page, edgeId: string) {
  const edge = page.locator(`[data-edge-id="${edgeId}"]`);
  await edge.dispatchEvent("pointerdown", { pointerId: 1, clientX: 10, clientY: 10 });
  await edge.dispatchEvent("pointerup", { pointerId: 1, clientX: 10, clientY: 10 });
}

test("tutorial entry starts interactively and restores the current lesson", async ({ page }) => {
  await page.goto("./");
  await page.getByRole("button", { name: /开始互动教程/ }).click();
  await expect(page.getByRole("heading", { name: "点一下，画出圆弧" })).toBeVisible();
  await page.getByRole("button", { name: "练习圆弧" }).click();
  await page.getByRole("button", { name: /我明白了/ }).click();
  await expect(page.getByRole("heading", { name: "数字告诉你经过几条弧" })).toBeVisible();
  await page.reload();
  await expect(page.getByRole("heading", { name: "数字告诉你经过几条弧" })).toBeVisible();
});

test("mobile player can finish all tutorial lessons", async ({ page }, testInfo) => {
  test.skip(testInfo.project.name !== "mobile-chromium");
  await page.goto("./#tutorial");
  const next = page.getByRole("button", { name: /我明白了|完成教程/ });

  await page.getByRole("button", { name: "练习圆弧" }).click();
  await next.click();
  await page.getByRole("button", { name: "边界圆弧 1" }).click();
  await page.getByRole("button", { name: "边界圆弧 2" }).click();
  await next.click();
  await page.getByRole("button", { name: "添加第三条弧制造分叉" }).click();
  await next.click();
  await page.getByRole("button", { name: /A · 一条连通曲线/ }).click();
  await next.click();

  await page.getByRole("button", { name: "同时邻接两个 π 单元格的共享圆弧" }).click();
  await expect(page.locator(".pi-count-explanation")).toContainText("进入统计集合 1 条");
  await next.click();
  for (let sector = 1; sector <= 6; sector += 1) await page.getByRole("button", { name: `观察第 ${sector} 类圆弧` }).click();
  await next.click();
  const directionButtons = page.locator(".pi-candidate-edges button");
  for (let index = 0; index < 6; index += 1) await directionButtons.nth(index).click();
  await directionButtons.nth(6).click();
  await expect(page.getByText(/某一类出现了两条/)).toBeVisible();
  await expect(next).toBeDisabled();
  await directionButtons.nth(6).click();
  await expect(next).toBeEnabled();
  await next.click();
  for (const edgeId of outerEdges) await toggleEdge(page, edgeId);
  await page.getByRole("button", { name: "检查我的闭环" }).click();
  await next.click();

  await expect(page.getByRole("heading", { name: "你已经准备好挑战了！" })).toBeVisible();
  await page.getByRole("button", { name: "返回选关" }).click();
  await expect(page.locator(".tutorial-callout")).toContainText("已完成");
});
