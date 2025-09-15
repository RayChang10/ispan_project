(function () {
    const { $, navigate } = window.JobMate;
    function loadJobs() {
        // 以靜態假資料展示最近媒合職缺
        const jobs = [
            { id: 'J001', title: '後端工程師（Go）', company: '星河科技', loc: '台北', pay: '年薪 120-180 萬' },
            { id: 'J003', title: '全端工程師（React/Node）', company: '火箭網科', loc: '遠端', pay: '年薪 120-170 萬' }
        ];
        const box = $('#jobs');
        jobs.forEach(j => {
            const row = document.createElement('div');
            row.className = 'row';
            row.innerHTML = `<div class="col">${j.title}｜${j.company}｜${j.loc}｜${j.pay}</div>`;
            const act = document.createElement('div'); act.className = 'actions';
            const btn = document.createElement('button'); btn.className = 'button primary'; btn.textContent = '選擇';
            btn.addEventListener('click', () => navigate('matching.html'));
            act.appendChild(btn);
            row.appendChild(act);
            box.appendChild(row);
        });
    }
    document.addEventListener('DOMContentLoaded', function () {
        loadJobs();
        $('#home').addEventListener('click', () => navigate('index.html'));
    });
})();



