import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import QRCode from "qrcode";

const here = path.dirname(fileURLToPath(import.meta.url));
const publicDir = path.resolve(here, "../public");
const target = process.argv[2] ?? "https://xiaoxiao-2002.github.io/ShuHui-PiDay/";

await fs.mkdir(publicDir, { recursive: true });
await Promise.all([
  QRCode.toFile(path.join(publicDir, "qr-entry.svg"), target, {
    type: "svg",
    errorCorrectionLevel: "H",
    margin: 2,
    color: { dark: "#132b49", light: "#ffffff" },
  }),
  QRCode.toFile(path.join(publicDir, "qr-entry.png"), target, {
    width: 1200,
    errorCorrectionLevel: "H",
    margin: 4,
    color: { dark: "#132b49", light: "#ffffff" },
  }),
]);
console.log(`QR code generated for ${target}`);
