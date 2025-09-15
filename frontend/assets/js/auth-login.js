(function () {
	const { $, renderNavbar, showToast, Auth, navigate, rel } = window.JobMate;

	function validate(email, password) {
		const reUpper = /[A-Z]/, reLower = /[a-z]/, reNum = /[0-9]/;
		if (!email || email.length < 8 || email.length > 64) return '帳號長度需 8–64 字';
		if (!password || password.length < 8 || password.length > 64 || !reUpper.test(password) || !reLower.test(password) || !reNum.test(password)) return '密碼需 8–64 字且含大小寫與數字';
		return '';
	}

	document.addEventListener('DOMContentLoaded', function () {
		renderNavbar($('#root'));
		const params = new URLSearchParams(location.search);
		// 強制設定跳轉到履歷選擇頁面
		let redirect = 'app/resume-choice.html';
		console.log('登入後將跳轉到:', redirect);
		$('#loginBtn').addEventListener('click', async () => {
			const email = $('#email').value.trim();
			const password = $('#password').value;
			const err = validate(email, password);
			if (err) { showToast(err, 'error'); return; }
			try {
				const res = await fetch('/api/auth/login', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ email, password }) });
				const data = await res.json().catch(() => ({}));
				if (!res.ok || data.success === false) { throw new Error((data && (data.detail || data.message)) || '登入失敗'); }
				const user = (data.data && data.data.user) || { email, name: email.slice(0, email.indexOf('@')) || '會員' };
				Auth.set({ user, accessToken: (data.data && data.data.accessToken) || ('minio-token-' + Date.now()), expiresAt: Date.now() + 3600_000 });
				// 確保每位使用者擁有穩定且唯一的 user_id（供面試狀態隔離用）
				const uid = (user.email || '')
					.toLowerCase()
					.replace('@', '_at_')
					.replace(/[\/\\]/g, '_')
					.replace(/\.\./g, '.');
				localStorage.setItem('jobmate_user_id', uid || ('u-' + Date.now()));
				showToast('登入成功');
				// 使用絕對路徑確保跳轉正確
				setTimeout(() => {
					navigate('/frontend/' + redirect);
				}, 1000);
			} catch (err) { showToast(String(err.message || err), 'error'); }
		});
	});
})();


