/* LiveTalking viewer with auto-fallback + SDP normalization
 * - 先用 Content-Type: application/sdp 送出 offer
 * - 若失敗，自動換 JSON 變體：{sdp}, {offer}, {type:'offer',sdp}, {sdp64:btoa(sdp)}
 * - 回應支援純 SDP 或 JSON(sdp/answer/data.sdp)
 * - 對回應 SDP 進行正規化（CRLF 換行、去尾空白、擷取第一個 v= 區塊）
 * - 需要的元素：<video id="lt-remote-video">、<div id="lt-status">
 * - 走同源 /ltapi/offer（交由 proxy.py 代理到 http://localhost:8010/offer）
 */
(() => {
  'use strict';

  const PLAY_URL = '/ltapi/offer';        // 由 proxy.py 代理到 8010
  const WAIT_FOR_ICE_COMPLETE = true;     // 某些伺服器需要 non-trickle ICE

  // 可在 HTML 內預先定義：window.LT_CONFIG = { voice:'xiaomei', model:'v1', roomId:'abc' }
  const EXTRA = (window.LT_CONFIG && typeof window.LT_CONFIG === 'object') ? window.LT_CONFIG : {};

  // 虛擬人同步配置
  const SYNC_CONFIG = {
    syncWithDashboard: true,    // 是否與 dashboard 同步
    sharedSessionId: null,      // 共享的 session ID
    syncInterval: 5000          // 同步間隔 (毫秒)
  };

  // ---- DOM 與狀態 ----
  const $ = (id) => document.getElementById(id);
  const elVideo = $('lt-remote-video');
  const elStatus = $('lt-status');
  const setStatus = (t) => { if (elStatus) elStatus.textContent = t; };

  // === 共用遠端 MediaStream，video & audio 都吃它 ===
  let audioEl = document.getElementById('lt-remote-audio');
  if (!audioEl) {
    audioEl = document.createElement('audio');
    audioEl.id = 'lt-remote-audio';
    audioEl.autoplay = true;
    audioEl.muted = false;
    audioEl.volume = 1.0;
    audioEl.style.display = 'none';
    document.body.appendChild(audioEl);
  }
  const remoteStream = new MediaStream();
  if (elVideo) elVideo.srcObject = remoteStream;
  audioEl.srcObject = remoteStream;

  // 第一次點擊解鎖自動播放
  document.addEventListener('click', () => {
    audioEl.play().catch(() => { });
    elVideo?.play?.().catch(() => { });
  }, { once: true });


  let pc = null, stopped = false;

  // ---- 工具：等待 ICE 完成（避免對端不支援 trickle）----
  function waitIceCompleteOnce(pc) {
    if (!WAIT_FOR_ICE_COMPLETE) return Promise.resolve();
    return new Promise((resolve) => {
      if (pc.iceGatheringState === 'complete') return resolve();
      const onchg = () => {
        console.log('[LT] iceGatheringState:', pc.iceGatheringState);
        if (pc.iceGatheringState === 'complete') {
          pc.removeEventListener('icegatheringstatechange', onchg);
          resolve();
        }
      };
      pc.addEventListener('icegatheringstatechange', onchg);
    });
  }

  // ---- 工具：SDP 正規化（修正 a=setup:active Invalid SDP line 等問題）----
  function normalizeSdp(raw) {
    if (!raw) return '';
    // 去掉 BOM
    if (raw.charCodeAt(0) === 0xFEFF) raw = raw.slice(1);
    // 全部先變成 \n
    raw = raw.replace(/\r\n/g, '\n').replace(/\r/g, '\n');
    // 去掉每行尾端多餘空白
    const lines = raw.split('\n').map(l => l.replace(/\s+$/, ''));
    // 再轉回 \r\n，確保結尾有 \r\n
    let sdp = lines.join('\r\n');
    if (!sdp.endsWith('\r\n')) sdp += '\r\n';
    return sdp;
  }

  // ---- 工具：若回應前面有其他文字，擷取第一段真正的 SDP ----
  function extractFirstSdpBlock(text) {
    if (!text) return '';
    const trimmed = text.trim();
    if (trimmed.startsWith('v=')) return trimmed;
    const i = text.indexOf('\nv=');
    if (i > -1) return text.slice(i + 1).trim();
    return trimmed; // 若找不到，照原文（後面還會再檢查）
  }

  // ---- 發送 HTTP ----
  async function postRaw(headers, body) {
    const res = await fetch(PLAY_URL, { method: 'POST', headers, body });
    const ct = (res.headers.get('content-type') || '').toLowerCase();
    const payload = ct.includes('application/json') ? await res.json().catch(() => null) : await res.text().catch(() => '');
    return { ok: res.ok, status: res.status, ctype: ct, data: payload };
  }

  // ---- 方案 1：純 SDP ----
  async function trySDP(offerSdp) {
    console.log('[LT] Try: application/sdp');
    return postRaw(
      {
        'Content-Type': 'application/sdp',
        'Accept': 'application/json, application/sdp, text/plain; q=0.9, */*;q=0.8',
      },
      offerSdp
    );
  }

  // ---- 方案 2：JSON 變體 ----
  async function tryJSON(offerSdp) {
    const variants = [
      { ...EXTRA, sdp: offerSdp, __hint: 'json.sdp' },
      { ...EXTRA, offer: offerSdp, __hint: 'json.offer' },
      { ...EXTRA, type: 'offer', sdp: offerSdp, __hint: 'json.type+sdp' },
      { ...EXTRA, sdp64: btoa(offerSdp), __hint: 'json.sdp64' },
    ];
    for (const p of variants) {
      const hint = p.__hint; delete p.__hint;
      console.log('[LT] Try: application/json ->', hint, p);
      const r = await postRaw(
        { 'Content-Type': 'application/json', 'Accept': 'application/json,text/plain,application/sdp,*/*;q=0.8' },
        JSON.stringify(p)
      );
      if (r.ok) return r;
      console.warn('[LT] JSON variant failed:', hint, r.status, typeof r.data === 'string' ? r.data.slice(0, 200) : r.data);
    }
    return { ok: false, status: 0, ctype: '', data: 'all json variants failed' };
  }

  // ---- 從回應取出 Answer SDP（並正規化）----
  function getNormalizedAnswerSdp(resp) {
    let text = '';
    if (resp.ctype.includes('application/json')) {
      const j = resp.data || {};
      text = j?.sdp || j?.answer || (j?.data && j.data.sdp) || '';
    } else {
      text = String(resp.data ?? '');
    }
    let sdp = extractFirstSdpBlock(text);
    sdp = normalizeSdp(sdp);
    if (!sdp.startsWith('v=')) return ''; // 最終仍無效
    return sdp;
  }

  // ---- 啟動 ----
  // 讀取 sessionid（只做一次）
  // 會嘗試多個路徑抓 sessionid，成功後存到 window.LT_CTX.sessionid
  async function loadSessionId() {
    // 如果啟用同步模式，先嘗試從 localStorage 獲取共享 session
    if (SYNC_CONFIG.syncWithDashboard) {
      const sharedSessionId = localStorage.getItem('lt_shared_session_id');
      if (sharedSessionId) {
        console.log('[LT] 使用共享 session ID:', sharedSessionId);
        SYNC_CONFIG.sharedSessionId = sharedSessionId;
        window.LT_CTX = window.LT_CTX || {};
        window.LT_CTX.sessionid = sharedSessionId;
        return sharedSessionId;
      }
    }

    const paths = [
      '/ltapi/index.json',  // 走 proxy 到 8010（理想）
      '/index.json'         // 直接抓（保底）
    ];
    for (const p of paths) {
      try {
        console.log('[LT] try fetch session from', p);
        const r = await fetch(p, { method: 'GET' });
        if (!r.ok) { console.warn('[LT] session fetch', p, 'status', r.status); continue; }
        const j = await r.json().catch(() => ({}));
        if (j && j.sessionid) {
          window.LT_CTX = window.LT_CTX || {};
          window.LT_CTX.sessionid = j.sessionid;
          console.log('[LT] got sessionid =', j.sessionid, 'via', p);

          // 如果啟用同步，保存到 localStorage
          if (SYNC_CONFIG.syncWithDashboard) {
            localStorage.setItem('lt_shared_session_id', j.sessionid);
            SYNC_CONFIG.sharedSessionId = j.sessionid;
            console.log('[LT] 已保存共享 session ID 供同步使用');
          }

          return j.sessionid;
        } else {
          console.warn('[LT] no sessionid in', p, j);
        }
      } catch (e) {
        console.warn('[LT] session fetch error', p, e);
      }
    }
    console.warn('[LT] sessionid not found (all paths tried).');
    return null;
  }


  async function start() {
    try {
      stopped = false;
      setStatus('連線中…（自動偵測協定）');
      await loadSessionId();

      pc = new RTCPeerConnection({ iceServers: [{ urls: ['stun:stun.l.google.com:19302'] }] });

      // 要求接收視訊 + 音訊
      pc.addTransceiver('video', { direction: 'recvonly' });
      pc.addTransceiver('audio', { direction: 'recvonly' });

      // 收到遠端 track 加到 remoteStream
      pc.addEventListener('track', (ev) => {
        console.log('[LT] ontrack:', ev.track.kind);
        remoteStream.addTrack(ev.track);
        if (ev.track.kind === 'audio') {
          // 收到音訊就嘗試播放（有時需要再次觸發）
          audioEl.play().catch(() => { });
        }
      });

      // 方便你在 Console 檢查
      window.__LT_PC = pc;


      // 建立 offer
      const offer = await pc.createOffer({ offerToReceiveAudio: true, offerToReceiveVideo: true });
      await pc.setLocalDescription(offer);
      await waitIceCompleteOnce(pc);

      // 先試純 SDP
      let resp = await trySDP(pc.localDescription.sdp);
      if (!resp.ok) {
        console.warn('[LT] SDP failed:', resp.status, typeof resp.data === 'string' ? resp.data.slice(0, 200) : resp.data);
        // 再試 JSON 變體
        resp = await tryJSON(pc.localDescription.sdp);
      }

      if (!resp.ok) {
        throw new Error(`信令回應碼 ${resp.status} | ${typeof resp.data === 'string' ? resp.data.slice(0, 200) : JSON.stringify(resp.data)}`);
      }
      console.log('[LT] Response status:', resp.status, 'ctype:', resp.ctype);

      const answerSdp = getNormalizedAnswerSdp(resp);
      if (!answerSdp) throw new Error('回應缺少有效 SDP（未找到以 v= 開頭的內容或格式不正確）');

      console.log('[LT] Answer (first 5 lines):\n' + answerSdp.split('\r\n').slice(0, 5).join('\n'));
      await pc.setRemoteDescription({ type: 'answer', sdp: answerSdp });

      setStatus('已連線 ✓');
      elVideo.addEventListener('loadedmetadata', () => elVideo.play().catch(() => { }), { once: true });

    } catch (e) {
      console.error('[LT] start() error:', e);
      // 友善的錯誤處理 - 不阻擋對話功能
      if (e?.message?.includes('502') || e?.message?.includes('503') || e?.message?.includes('Upstream error') || e?.message?.includes('unavailable')) {
        setStatus('⚠️ 虛擬人服務未啟動');
        console.warn('[LT] LiveTalking 服務未啟動，但對話功能仍可正常使用');
        // 切換到降級模式
        enableFallbackMode();
      } else {
        setStatus('連線失敗：' + (e?.message || e));
      }
    }
  }

  // ---- 降級模式 ----
  function enableFallbackMode() {
    const ltWrapper = document.getElementById('lt-wrapper');
    const fallbackEl = document.getElementById('avatar-fallback');

    if (ltWrapper && fallbackEl) {
      ltWrapper.style.display = 'none';
      fallbackEl.style.display = 'flex';
      console.log('[LT] 已切換到降級模式');

      // 綁定重試按鈕
      const retryBtn = document.getElementById('retry-avatar');
      if (retryBtn) {
        retryBtn.addEventListener('click', () => {
          console.log('[LT] 用戶點擊重試連接');
          retryConnection();
        });
      }
    }

    // 調整布局 - 讓對話區域更大
    const chatSection = document.getElementById('chat-section');
    const avatarSection = document.getElementById('avatar-section');
    if (chatSection && avatarSection) {
      // 縮小虛擬人區域，擴大對話區域
      avatarSection.style.flex = '0 0 300px';
      chatSection.style.flex = '1';
    }

    // 廣播事件，讓其他組件知道虛擬人服務不可用
    window.dispatchEvent(new CustomEvent('avatarServiceUnavailable', {
      detail: { message: '虛擬人服務暫時無法使用，對話功能仍可正常使用' }
    }));
  }

  function retryConnection() {
    const ltWrapper = document.getElementById('lt-wrapper');
    const fallbackEl = document.getElementById('avatar-fallback');
    const retryBtn = document.getElementById('retry-avatar');

    // 顯示重試狀態
    if (retryBtn) {
      retryBtn.textContent = '重新連接中...';
      retryBtn.disabled = true;
    }

    // 暫時切回正常顯示
    if (ltWrapper && fallbackEl) {
      ltWrapper.style.display = 'flex';
      fallbackEl.style.display = 'none';
    }

    setStatus('重新連接中...');

    // 重新嘗試連接
    setTimeout(() => {
      start().finally(() => {
        // 重置重試按鈕
        if (retryBtn) {
          retryBtn.textContent = '重試連接';
          retryBtn.disabled = false;
        }
      });
    }, 1000);
  }

  // ---- 停止 ----
  function stop() {
    stopped = true;
    try { pc?.getSenders().forEach(s => { try { s.track && s.track.stop(); } catch { } }); } catch { }
    try { pc?.close(); } catch { }
    pc = null;
    if (elVideo) elVideo.srcObject = null;
    setStatus('已中斷');
  }

  // 同步狀態監控
  function startSyncMonitoring() {
    if (!SYNC_CONFIG.syncWithDashboard) return;

    setInterval(async () => {
      try {
        // 檢查是否有新的共享 session
        const currentSharedId = localStorage.getItem('lt_shared_session_id');
        if (currentSharedId && currentSharedId !== SYNC_CONFIG.sharedSessionId) {
          console.log('[LT] 檢測到新的共享 session，重新連接:', currentSharedId);
          SYNC_CONFIG.sharedSessionId = currentSharedId;
          // 重新啟動連接
          stop();
          setTimeout(start, 1000);
        }
      } catch (e) {
        console.warn('[LT] 同步監控錯誤:', e);
      }
    }, SYNC_CONFIG.syncInterval);
  }

  // 導出同步控制函數
  function setSyncMode(enabled) {
    SYNC_CONFIG.syncWithDashboard = enabled;
    console.log('[LT] 同步模式:', enabled ? '啟用' : '停用');
    if (enabled) {
      startSyncMonitoring();
    }
  }

  // 強制同步到指定 session
  function syncToSession(sessionId) {
    if (sessionId) {
      localStorage.setItem('lt_shared_session_id', sessionId);
      SYNC_CONFIG.sharedSessionId = sessionId;
      console.log('[LT] 強制同步到 session:', sessionId);
      stop();
      setTimeout(start, 1000);
    }
  }

  document.addEventListener('DOMContentLoaded', () => {
    start();
    if (SYNC_CONFIG.syncWithDashboard) {
      startSyncMonitoring();
    }
  });

  window.LT = {
    start,
    stop,
    setSyncMode,
    syncToSession,
    getSyncConfig: () => SYNC_CONFIG
  };
})();
