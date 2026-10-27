import { lookup } from "./lookup.js";

const PONG = 1;
const CHANNEL_MESSAGE = 4;

const hex = (s) => Uint8Array.from(s.match(/.{2}/g).map((b) => parseInt(b, 16)));

async function verify(request, body, publicKey) {
  const sig = request.headers.get("x-signature-ed25519");
  const ts = request.headers.get("x-signature-timestamp");
  if (!sig || !ts) return false;
  try {
    const key = await crypto.subtle.importKey("raw", hex(publicKey), { name: "NODE-ED25519", namedCurve: "NODE-ED25519" }, false, ["verify"]);
    return await crypto.subtle.verify("NODE-ED25519", key, hex(sig), new TextEncoder().encode(ts + body));
  } catch {
    return false;
  }
}

export function formatResults(query, results) {
  if (!results.length) return `「${query}」에 해당하는 단어를 찾지 못했어요.`;
  const lines = results.map((r) => {
    const head = r.forms.length ? `${r.forms[0]}（${r.readings[0]}）` : r.readings[0];
    const tag = r.level ? ` \`${r.level}\`` : "";
    return `**${head}**${tag}\n> ${r.ko}`;
  });
  return `**「${query}」 검색 결과**\n\n${lines.join("\n\n")}\n\n-# JMdict (CC BY-SA 4.0) · 한국어 뜻은 직접 번역`;
}

export default {
  async fetch(request, env) {
    if (request.method !== "POST") return new Response("writeJP bot");
    const body = await request.text();
    if (!(await verify(request, body, env.DISCORD_PUBLIC_KEY))) {
      return new Response("invalid signature", { status: 401 });
    }
    const interaction = JSON.parse(body);
    if (interaction.type === 1) return Response.json({ type: PONG });

    if (interaction.type === 2 && interaction.data.name === "단어") {
      const word = interaction.data.options?.find((o) => o.name === "단어")?.value ?? "";
      const content = formatResults(word, lookup(word));
      return Response.json({ type: CHANNEL_MESSAGE, data: { content } });
    }
    return Response.json({ type: CHANNEL_MESSAGE, data: { content: "알 수 없는 명령이에요.", flags: 64 } });
  },
};
