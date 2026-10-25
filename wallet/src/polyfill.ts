// Полифиллы для @ton/* в браузере: TON-либы используют Node Buffer/process.
import { Buffer } from "buffer";

if (typeof window !== "undefined") {
  const w = window as unknown as { Buffer?: typeof Buffer; process?: unknown; global?: unknown };
  if (!w.Buffer) w.Buffer = Buffer;
  if (!w.process) w.process = { env: {}, browser: true } as unknown;
  if (!w.global) w.global = w;
}

export {};
