import { createServer } from "node:http";
import { networkInterfaces } from "node:os";
import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import qrcode from "qrcode-terminal";

const here = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(here, "../dist");
const port = Number(process.argv[2] ?? process.env.PORT ?? 8080);
const prefix = "/ShuHui-PiDay/";
const mime = {
  ".css": "text/css; charset=utf-8",
  ".html": "text/html; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".png": "image/png",
  ".svg": "image/svg+xml; charset=utf-8",
  ".webmanifest": "application/manifest+json; charset=utf-8",
};

async function send(response, pathname) {
  let relative = decodeURIComponent(pathname);
  if (relative === "/") relative = prefix;
  if (relative.startsWith(prefix)) relative = relative.slice(prefix.length);
  const candidate = path.resolve(root, relative || "index.html");
  if (!candidate.startsWith(root)) {
    response.writeHead(403).end("Forbidden");
    return;
  }
  try {
    const stat = await fs.stat(candidate);
    const file = stat.isDirectory() ? path.join(candidate, "index.html") : candidate;
    const body = await fs.readFile(file);
    response.writeHead(200, {
      "Content-Type": mime[path.extname(file)] ?? "application/octet-stream",
      "Cache-Control": "no-cache",
    });
    response.end(body);
  } catch {
    const body = await fs.readFile(path.join(root, "index.html"));
    response.writeHead(200, { "Content-Type": mime[".html"], "Cache-Control": "no-cache" });
    response.end(body);
  }
}

createServer((request, response) => {
  void send(response, new URL(request.url ?? "/", "http://localhost").pathname);
}).listen(port, "0.0.0.0", () => {
  const addresses = Object.values(networkInterfaces())
    .flat()
    .filter((item) => item?.family === "IPv4" && !item.internal)
    .map((item) => `http://${item.address}:${port}${prefix}`);
  console.log("\nπDay 现场局域网镜像已启动。手机需与本机连接同一 Wi-Fi：\n");
  for (const address of addresses) {
    console.log(address);
    qrcode.generate(address, { small: true });
  }
  if (!addresses.length) console.log(`http://localhost:${port}${prefix}`);
  console.log("按 Ctrl+C 停止。局域网 HTTP 版不提供 PWA 安装或可靠离线缓存。\n");
});
