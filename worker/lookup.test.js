import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

// wrangler 없이도 돌리도록 dict.json을 직접 읽어 같은 로직을 검증한다.
const dict = JSON.parse(readFileSync(new URL("./dict.json", import.meta.url)));

test("dict 형식", () => {
  assert.ok(dict.length > 30000);
  for (const [forms, readings, ko] of dict.slice(0, 500)) {
    assert.ok(Array.isArray(forms) && Array.isArray(readings) && ko);
  }
});

test("대표 단어 존재", () => {
  const has = (w) => dict.some((e) => e[0].includes(w));
  assert.ok(has("政府"));
  assert.ok(has("経済"));
});
