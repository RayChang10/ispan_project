(function () {
	const { $, renderNavbar, showToast, navigate, rel } = window.JobMate;
	const reUpper = /[A-Z]/, reLower = /[a-z]/, reNum = /[0-9]/;
	function okPwd(p) { return p && p.length >= 8 && p.length <= 64 && reUpper.test(p) && reLower.test(p) && reNum.test(p); }

	document.addEventListener('DOMContentLoaded', function () {
		renderNavbar($('#root'));
		$('#registerBtn').addEventListener('click', async () => {
			const email = $('#email').value.trim(), p1 = $('#password').value, p2 = $('#password2').value, name = $('#name').value.trim();
			if (!email || email.length < 8 || email.length > 64) return showToast('帳號長度需 8–64 字', 'error');
			if (!okPwd(p1)) return showToast('密碼需 8–64 字且含大小寫與數字', 'error');
			if (p1 !== p2) return showToast('兩次輸入的密碼不一致', 'error');
			if (!name || name.length > 50) return showToast('姓名必填且不超過 50 字', 'error');
			try {
				const res = await fetch('/api/auth/register', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ email, password: p1, name }) });
				const data = await res.json().catch(() => ({}));
				if (!res.ok || data.success === false) { throw new Error((data && (data.detail || data.message)) || '註冊失敗'); }
				showToast('註冊成功，請登入');
				setTimeout(() => navigate(rel('auth/login.html')), 600);
			} catch (err) { showToast(String(err.message || err), 'error'); }
		});
	});
})();


