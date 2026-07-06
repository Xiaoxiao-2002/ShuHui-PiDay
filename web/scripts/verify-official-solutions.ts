import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import type { PlayablePuzzleV1, PuzzleIndexV1 } from "../src/types";
import { validateSolutionEdges } from "../src/validator";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
const publicDir = path.join(root, "web", "public", "puzzles");
const forbidden = new Set(["target_solution_edges", "solution_edges", "analysis"]);

function assertSafe(value: unknown, location = "root"): void {
  if (Array.isArray(value)) {
    value.forEach((entry, index) => assertSafe(entry, `${location}[${index}]`));
    return;
  }
  if (!value || typeof value !== "object") return;
  for (const [key, nested] of Object.entries(value)) {
    if (forbidden.has(key)) throw new Error(`发布题库包含禁止字段 ${location}.${key}`);
    assertSafe(nested, `${location}.${key}`);
  }
}

const index = JSON.parse(await fs.readFile(path.join(publicDir, "index.json"), "utf8")) as PuzzleIndexV1;
const catalog = JSON.parse(await fs.readFile(path.join(root, "web", "puzzle-catalog.json"), "utf8")) as { entries: Array<{ id: string; source: string }> };
const sourceById = new Map(await Promise.all(catalog.entries.map(async (entry) => [
  entry.id,
  JSON.parse(await fs.readFile(path.join(root, entry.source), "utf8")) as { target_solution_edges: string[] },
] as const)));

for (const item of index.puzzles) {
  const raw = JSON.parse(await fs.readFile(path.join(publicDir, item.file), "utf8")) as PlayablePuzzleV1;
  assertSafe(raw, item.id);
  const source = sourceById.get(item.id);
  if (!source) throw new Error(`${item.id} 找不到题库目录中的源题`);
  const result = validateSolutionEdges(raw, source.target_solution_edges);
  if (!result.valid) throw new Error(`${item.id} 的正式答案未通过 TypeScript 验证：${result.code}`);
  for (let i = 0; i < source.target_solution_edges.length; i += 1) {
    const shortened = source.target_solution_edges.filter((_, answerIndex) => answerIndex !== i);
    if (validateSolutionEdges(raw, shortened).valid) throw new Error(`${item.id} 删除答案边后仍被接受`);
  }
}

console.log(`TypeScript 已复验 ${index.puzzles.length} 道正式答案；发布题库未发现答案字段。`);
