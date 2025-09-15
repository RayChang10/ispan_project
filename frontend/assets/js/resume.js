(function () {
    const { $, $all, saveDraft, loadDraft, clearDraft, navigate, cnCharCount, requireAuth } = window.JobMate;

    // 需先登入再進入履歷頁
    if (!requireAuth()) return;

    function toggleOther(selectEl, otherInput) {
        const v = selectEl.value;
        if (v === 'other') otherInput.classList.remove('hidden');
        else { otherInput.classList.add('hidden'); otherInput.value = ''; }
    }

    // 多選 select 工具
    function getMultiValues(selectEl) {
        return Array.from(selectEl.selectedOptions || []).map(o => o.value);
    }

    function toggleOtherMulti(selectEl, otherInput) {
        const values = getMultiValues(selectEl);
        if (values.includes('other')) otherInput.classList.remove('hidden');
        else { otherInput.classList.add('hidden'); otherInput.value = ''; }
    }

    function setMultiSelect(selectEl, values) {
        const set = new Set((values || []).map(v => String(v)));
        Array.from(selectEl.options).forEach(opt => { opt.selected = set.has(opt.value); });
    }

    function counter(textarea, countEl, limit) {
        function update() { countEl.textContent = cnCharCount(textarea.value); }
        textarea.addEventListener('input', update);
        update();
    }

    // 全局監聽：限制所有日期輸入的「年份」最多 4 位數，並且不超過 9999 年
    function enableDateYearGuarding() {
        const handler = (ev) => {
            const el = ev.target;
            if (!el || !(el instanceof HTMLInputElement) || el.type !== 'date') return;
            try { el.setAttribute('max', '9999-12-31'); } catch (_) { }
            const raw = el.value || '';
            if (!raw) return;
            const parts = raw.split(/[\/-]/);
            if (parts.length === 0) return;
            let year = parts[0] || '';
            let month = parts[1] || '';
            let day = parts[2] || '';
            if (year.length > 4) year = year.slice(0, 4);
            if (/^\d+$/.test(year) && Number(year) > 9999) year = '9999';
            const normalized = [year, month, day].filter(Boolean).join('-');
            if (normalized !== raw) el.value = normalized;
        };
        document.addEventListener('input', handler, true);
        document.addEventListener('change', handler, true);
        document.addEventListener('focusin', (ev) => {
            const el = ev.target;
            if (!el || !(el instanceof HTMLInputElement) || el.type !== 'date') return;
            try { el.setAttribute('max', '9999-12-31'); } catch (_) { }
        }, true);
    }

    function createWorkItem() {
        const wrap = document.createElement('div');
        wrap.className = 'dynamic-group';
        wrap.innerHTML = `
			<div class="grid">
				<div>
					<label class="label">公司名稱<span class="badge">必填</span></label>
					<input type="text" class="input company" required />
				</div>
				<div>
					<label class="label">產業類型<span class="badge">必填</span></label>
					<select class="input industry" required>
						<option value="">請選擇</option>
						<option>軟體</option>
						<option>硬體</option>
						<option>金融</option>
						<option value="other">其他</option>
					</select>
					<input class="input industryOther hidden" type="text" placeholder="請輸入產業" />
				</div>
				<div>
					<label class="label">工作地點<span class="badge">必填</span></label>
					<select class="input workLoc" required>
						<option value="">請選擇</option>
						<option>台北市</option>
						<option>新北市</option>
						<option>新竹市</option>
						<option>台中市</option>
						<option>台南市</option>
						<option>高雄市</option>
						<option value="other">其他</option>
					</select>
					<input class="input workLocOther hidden" type="text" placeholder="請輸入地點" />
				</div>
				<div>
					<label class="label">職稱<span class="badge">必填</span></label>
					<input class="input title" type="text" required />
				</div>
				<div>
					<label class="label">職務類別<span class="badge">必填</span></label>
					<div class="grid">
						<select class="input jobCat1" required>
							<option value="">第一層</option>
							<option>工程</option>
							<option>產品</option>
							<option>設計</option>
							<option value="other">其他</option>
						</select>
						<input class="input jobCat1Other hidden" type="text" placeholder="請輸入第一層類別" />
						<select class="input jobCat2" required>
							<option value="">第二層</option>
							<option>前端工程師</option>
							<option>後端工程師</option>
							<option>資料工程師</option>
							<option value="other">其他</option>
						</select>
						<input class="input jobCat2Other hidden" type="text" placeholder="請輸入第二層類別" />
					</div>
				</div>
				<div>
					<label class="label">開始日期<span class="badge">必填</span></label>
					<input type="date" class="input startDate" required />
				</div>
				<div>
					<label class="label">結束日期<span class="badge">必填</span></label>
					<div>
						<label><input type="radio" name="status_${Date.now()}" value="current" checked> 任職中</label>
						<label style="margin-left:12px;"><input type="radio" name="status_${Date.now()}" value="left"> 已離職</label>
					</div>
					<input type="date" class="input endDate hidden" />
				</div>
				<div class="col">
					<label class="label">工作描述（上限500字）<span class="badge">必填</span></label>
					<textarea class="desc" maxlength="500" required></textarea>
					<div class="help"><span class="descCount">0</span> / 500</div>
				</div>
				<div class="col">
					<label class="label">主要技能</label>
					<textarea class="skills" maxlength="1000"></textarea>
				</div>
				<div>
					<label class="label">薪資待遇（數字）<span class="badge">必填</span></label>
					<input type="number" class="input salary" required />
				</div>
				<div>
					<label class="label">薪資類型<span class="badge">必填</span></label>
					<select class="input salaryType" required>
						<option value="">請選擇</option>
						<option>月薪</option>
						<option>年薪</option>
						<option>時薪</option>
					</select>
				</div>
				<div>
					<label class="label">管理責任<span class="badge">必填</span></label>
					<div>
						<label><input type="radio" name="mgr_${Date.now()}" value="yes" required> 是</label>
						<label style="margin-left:12px;"><input type="radio" name="mgr_${Date.now()}" value="no"> 否</label>
					</div>
				</div>
			</div>
			<div class="actions">
				<button class="button danger btnDel">刪除此筆</button>
			</div>
		`;

        const industry = $('.industry', wrap);
        const industryOther = $('.industryOther', wrap);
        industry.addEventListener('change', () => toggleOther(industry, industryOther));
        const workLoc = $('.workLoc', wrap);
        const workLocOther = $('.workLocOther', wrap);
        workLoc.addEventListener('change', () => toggleOther(workLoc, workLocOther));

        const jobCat1 = $('.jobCat1', wrap);
        const jobCat1Other = $('.jobCat1Other', wrap);
        if (jobCat1) jobCat1.addEventListener('change', () => { toggleOther(jobCat1, jobCat1Other); if (jobCat1Other) jobCat1Other.required = (jobCat1.value === 'other'); });
        const jobCat2 = $('.jobCat2', wrap);
        const jobCat2Other = $('.jobCat2Other', wrap);
        if (jobCat2) jobCat2.addEventListener('change', () => { toggleOther(jobCat2, jobCat2Other); if (jobCat2Other) jobCat2Other.required = (jobCat2.value === 'other'); });

        const radioName = $all('input[type=radio][name^=status_]', wrap);
        const endDate = $('.endDate', wrap);
        radioName.forEach(r => {
            r.addEventListener('change', () => {
                endDate.classList.toggle('hidden', r.value !== 'left' || !r.checked);
            });
        });

        const d = $('.desc', wrap);
        counter(d, $('.descCount', wrap), 500);

        $('.btnDel', wrap).addEventListener('click', () => wrap.remove());
        return wrap;
    }

    function createEduItem() {
        const wrap = document.createElement('div');
        wrap.className = 'dynamic-group';
        wrap.innerHTML = `
			<div class="grid">
				<div>
					<label class="label">學校名稱<span class="badge">必填</span></label>
					<input type="text" class="input school" required />
				</div>
				<div>
					<label class="label">學校名稱<span class="badge">必填</span></label>
					<input type="text" class="input school2" required />
				</div>
				<div>
					<label class="label">學位<span class="badge">必填</span></label>
					<select class="input degree" required>
						<option value="">請選擇</option>
						<option value="vocational">高職</option>
						<option value="bachelor">大學</option>
						<option value="master">碩士</option>
						<option value="phd">博士</option>
						<option value="other">其他</option>
					</select>
				</div>
				<div class="majorWrap hidden">
					<label class="label">主修<span class="badge">必填</span></label>
					<div class="actions" style="gap:8px;">
						<input type="text" class="input major" placeholder="請輸入主修" />
						<button class="button secondary addMajor">新增主修</button>
					</div>
					<div class="help majors"></div>
				</div>
				<div>
					<label class="label">開始日期<span class="badge">必填</span></label>
					<input type="date" class="input eduStart" required />
				</div>
				<div>
					<label class="label">結束日期<span class="badge">必填</span></label>
					<div>
						<label><input type="radio" name="study_${Date.now()}" value="studying" checked> 就學中</label>
						<label style="margin-left:12px;"><input type="radio" name="study_${Date.now()}" value="graduated"> 已畢業</label>
					</div>
					<input type="date" class="input eduEnd hidden" />
				</div>
				<div>
					<label class="label">學校地區<span class="badge">必填</span></label>
					<select class="input eduLoc" required>
						<option value="">請選擇</option>
						<option>台北市</option>
						<option>新北市</option>
						<option>新竹市</option>
						<option>台中市</option>
						<option>台南市</option>
						<option>高雄市</option>
						<option value="other">其他</option>
					</select>
					<input class="input eduLocOther hidden" type="text" placeholder="請輸入地區" />
				</div>
			</div>
			<div class="actions">
				<button class="button danger btnDel">刪除此筆</button>
			</div>
		`;

        const degree = $('.degree', wrap);
        const majorWrap = $('.majorWrap', wrap);
        degree.addEventListener('change', () => {
            majorWrap.classList.toggle('hidden', !['vocational', 'bachelor', 'master', 'phd'].includes(degree.value));
        });
        const majors = [];
        $('.addMajor', wrap).addEventListener('click', () => {
            const val = $('.major', wrap).value.trim();
            if (!val) return;
            majors.push(val);
            $('.major', wrap).value = '';
            $('.majors', wrap).textContent = '主修：' + majors.join('、');
        });

        const studyRadios = $all('input[type=radio][name^=study_]', wrap);
        const eduEnd = $('.eduEnd', wrap);
        studyRadios.forEach(r => r.addEventListener('change', () => {
            eduEnd.classList.toggle('hidden', r.value !== 'graduated' || !r.checked);
        }));

        const eduLoc = $('.eduLoc', wrap);
        const eduLocOther = $('.eduLocOther', wrap);
        eduLoc.addEventListener('change', () => toggleOther(eduLoc, eduLocOther));

        $('.btnDel', wrap).addEventListener('click', () => wrap.remove());
        return wrap;
    }

    function createSkillItem() {
        const wrap = document.createElement('div');
        wrap.className = 'dynamic-group';
        wrap.innerHTML = `
			<div class="grid">
				<div>
					<label class="label">技能名稱<span class="badge">必填</span></label>
					<input type="text" class="input skName" required />
				</div>
				<div class="col">
					<label class="label">技能描述（上限500字）<span class="badge">必填</span></label>
					<textarea class="skDesc" maxlength="500" required></textarea>
					<div class="help"><span class="skCount">0</span> / 500</div>
				</div>
			</div>
			<div class="actions">
				<button class="button danger btnDel">刪除此筆</button>
			</div>
		`;
        const d = $('.skDesc', wrap);
        const c = $('.skCount', wrap);
        d.addEventListener('input', () => c.textContent = cnCharCount(d.value));
        $('.btnDel', wrap).addEventListener('click', () => wrap.remove());
        return wrap;
    }

    function createProjItem() {
        const wrap = document.createElement('div');
        wrap.className = 'dynamic-group';
        wrap.innerHTML = `
			<div class="grid">
				<div>
					<label class="label">專案名稱<span class="badge">必填</span></label>
					<input type="text" class="input pjName" required />
				</div>
				<div>
					<label class="label">開始日期<span class="badge">必填</span></label>
					<input type="date" class="input pjStart" required />
				</div>
				<div>
					<label class="label">結束日期<span class="badge">必填</span></label>
					<div>
						<label><input type="radio" name="proj_${Date.now()}" value="ongoing" checked> 執行中</label>
						<label style="margin-left:12px;"><input type="radio" name="proj_${Date.now()}" value="done"> 已結束</label>
					</div>
					<input type="date" class="input pjEnd hidden" />
				</div>
				<div class="col">
					<label class="label">專案說明（上限500字）<span class="badge">必填</span></label>
					<textarea class="pjDesc" maxlength="500" required></textarea>
					<div class="help"><span class="pjCount">0</span> / 500</div>
				</div>
				<div>
					<label class="label">專案連結</label>
					<input type="url" class="input pjLink" />
				</div>
			</div>
			<div class="actions">
				<button class="button danger btnDel">刪除此筆</button>
			</div>
		`;
        const pjRadios = $all('input[type=radio][name^=proj_]', wrap);
        const pjEnd = $('.pjEnd', wrap);
        pjRadios.forEach(r => r.addEventListener('change', () => {
            pjEnd.classList.toggle('hidden', r.value !== 'done' || !r.checked);
        }));
        const d = $('.pjDesc', wrap), c = $('.pjCount', wrap);
        d.addEventListener('input', () => c.textContent = cnCharCount(d.value));
        $('.btnDel', wrap).addEventListener('click', () => wrap.remove());
        return wrap;
    }

    function createLangItem() {
        const wrap = document.createElement('div');
        wrap.className = 'dynamic-group';
        wrap.innerHTML = `
			<div class="grid">
				<div>
					<label class="label">語言名稱<span class="badge">必填</span></label>
					<input type="text" class="input lgName" required />
				</div>
				<div class="grid-3">
					<div>
						<label class="label">聽<span class="badge">必填</span></label>
						<select class="input lgListen" required>
							<option value="">請選擇</option>
							<option>初階</option>
							<option>中階</option>
							<option>高階</option>
						</select>
					</div>
					<div>
						<label class="label">說<span class="badge">必填</span></label>
						<select class="input lgSpeak" required>
							<option value="">請選擇</option>
							<option>初階</option>
							<option>中階</option>
							<option>高階</option>
						</select>
					</div>
					<div>
						<label class="label">讀<span class="badge">必填</span></label>
						<select class="input lgRead" required>
							<option value="">請選擇</option>
							<option>初階</option>
							<option>中階</option>
							<option>高階</option>
						</select>
					</div>
					<div>
						<label class="label">寫<span class="badge">必填</span></label>
						<select class="input lgWrite" required>
							<option value="">請選擇</option>
							<option>初階</option>
							<option>中階</option>
							<option>高階</option>
						</select>
					</div>
				</div>
				<div>
					<label class="label">語言證照名稱</label>
					<input type="text" class="input lgCert" />
				</div>
				<div>
					<label class="label">證照描述</label>
					<input type="text" class="input lgCertDesc" />
				</div>
			</div>
			<div class="actions">
				<button class="button danger btnDel">刪除此筆</button>
			</div>
		`;
        $('.btnDel', wrap).addEventListener('click', () => wrap.remove());
        return wrap;
    }

    function createCertItem() {
        const wrap = document.createElement('div');
        wrap.className = 'dynamic-group';
        wrap.innerHTML = `
			<div class="grid">
				<div>
					<label class="label">證照名稱<span class="badge">必填</span></label>
					<input type="text" class="input ctName" required />
				</div>
				<div>
					<label class="label">證照描述<span class="badge">必填</span></label>
					<input type="text" class="input ctDesc" required />
				</div>
			</div>
			<div class="actions">
				<button class="button danger btnDel">刪除此筆</button>
			</div>
		`;
        $('.btnDel', wrap).addEventListener('click', () => wrap.remove());
        return wrap;
    }

    function addInitialEducation() {
        $('#eduList').appendChild(createEduItem());
    }

    function bindBasics() {
        const loc = $('#location');
        loc.addEventListener('change', () => toggleOther(loc, $('#locationOther')));
        const expDomain = $('#expDomain');
        expDomain.addEventListener('change', () => toggleOther(expDomain, $('#expDomainOther')));
        const expLoc = '#expLocation';
        const expLocEl = document.querySelector(expLoc);
        if (expLocEl) expLocEl.addEventListener('change', () => toggleOtherMulti(expLocEl, $('#expLocationOther')));

        const summary = $('#summary');
        summary.addEventListener('input', () => $('#summaryCount').textContent = cnCharCount(summary.value));
        const bioZh = $('#bioZh'); bioZh.addEventListener('input', () => $('#bioZhCount').textContent = cnCharCount(bioZh.value));
        const bioZh2 = $('#bioZh2'); bioZh2.addEventListener('input', () => $('#bioZh2Count').textContent = cnCharCount(bioZh2.value));
    }

    function bindDynamicButtons() {
        $('#addWork').addEventListener('click', () => $('#workList').appendChild(createWorkItem()));
        $('#addEdu').addEventListener('click', () => $('#eduList').appendChild(createEduItem()));
        $('#addSkill').addEventListener('click', () => $('#skillList').appendChild(createSkillItem()));
        $('#addProj').addEventListener('click', () => $('#projList').appendChild(createProjItem()));
        $('#addLang').addEventListener('click', () => $('#langList').appendChild(createLangItem()));
        $('#addCert').addEventListener('click', () => $('#certList').appendChild(createCertItem()));
    }

    function toJSON() {
        // 只做簡要蒐集示意（完整校驗可再加強）
        const getVal = sel => $(sel)?.value || '';
        return {
            name: getVal('#name'),
            age: getVal('#age'),
            location: getVal('#location') === 'other' ? getVal('#locationOther') : getVal('#location'),
            locationOther: getVal('#locationOther'),
            summary: getVal('#summary'),
            keywords: Array.from(document.querySelectorAll('#keywordList .kw')).map(x => x.dataset.value),
            expectation: {
                domain: getVal('#expDomain') === 'other' ? getVal('#expDomainOther') : getVal('#expDomain'),
                // 多選地點：選中的選項（排除 other）+ 其他輸入（以、或逗號分隔）
                location: (function () {
                    const sel = document.getElementById('expLocation');
                    const selected = Array.from(sel?.selectedOptions || []).map(o => o.value).filter(v => v && v !== 'other');
                    const extra = (document.getElementById('expLocationOther')?.value || '')
                        .split(/[、,，\s]+/).map(s => s.trim()).filter(Boolean);
                    return Array.from(new Set([...selected, ...extra]));
                })(),
                remote: (document.querySelector('input[name=remote]:checked') || {}).value || ''
            },
            works: $all('#workList .dynamic-group').map(w => ({
                company: $('.company', w).value,
                industry: $('.industry', w).value === 'other' ? $('.industryOther', w).value : $('.industry', w).value,
                location: $('.workLoc', w).value === 'other' ? $('.workLocOther', w).value : $('.workLoc', w).value,
                title: $('.title', w).value,
                jobCategory: {
                    level1: $('.jobCat1', w).value === 'other' ? ($('.jobCat1Other', w).value || '') : $('.jobCat1', w).value,
                    level2: $('.jobCat2', w).value === 'other' ? ($('.jobCat2Other', w).value || '') : $('.jobCat2', w).value
                },
                start: $('.startDate', w).value,
                end: $('.endDate', w).classList.contains('hidden') ? null : $('.endDate', w).value,
                desc: $('.desc', w).value,
                skills: $('.skills', w).value,
                salary: $('.salary', w).value,
                salaryType: $('.salaryType', w).value,
                management: (Array.from($all('input[type=radio][name^=mgr_]', w)).find(x => x.checked) || {}).value
            })),
            educations: $all('#eduList .dynamic-group').map(e => ({
                school: $('.school', e).value,
                school2: $('.school2', e).value,
                degree: $('.degree', e).value,
                majors: ($('.majors', e).textContent.replace('主修：', '') || '').split('、').filter(Boolean),
                start: $('.eduStart', e).value,
                end: $('.eduEnd', e).classList.contains('hidden') ? null : $('.eduEnd', e).value,
                location: $('.eduLoc', e).value === 'other' ? $('.eduLocOther', e).value : $('.eduLoc', e).value
            })),
            skills: $all('#skillList .dynamic-group').map(s => ({ name: $('.skName', s).value, desc: $('.skDesc', s).value })),
            projects: $all('#projList .dynamic-group').map(p => ({
                name: $('.pjName', p).value,
                start: $('.pjStart', p).value,
                end: $('.pjEnd', p).classList.contains('hidden') ? null : $('.pjEnd', p).value,
                desc: $('.pjDesc', p).value,
                link: $('.pjLink', p).value
            })),
            languages: $all('#langList .dynamic-group').map(l => ({
                name: $('.lgName', l).value,
                listen: $('.lgListen', l).value,
                speak: $('.lgSpeak', l).value,
                read: $('.lgRead', l).value,
                write: $('.lgWrite', l).value,
                cert: $('.lgCert', l).value,
                certDesc: $('.lgCertDesc', l).value
            })),
            bio: { zh: getVal('#bioZh'), zh2: getVal('#bioZh2') },
            certs: $all('#certList .dynamic-group').map(c => ({ name: $('.ctName', c).value, desc: $('.ctDesc', c).value }))
        };
    }

    function bindActions() {
        $('#btnBack').addEventListener('click', () => navigate('index.html'));
        $('#btnClear').addEventListener('click', () => {
            if (confirm('確定要清除所有輸入？')) {
                localStorage.removeItem('jm_resume');
                location.reload();
            }
        });
        $('#btnDraft').addEventListener('click', () => {
            saveDraft('jm_resume', toJSON());
            alert('已儲存草稿');
        });
        $('#btnDone').addEventListener('click', () => {
            saveDraft('jm_resume', toJSON());
            navigate('matching.html');
        });
    }

    async function initFromDraft() {
        // 優先嘗試載入解析的履歷資料
        try {
            console.log('正在載入解析的履歷資料...');
            const response = await fetch('/api/users/resume/latest');

            if (response.ok) {
                const result = await response.json();
                if (result.success && result.data) {
                    console.log('成功載入履歷資料:', result.data);
                    console.log('工作經歷數量:', result.data.works?.length || 0);
                    console.log('教育背景數量:', result.data.educations?.length || 0);
                    console.log('技能數量:', result.data.skills?.length || 0);
                    console.log('專案數量:', result.data.projects?.length || 0);
                    console.log('關鍵字數量:', result.data.keywords?.length || 0);
                    const data = result.data;

                    // 填入基本資料
                    $('#name').value = data.name || '';
                    $('#age').value = data.age || '';

                    // 處理居住地
                    if (data.location) {
                        const known = ['台北市', '新北市', '桃園市', '台中市', '台南市', '高雄市'];
                        if (known.includes(data.location)) {
                            $('#location').value = data.location;
                        } else {
                            $('#location').value = 'other';
                            $('#locationOther').classList.remove('hidden');
                            $('#locationOther').value = data.location;
                        }
                    }

                    // 填入簡介
                    if (data.summary) {
                        $('#summary').value = data.summary;
                        $('#summary').dispatchEvent(new Event('input'));
                    }

                    // 處理期望工作
                    if (data.expectation) {
                        if (data.expectation.domain) {
                            const known = ['軟體工程', '資料科學', '產品/專案'];
                            if (known.includes(data.expectation.domain)) {
                                $('#expDomain').value = data.expectation.domain;
                            } else {
                                $('#expDomain').value = 'other';
                                $('#expDomainOther').classList.remove('hidden');
                                $('#expDomainOther').value = data.expectation.domain;
                            }
                        }

                        if (data.expectation.remote) {
                            const remoteValue = data.expectation.remote;
                            const input = document.querySelector(`input[name=remote][value="${remoteValue}"]`);
                            if (input) input.checked = true;
                        }

                        // 處理期望工作地點
                        if (data.expectation.location && Array.isArray(data.expectation.location)) {
                            const selEl = document.getElementById('expLocation');
                            if (selEl) {
                                const knownCities = ['台北市', '新北市', '新竹市', '台中市', '台南市', '高雄市'];
                                const selectedKnown = [];
                                const others = [];

                                data.expectation.location.forEach(city => {
                                    if (knownCities.includes(city)) {
                                        selectedKnown.push(city);
                                    } else {
                                        others.push(city);
                                    }
                                });

                                // 設定已知城市的選項
                                Array.from(selEl.options).forEach(opt => {
                                    if (selectedKnown.includes(opt.value)) {
                                        opt.selected = true;
                                    }
                                });

                                // 如果有其他城市，設定其他選項
                                if (others.length > 0) {
                                    const otherOption = Array.from(selEl.options).find(opt => opt.value === 'other');
                                    if (otherOption) {
                                        otherOption.selected = true;
                                        $('#expLocationOther').classList.remove('hidden');
                                        $('#expLocationOther').value = others.join('、');
                                    }
                                }
                            }
                        }
                    }

                    // 處理關鍵字
                    if (data.keywords && Array.isArray(data.keywords)) {
                        const list = document.getElementById('keywordList');
                        if (list) {
                            data.keywords.forEach(keyword => {
                                if (keyword && keyword.trim()) {
                                    const item = document.createElement('span');
                                    item.className = 'badge kw';
                                    item.dataset.value = keyword;
                                    item.style.display = 'inline-flex';
                                    item.style.alignItems = 'center';
                                    item.style.gap = '6px';
                                    item.textContent = keyword;
                                    const del = document.createElement('button');
                                    del.className = 'button danger';
                                    del.textContent = '刪除';
                                    del.style.padding = '2px 8px';
                                    del.style.fontSize = '12px';
                                    del.addEventListener('click', () => item.remove());
                                    item.appendChild(del);
                                    list.appendChild(item);
                                }
                            });
                        }
                    }

                    // 處理工作經歷
                    if (data.works && Array.isArray(data.works)) {
                        data.works.forEach(work => {
                            const item = createWorkItem();

                            // 基本資訊
                            $('.company', item).value = work.company || '';
                            $('.title', item).value = work.title || '';

                            // 轉換日期格式 YYYY/MM -> YYYY-MM-01
                            if (work.start) {
                                const startDate = work.start.replace('/', '-') + (work.start.length <= 7 ? '-01' : '');
                                $('.startDate', item).value = startDate;
                            }

                            $('.desc', item).value = work.desc || work.bullets?.join('\n') || '';
                            $('.skills', item).value = work.skills || '';

                            // 薪資欄位（後端目前沒有提供，設為空）
                            $('.salary', item).value = work.salary || '';
                            $('.salaryType', item).value = work.salaryType || '';

                            // 產業類型（後端目前沒有提供，根據公司名稱推測或設為空）
                            if (work.industry) {
                                const knownIndustries = ['軟體', '硬體', '金融'];
                                if (knownIndustries.includes(work.industry)) {
                                    $('.industry', item).value = work.industry;
                                } else {
                                    $('.industry', item).value = 'other';
                                    $('.industryOther', item).classList.remove('hidden');
                                    $('.industryOther', item).value = work.industry;
                                }
                            } else {
                                // 根據公司名稱進行簡單推測
                                const companyName = work.company || '';
                                if (companyName.includes('Delta') || companyName.includes('Micron') || companyName.includes('Winbond')) {
                                    $('.industry', item).value = '硬體';
                                } else {
                                    $('.industry', item).value = '軟體'; // 預設值
                                }
                            }

                            // 工作地點（後端沒有提供，根據公司推測）
                            if (work.location) {
                                const knownLocations = ['台北市', '新北市', '新竹市', '台中市', '台南市', '高雄市'];
                                if (knownLocations.includes(work.location)) {
                                    $('.workLoc', item).value = work.location;
                                } else {
                                    $('.workLoc', item).value = 'other';
                                    $('.workLocOther', item).classList.remove('hidden');
                                    $('.workLocOther', item).value = work.location;
                                }
                            } else {
                                // 根據公司名稱推測地點，預設為台北市
                                $('.workLoc', item).value = '台北市';
                            }

                            // 結束日期
                            if (work.end && work.end !== 'Present' && work.end !== '至今') {
                                $('.endDate', item).classList.remove('hidden');
                                // 轉換日期格式
                                const endDate = work.end.replace('/', '-') + (work.end.length <= 7 ? '-01' : '');
                                $('.endDate', item).value = endDate;
                                // 設定為已離職
                                const statusRadios = Array.from($all('input[type=radio][name^=status_]', item));
                                statusRadios.forEach(radio => {
                                    if (radio.value === 'left') radio.checked = true;
                                });
                            }

                            // 職務類別（後端目前沒有提供，根據職位名稱推測）
                            const jobTitle = work.title || '';
                            if (jobTitle.includes('Data Scientist') || jobTitle.includes('AI')) {
                                $('.jobCat1', item).value = '工程';
                                $('.jobCat2', item).value = '資料工程師';
                            } else if (jobTitle.includes('Product Manager')) {
                                $('.jobCat1', item).value = '產品';
                                $('.jobCat2', item).value = 'other';
                                $('.jobCat2Other', item).classList.remove('hidden');
                                $('.jobCat2Other', item).value = 'Product Manager';
                            } else if (jobTitle.includes('Engineer')) {
                                $('.jobCat1', item).value = '工程';
                                $('.jobCat2', item).value = '後端工程師';
                            } else {
                                $('.jobCat1', item).value = '工程';
                                $('.jobCat2', item).value = 'other';
                                $('.jobCat2Other', item).classList.remove('hidden');
                                $('.jobCat2Other', item).value = jobTitle;
                            }

                            // 管理責任（後端沒有提供，根據職位推測）
                            if (work.management) {
                                const mgrRadios = Array.from($all('input[type=radio][name^=mgr_]', item));
                                mgrRadios.forEach(radio => {
                                    if (radio.value === work.management) radio.checked = true;
                                });
                            } else {
                                // 如果職位包含 Manager 或 Lead，推測有管理責任
                                const hasManagement = jobTitle.includes('Manager') || jobTitle.includes('Lead') || jobTitle.includes('Led');
                                const mgrRadios = Array.from($all('input[type=radio][name^=mgr_]', item));
                                mgrRadios.forEach(radio => {
                                    if (radio.value === (hasManagement ? 'yes' : 'no')) radio.checked = true;
                                });
                            }

                            // 觸發事件更新計數器
                            $('.desc', item).dispatchEvent(new Event('input'));

                            $('#workList').appendChild(item);
                        });
                    }

                    // 處理教育背景
                    if (data.educations && Array.isArray(data.educations)) {
                        data.educations.forEach(edu => {
                            const item = createEduItem();

                            $('.school', item).value = edu.school || '';
                            // school2 字段在後端API中不存在，使用 school 的值或設為空
                            $('.school2', item).value = edu.school2 || edu.school || '';

                            // 學位映射：將英文學位轉換為中文
                            let degreeValue = edu.degree || '';
                            const degreeMapping = {
                                'Master': 'master',
                                'Bachelor': 'bachelor',
                                'PhD': 'phd',
                                'Doctorate': 'phd',
                                'Vocational': 'vocational',
                                'master': 'master',
                                'bachelor': 'bachelor',
                                'phd': 'phd',
                                'vocational': 'vocational'
                            };
                            $('.degree', item).value = degreeMapping[degreeValue] || degreeValue;
                            // 轉換日期格式
                            if (edu.start) {
                                const startDate = edu.start.replace('/', '-') + (edu.start.length <= 7 ? '-01' : '');
                                $('.eduStart', item).value = startDate;
                            }

                            // 顯示主修區塊如果有學位
                            const mappedDegree = degreeMapping[degreeValue] || degreeValue;
                            if (['vocational', 'bachelor', 'master', 'phd'].includes(mappedDegree)) {
                                $('.majorWrap', item).classList.remove('hidden');
                                // 處理主修字段（可能是 major 字符串或 majors 陣列）
                                let majors = [];
                                if (edu.majors && Array.isArray(edu.majors)) {
                                    majors = edu.majors;
                                } else if (edu.major && typeof edu.major === 'string') {
                                    majors = [edu.major];
                                }
                                if (majors.length > 0) {
                                    $('.majors', item).textContent = '主修：' + majors.join('、');
                                }
                            }

                            // 結束日期
                            if (edu.end) {
                                $('.eduEnd', item).classList.remove('hidden');
                                // 轉換日期格式
                                const endDate = edu.end.replace('/', '-') + (edu.end.length <= 7 ? '-01' : '');
                                $('.eduEnd', item).value = endDate;
                                // 設定為已畢業
                                const studyRadios = Array.from($all('input[type=radio][name^=study_]', item));
                                studyRadios.forEach(radio => {
                                    if (radio.value === 'graduated') radio.checked = true;
                                });
                            }

                            // 學校地區
                            if (edu.location) {
                                const knownLocations = ['台北市', '新北市', '新竹市', '台中市', '台南市', '高雄市'];
                                if (knownLocations.includes(edu.location)) {
                                    $('.eduLoc', item).value = edu.location;
                                } else {
                                    $('.eduLoc', item).value = 'other';
                                    $('.eduLocOther', item).classList.remove('hidden');
                                    $('.eduLocOther', item).value = edu.location;
                                }
                            }

                            $('#eduList').appendChild(item);
                        });
                    }

                    // 處理技能
                    if (data.skills && Array.isArray(data.skills)) {
                        data.skills.forEach(skill => {
                            const item = createSkillItem();
                            $('.skName', item).value = skill.name || skill;
                            $('.skDesc', item).value = skill.desc || '';
                            $('.skDesc', item).dispatchEvent(new Event('input'));
                            $('#skillList').appendChild(item);
                        });
                    }

                    // 處理專案
                    if (data.projects && Array.isArray(data.projects)) {
                        data.projects.forEach(project => {
                            const item = createProjItem();
                            $('.pjName', item).value = project.name || '';

                            // 轉換日期格式
                            if (project.start) {
                                const startDate = project.start.replace('/', '-') + (project.start.length <= 7 ? '-01' : '');
                                $('.pjStart', item).value = startDate;
                            }

                            $('.pjDesc', item).value = project.desc || project.bullets?.join('\n') || '';
                            // link 字段在後端API中不存在，設為空
                            $('.pjLink', item).value = project.link || '';

                            // 結束日期
                            if (project.end) {
                                $('.pjEnd', item).classList.remove('hidden');
                                // 轉換日期格式
                                const endDate = project.end.replace('/', '-') + (project.end.length <= 7 ? '-01' : '');
                                $('.pjEnd', item).value = endDate;
                                // 設定為已結束
                                const projRadios = Array.from($all('input[type=radio][name^=proj_]', item));
                                projRadios.forEach(radio => {
                                    if (radio.value === 'done') radio.checked = true;
                                });
                            }

                            $('.pjDesc', item).dispatchEvent(new Event('input'));
                            $('#projList').appendChild(item);
                        });
                    }

                    // 處理語言
                    if (data.languages && Array.isArray(data.languages)) {
                        data.languages.forEach(lang => {
                            const item = createLangItem();
                            if (typeof lang === 'string') {
                                $('.lgName', item).value = lang;
                            } else {
                                $('.lgName', item).value = lang.name || '';
                                $('.lgListen', item).value = lang.listen || '';
                                $('.lgSpeak', item).value = lang.speak || '';
                                $('.lgRead', item).value = lang.read || '';
                                $('.lgWrite', item).value = lang.write || '';
                                $('.lgCert', item).value = lang.cert || '';
                                $('.lgCertDesc', item).value = lang.certDesc || '';
                            }
                            $('#langList').appendChild(item);
                        });
                    }

                    // 處理證照
                    if (data.certs && Array.isArray(data.certs)) {
                        data.certs.forEach(cert => {
                            const item = createCertItem();
                            if (typeof cert === 'string') {
                                $('.ctName', item).value = cert;
                            } else {
                                $('.ctName', item).value = cert.name || '';
                                $('.ctDesc', item).value = cert.desc || '';
                            }
                            $('#certList').appendChild(item);
                        });
                    }

                    // 處理自傳
                    if (data.bio) {
                        if (data.bio.zh) {
                            $('#bioZh').value = data.bio.zh;
                            $('#bioZh').dispatchEvent(new Event('input'));
                        }
                        if (data.bio.zh2) {
                            $('#bioZh2').value = data.bio.zh2;
                            $('#bioZh2').dispatchEvent(new Event('input'));
                        }
                    }

                    // 如果沒有教育背景，添加一個初始項目
                    if (!data.educations || data.educations.length === 0) {
                        addInitialEducation();
                    }

                    console.log('履歷資料載入完成');
                    return; // 成功載入，直接返回
                }
            }
        } catch (error) {
            console.log('載入履歷資料失敗，使用本地草稿:', error);
        }

        // 如果沒有解析資料，則載入本地草稿
        const d = loadDraft('jm_resume');
        if (!d) { addInitialEducation(); return; }
        $('#name').value = d.name || '';
        $('#age').value = d.age || '';
        if (d.location) {
            const known = ['台北市', '新北市', '桃園市', '台中市', '台南市', '高雄市'];
            if (known.includes(d.location)) {
                $('#location').value = d.location;
            } else { $('#location').value = 'other'; $('#locationOther').classList.remove('hidden'); $('#locationOther').value = d.location; }
        }
        $('#summary').value = d.summary || '';
        $('#summary').dispatchEvent(new Event('input'));
        if (Array.isArray(d.keywords)) { const list = document.getElementById('keywordList'); if (list) { d.keywords.forEach(v => { const item = document.createElement('span'); item.className = 'badge kw'; item.dataset.value = v; item.style.display = 'inline-flex'; item.style.alignItems = 'center'; item.style.gap = '6px'; item.textContent = v; const del = document.createElement('button'); del.className = 'button danger'; del.textContent = '刪除'; del.style.padding = '2px 8px'; del.style.fontSize = '12px'; del.addEventListener('click', () => item.remove()); item.appendChild(del); list.appendChild(item); }); } }

        if (d.expectation) {
            const ed = d.expectation.domain; if (ed) {
                const known = ['軟體工程', '資料科學', '產品/專案'];
                if (known.includes(ed)) $('#expDomain').value = ed; else { $('#expDomain').value = 'other'; $('#expDomainOther').classList.remove('hidden'); $('#expDomainOther').value = ed; }
            }
            const el = d.expectation.location; if (el) {
                const locs = Array.isArray(el) ? el : [el];
                const known = ['台北市', '新北市', '新竹市', '台中市', '台南市', '高雄市'];
                const knownSet = new Set(known);
                const selected = [];
                const others = [];
                locs.forEach(v => { if (knownSet.has(v)) selected.push(v); else if (v) others.push(v); });
                const selEl = document.getElementById('expLocation');
                if (selEl) setMultiSelect(selEl, [...selected, others.length ? 'other' : undefined].filter(Boolean));
                if (others.length) { const o = document.getElementById('expLocationOther'); o.classList.remove('hidden'); o.value = others.join('、'); }
            }
            if (d.expectation.remote) {
                const r = d.expectation.remote === 'yes' ? 'yes' : d.expectation.remote === 'no' ? 'no' : 'any';
                const input = document.querySelector(`input[name=remote][value="${r}"]`);
                if (input) input.checked = true;
            }
        }

        (d.works || []).forEach(w => {
            const item = createWorkItem();
            $('.company', item).value = w.company || '';
            if (w.industry) { if (['軟體', '硬體', '金融'].includes(w.industry)) $('.industry', item).value = w.industry; else { $('.industry', item).value = 'other'; $('.industryOther', item).classList.remove('hidden'); $('.industryOther', item).value = w.industry; } }
            if (w.location) { const known = ['台北市', '新北市', '新竹市', '台中市', '台南市', '高雄市']; if (known.includes(w.location)) $('.workLoc', item).value = w.location; else { $('.workLoc', item).value = 'other'; $('.workLocOther', item).classList.remove('hidden'); $('.workLocOther', item).value = w.location; } }
            $('.title', item).value = w.title || '';
            (function () {
                const jc1 = (w.jobCategory || {}).level1 || '';
                const known1 = ['工程', '產品', '設計'];
                if (known1.includes(jc1)) { $('.jobCat1', item).value = jc1; }
                else if (jc1) { $('.jobCat1', item).value = 'other'; $('.jobCat1Other', item).classList.remove('hidden'); $('.jobCat1Other', item).required = true; $('.jobCat1Other', item).value = jc1; }
                const jc2 = (w.jobCategory || {}).level2 || '';
                const known2 = ['前端工程師', '後端工程師', '資料工程師'];
                if (known2.includes(jc2)) { $('.jobCat2', item).value = jc2; }
                else if (jc2) { $('.jobCat2', item).value = 'other'; $('.jobCat2Other', item).classList.remove('hidden'); $('.jobCat2Other', item).required = true; $('.jobCat2Other', item).value = jc2; }
            })();
            $('.startDate', item).value = w.start || '';
            if (w.end) { $('.endDate', item).classList.remove('hidden'); $('.endDate', item).value = w.end; Array.from($all('input[type=radio][name^=status_]', item)).forEach(r => { if (r.value === 'left') r.checked = true; }); }
            $('.desc', item).value = w.desc || ''; $('.desc', item).dispatchEvent(new Event('input'));
            $('.skills', item).value = w.skills || '';
            $('.salary', item).value = w.salary || '';
            $('.salaryType', item).value = w.salaryType || '';
            Array.from($all('input[type=radio][name^=mgr_]', item)).forEach(r => { if (r.value === (w.management || '')) r.checked = true; });
            $('#workList').appendChild(item);
        });

        (d.educations || []).forEach(e => {
            const item = createEduItem();
            $('.school', item).value = e.school || '';
            $('.school2', item).value = e.school2 || '';
            $('.degree', item).value = e.degree || '';
            if (['vocational', 'bachelor', 'master', 'phd'].includes(e.degree)) $('.majorWrap', item).classList.remove('hidden');
            $('.majors', item).textContent = (e.majors || []).length ? ('主修：' + e.majors.join('、')) : '';
            $('.eduStart', item).value = e.start || '';
            if (e.end) { $('.eduEnd', item).classList.remove('hidden'); $('.eduEnd', item).value = e.end; Array.from($all('input[type=radio][name^=study_]', item)).forEach(r => { if (r.value === 'graduated') r.checked = true; }); }
            if (e.location) { const known = ['台北市', '新北市', '新竹市', '台中市', '台南市', '高雄市']; if (known.includes(e.location)) $('.eduLoc', item).value = e.location; else { $('.eduLoc', item).value = 'other'; $('.eduLocOther', item).classList.remove('hidden'); $('.eduLocOther', item).value = e.location; } }
            $('#eduList').appendChild(item);
        });

        (d.skills || []).forEach(s => { const i = createSkillItem(); $('.skName', i).value = s.name || ''; $('.skDesc', i).value = s.desc || ''; $('#skillList').appendChild(i); });
        (d.projects || []).forEach(p => { const i = createProjItem(); $('.pjName', i).value = p.name || ''; $('.pjStart', i).value = p.start || ''; if (p.end) { $('.pjEnd', i).classList.remove('hidden'); $('.pjEnd', i).value = p.end; Array.from($all('input[type=radio][name^=proj_]', i)).forEach(r => { if (r.value === 'done') r.checked = true; }); } $('.pjDesc', i).value = p.desc || ''; $('.pjLink', i).value = p.link || ''; $('#projList').appendChild(i); });
        (d.languages || []).forEach(l => { const i = createLangItem(); $('.lgName', i).value = l.name || ''; $('.lgListen', i).value = l.listen || ''; $('.lgSpeak', i).value = l.speak || ''; $('.lgRead', i).value = l.read || ''; $('.lgWrite', i).value = l.write || ''; $('.lgCert', i).value = l.cert || ''; $('.lgCertDesc', i).value = l.certDesc || ''; $('#langList').appendChild(i); });
        (d.certs || []).forEach(c => { const i = createCertItem(); $('.ctName', i).value = c.name || ''; $('.ctDesc', i).value = c.desc || ''; $('#certList').appendChild(i); });

        $('#bioZh').value = (d.bio || {}).zh || ''; $('#bioZh').dispatchEvent(new Event('input'));
        $('#bioZh2').value = (d.bio || {}).zh2 || ''; $('#bioZh2').dispatchEvent(new Event('input'));

        if (!d.educations || d.educations.length === 0) addInitialEducation();
    }

    document.addEventListener('DOMContentLoaded', async function () {
        bindBasics();
        bindDynamicButtons();
        bindActions();
        await initFromDraft();
        // 啟用日期年份 4 碼限制
        enableDateYearGuarding();

        // 關鍵字新增/刪除
        function renderKeyword(value) {
            const item = document.createElement('span');
            item.className = 'badge kw';
            item.dataset.value = value;
            item.style.display = 'inline-flex'; item.style.alignItems = 'center'; item.style.gap = '6px';
            item.textContent = value;
            const del = document.createElement('button'); del.className = 'button danger'; del.textContent = '刪除'; del.style.padding = '2px 8px'; del.style.fontSize = '12px';
            del.addEventListener('click', () => item.remove());
            item.appendChild(del);
            return item;
        }
        const addBtn = document.getElementById('addKeyword');
        const input = document.getElementById('keywordInput');
        const list = document.getElementById('keywordList');
        if (addBtn && input && list) {
            addBtn.addEventListener('click', () => { const v = (input.value || '').trim(); if (!v) return; list.appendChild(renderKeyword(v)); input.value = ''; input.focus(); });
            input.addEventListener('keydown', e => { if (e.key === 'Enter') { addBtn.click(); } });
        }
    });
})();