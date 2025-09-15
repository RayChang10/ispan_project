(function () {
	function $(selector, root) { return (root || document).querySelector(selector); }
	function $all(selector, root) { return Array.from((root || document).querySelectorAll(selector)); }

	function saveDraft(key, data) { localStorage.setItem(key, JSON.stringify(data)); }
	function loadDraft(key) { try { return JSON.parse(localStorage.getItem(key) || 'null'); } catch (e) { return null; } }
	function clearDraft(key) { localStorage.removeItem(key); }

	function navigate(path) { window.location.href = path; }

	function cnCharCount(str) { if (!str) return 0; return Array.from(str).length; }

	// 簡易語音輸入（Web Speech API）
	function attachSpeechToInput(button, input) {
		if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
			button.disabled = true; button.title = '瀏覽器不支援語音輸入'; return;
		}
		var SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition;
		var rec = new SpeechRec(); rec.lang = 'zh-TW'; rec.interimResults = false; var listening = false;
		button.addEventListener('click', function () { if (listening) { rec.stop(); return; } listening = true; button.classList.add('warning'); rec.start(); });
		rec.onend = function () { listening = false; button.classList.remove('warning'); };
		rec.onresult = function (e) { var text = e.results[0][0].transcript || ''; input.value = (input.value ? input.value + ' ' : '') + text; input.dispatchEvent(new Event('input')); };
	}

	// Toast（簡化）
	function showToast(message, type) {
		var wrap = $('#toast-wrap'); if (!wrap) { wrap = document.createElement('div'); wrap.id = 'toast-wrap'; wrap.style.position = 'fixed'; wrap.style.right = '16px'; wrap.style.bottom = '16px'; wrap.style.zIndex = '9999'; document.body.appendChild(wrap); }
		var t = document.createElement('div'); t.textContent = message; t.style.marginTop = '8px'; t.style.padding = '8px 12px'; t.style.borderRadius = '8px'; t.style.border = '1px solid #1f2937'; t.style.background = type === 'error' ? '#3f1d1d' : '#0b1220'; t.style.color = '#e5e7eb'; wrap.appendChild(t); setTimeout(() => t.remove(), 3000);
	}

	// Auth 狀態（示意）
	const Auth = {
		get() { try { return JSON.parse(localStorage.getItem('jm_auth') || 'null'); } catch (e) { return null; } },
		set(v) { localStorage.setItem('jm_auth', JSON.stringify(v || {})); },
		clear() { localStorage.removeItem('jm_auth'); },
		isAuthed() { const a = this.get(); return !!(a && a.accessToken); }
	};

	// 產生相對路徑（根目錄: 專案根）
	function rel(path) {
		var p = location.pathname.replace(/\\/g, '/');
		// 檢查是否在子目錄中
		var inSub = /\/app\//.test(p) || /\/me\//.test(p) || /\/auth\//.test(p);
		// 如果在子目錄中，需要回到上一層
		return inSub ? ('../' + path) : ('./' + path);
	}

	function requireAuth(redirectPath) {
		if (!Auth.isAuthed()) {
			var to = encodeURIComponent(redirectPath || location.pathname + location.search);
			window.location.href = rel('auth/login.html') + '?redirect=' + to;
			return false;
		}
		return true;
	}

	function renderNavbar(container) {
		if (!container) return;
		var bar = document.createElement('div'); bar.className = 'header';
		var left = document.createElement('div'); left.innerHTML = '<span class="kicker">JobMate360</span>'; left.style.cursor = 'pointer'; left.addEventListener('click', () => navigate(rel('index.html')));
		var right = document.createElement('div');
		if (Auth.isAuthed()) {
			var user = (Auth.get() || {}).user || { name: '會員' };
			var me = document.createElement('button'); me.className = 'button secondary'; me.textContent = user.name || '會員中心'; me.addEventListener('click', () => navigate(rel('me/index.html')));
			var bell = document.createElement('button'); bell.className = 'button secondary'; bell.textContent = '通知';
			var logout = document.createElement('button'); logout.className = 'button danger'; logout.textContent = '登出'; logout.addEventListener('click', () => { Auth.clear(); localStorage.removeItem('jobmate_user_id'); navigate(rel('index.html')); });
			right.appendChild(me); right.appendChild(bell); right.appendChild(logout);
		} else {
			var login = document.createElement('button'); login.className = 'button primary'; login.textContent = '登入'; login.addEventListener('click', () => navigate(rel('auth/login.html')));
			var reg = document.createElement('button'); reg.className = 'button secondary'; reg.textContent = '註冊'; reg.addEventListener('click', () => navigate(rel('auth/register.html')));
			right.appendChild(login); right.appendChild(reg);
		}
		bar.appendChild(left); bar.appendChild(right);
		container.prepend(bar);
	}

	window.JobMate = {
		$,
		$all,
		saveDraft,
		loadDraft,
		clearDraft,
		navigate,
		cnCharCount,
		attachSpeechToInput,
		showToast,
		Auth,
		rel,
		requireAuth,
		renderNavbar
	};
})();


