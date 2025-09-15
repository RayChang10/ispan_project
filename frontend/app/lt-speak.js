// frontend/app/lt-speak.js  （最簡固定版：只打 /human，用 POST JSON）
(function () {
  window.LT = window.LT || {};

  // 固定打 /human，POST JSON
  async function postHuman(text, extra = {}) {
    const body = {
      text,
      type: 'echo',        // 依你的後端預期；若不需要可刪
      interrupt: true,     // 依你的後端預期；若不需要可刪
      ...extra             // 需要再帶的欄位可從這裡擴充（例如 sessionid）
    };
    const r = await fetch('/ltapi/human', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    if (!r.ok) {
      const t = await r.text().catch(() => '');
      throw new Error(`/human failed ${r.status}: ${t}`);
    }
    return true;
  }

  // 對外介面：LT.speak(text, opts?)
  window.LT.speak = async function (text, opts = {}) {
    if (!text || !text.trim()) return false;
    try {
      await postHuman(text, opts);
      return true;
    } catch (err) {
      console.warn('[LT.speak] error:', err);
      return false;
    }
  };
})();
