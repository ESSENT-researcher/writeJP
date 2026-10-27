// 사용: DISCORD_APP_ID=... DISCORD_BOT_TOKEN=... node register-commands.mjs
const { DISCORD_APP_ID, DISCORD_BOT_TOKEN } = process.env;
const res = await fetch(`https://discord.com/api/v10/applications/${DISCORD_APP_ID}/commands`, {
  method: "PUT",
  headers: { Authorization: `Bot ${DISCORD_BOT_TOKEN}`, "Content-Type": "application/json" },
  body: JSON.stringify([
    {
      name: "단어",
      description: "일본어 단어의 한국어 뜻을 찾아줘요",
      options: [{ type: 3, name: "단어", description: "한자, 히라가나, 가타카나 모두 가능", required: true }],
    },
  ]),
});
console.log(res.status, await res.text());
