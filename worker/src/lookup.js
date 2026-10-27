import dict from "../dict.json";

// 가타카나를 히라가나로 바꿔 읽기 검색이 표기 차이에 흔들리지 않게 한다.
export function normalize(text) {
  return text
    .trim()
    .replace(/[ァ-ヶ]/g, (c) => String.fromCharCode(c.charCodeAt(0) - 0x60));
}

const index = new Map();
const add = (key, i) => {
  const k = normalize(key);
  if (!k) return;
  if (!index.has(k)) index.set(k, []);
  index.get(k).push(i);
};
dict.forEach((entry, i) => {
  entry[0].forEach((f) => add(f, i));
  entry[1].forEach((r) => add(r, i));
});

const LEVEL_RANK = { N1: 1, N2: 2, N3: 3, N4: 4, N5: 5 };

// JLPT 단어를 앞에 둔다(이미 학습 대상이라 더 쓸모 있음).
const byRelevance = (a, b) => {
  const ra = LEVEL_RANK[dict[a][3]] ?? 9;
  const rb = LEVEL_RANK[dict[b][3]] ?? 9;
  return ra - rb || a - b;
};

export function lookup(query, limit = 5) {
  const q = normalize(query);
  if (!q) return [];
  let hits = [...new Set(index.get(q) ?? [])];
  if (!hits.length) {
    // 정확히 일치하는 항목이 없으면 앞부분이 같은 단어를 찾는다.
    const found = new Set();
    for (const [key, ids] of index) {
      if (key.startsWith(q)) ids.forEach((i) => found.add(i));
      if (found.size > 200) break;
    }
    hits = [...found];
  }
  return hits.sort(byRelevance).slice(0, limit).map((i) => {
    const [forms, readings, ko, level] = dict[i];
    return { forms, readings, ko, level };
  });
}
