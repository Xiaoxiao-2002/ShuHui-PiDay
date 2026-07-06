import { expect, test } from "@playwright/test";

test("tutorial center opens the basic track and restores its lesson", async ({ page }) => {
  await page.goto("./");
  await page.getByRole("button", { name: /打开教程中心/ }).click();
  await expect(page.getByRole("heading", { name: "选择一个互动教程" })).toBeVisible();
  await page.locator(".basic-track").getByRole("button", { name: "开始教程 →" }).click();
  await page.getByRole("button", { name: "练习圆弧" }).click();
  await page.getByRole("button", { name: /我明白了/ }).click();
  await expect(page.getByRole("heading", { name: "数字告诉你经过几条弧" })).toBeVisible();
  await page.reload();
  await expect(page.getByRole("heading", { name: "数字告诉你经过几条弧" })).toBeVisible();
});

test("mobile player can complete the isolated pi tutorial", async ({ page }, testInfo) => {
  test.skip(testInfo.project.name !== "mobile-chromium");
  await page.goto("./#tutorial/pi");
  const next = page.getByRole("button", { name: /我明白了|完成教程/ });

  for (let sector = 1; sector <= 6; sector += 1) await page.getByRole("button", { name: `点亮第 ${sector} 类圆弧` }).click();
  await expect(page.getByText(/六段弧拼成了一个完整圆周/)).toBeVisible();
  await next.click();

  await expect(page.getByText(/本步只检查 π/)).toBeVisible();
  await expect(page.getByText(/删除重复的第 1、3 类/)).toBeVisible();
  await page.getByRole("button", { name: "π 区域 3第 1 类圆弧" }).click();
  await page.getByRole("button", { name: "π 区域 3第 3 类圆弧" }).click();
  await page.getByRole("button", { name: "π 区域 3第 5 类圆弧" }).click();
  await page.getByRole("button", { name: "π 区域 3第 6 类圆弧" }).click();
  await expect(page.getByText(/三个 π 区域合在一起/)).toBeVisible();
  await next.click();

  await page.getByRole("button", { name: "两个 π 区域的公共弧" }).click();
  await expect(page.locator(".pi-count-explanation")).toContainText("计入对应类别 1 次");
  await next.click();
  await expect(page.getByRole("heading", { name: "你已经掌握 π 约束了！" })).toBeVisible();
  await page.getByRole("button", { name: "返回教程中心" }).click();
  await expect(page.locator(".pi-track")).toContainText("已完成");
});

test("mobile player can solve the guided pi puzzle step by step", async ({ page }, testInfo) => {
  test.skip(testInfo.project.name !== "mobile-chromium");
  await page.goto("./#tutorial/guided");
  const next = page.getByRole("button", { name: /我明白了|完成教程/ });
  const toggle = async (edgeId: string) => {
    const edge = page.locator(`[data-edge-id="${edgeId}"]`);
    await edge.dispatchEvent("pointerdown", { pointerId: 1, clientX: 10, clientY: 10 });
    await edge.dispatchEvent("pointerup", { pointerId: 1, clientX: 10, clientY: 10 });
  };
  for (const edgeId of ["arc:0:0:0", "arc:0:0:1", "arc:0:0:3", "arc:0:0:5"]) await toggle(edgeId);
  await next.click();
  await toggle("arc:0:1:2");
  await expect(page.getByText(/把路线引向另一个圆/)).toBeVisible();
  await toggle("arc:0:0:2"); await toggle("arc:0:0:4");
  await next.click();
  await page.getByRole("button", { name: "逐项验证我的答案" }).click();
  await expect(page.getByText(/全部通过/)).toBeVisible();
  await next.click();
  await expect(page.getByRole("heading", { name: "你独立完成了 π 小题！" })).toBeVisible();
});
