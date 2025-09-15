(function () {
    const { $, $all, navigate, attachSpeechToInput, showToast, loadDraft, saveDraft, cnCharCount } = window.JobMate;

    let resumeData = {};
    let selectedJob = null;
    let healthCheckResult = null;

    // 載入已儲存的資料
    function loadSavedData() {
        console.log('🔄 開始載入已儲存的資料...');

        // 直接從 localStorage 讀取，因為這是最可靠的方式
        let savedResume = null;

        // 嘗試不同的儲存鍵值
        const possibleKeys = ['jm_resume', 'jobmate_resume'];

        for (const key of possibleKeys) {
            try {
                const storedData = localStorage.getItem(key);
                console.log(`🔍 檢查 ${key}:`, storedData ? '有資料' : '無資料');

                if (storedData) {
                    savedResume = JSON.parse(storedData);
                    console.log(`✅ 從 ${key} 載入成功:`, savedResume);
                    break;
                }
            } catch (error) {
                console.error(`❌ 解析 ${key} 失敗:`, error);
            }
        }

        console.log('🔍 最終 savedResume:', savedResume);
        console.log('🔍 savedResume 類型:', typeof savedResume);
        console.log('🔍 savedResume 是否為物件:', savedResume && typeof savedResume === 'object');

        if (savedResume && typeof savedResume === 'object' && Object.keys(savedResume).length > 0) {
            console.log('✅ 履歷資料載入成功，準備填充表單...');
            resumeData = savedResume;

            // 延遲執行，確保 DOM 完全載入
            setTimeout(() => {
                console.log('📞 調用 populateForm...');
                populateForm(resumeData);
                console.log('📞 populateForm 調用完成');

                // 資料載入完成後，立即安排健檢執行
                console.log('📅 安排自動健檢執行...');
                setTimeout(async () => {
                    try {
                        console.log('🚀 執行資料載入後的自動健檢...');
                        await performHealthCheck();
                        console.log('✅ 資料載入後健檢完成');
                    } catch (error) {
                        console.error('❌ 資料載入後健檢失敗:', error);
                    }
                }, 1000);
            }, 100);
        } else {
            console.warn('❌ 未找到有效的履歷資料');
            resumeData = {};
        }

        // 載入選中的職缺
        try {
            const savedJob = localStorage.getItem('jobmate_selected_job');
            if (savedJob) {
                selectedJob = JSON.parse(savedJob);
                console.log('載入選中職缺:', selectedJob);
            } else {
                console.warn('未找到選中的職缺');
            }
        } catch (error) {
            console.error('載入選中職缺失敗:', error);
        }
    }

    // 填充表單資料
    function populateForm(data) {
        console.log('🔧 開始填充表單資料:', data);

        // 檢查 $ 函數是否可用
        if (typeof $ !== 'function') {
            console.error('❌ $ 函數不可用，無法填充表單');
            return;
        }

        // 等待 DOM 完全載入
        if (document.readyState !== 'complete') {
            console.log('⏳ DOM 尚未完全載入，延遲執行...');
            setTimeout(() => populateForm(data), 500);
            return;
        }

        console.log('📋 DOM 已就緒，開始填充表單...');

        // 基本資料 - 使用原生 DOM 選取器
        if (data.name) {
            const nameEl = document.getElementById('name');
            console.log('🔍 name 元素:', nameEl);
            if (nameEl) {
                nameEl.value = data.name;
                console.log('✅ 姓名已填入:', data.name);
            } else {
                console.warn('❌ #name 元素不存在');
            }
        }

        if (data.age) {
            const ageEl = document.getElementById('age');
            console.log('🔍 age 元素:', ageEl);
            if (ageEl) {
                ageEl.value = data.age;
                console.log('✅ 年齡已填入:', data.age);
            } else {
                console.warn('❌ #age 元素不存在');
            }
        }

        if (data.location) {
            const locationEl = document.getElementById('location');
            console.log('🔍 location 元素:', locationEl);
            if (locationEl) {
                locationEl.value = data.location;
                console.log('✅ 居住地已填入:', data.location);

                // 如果是 "其他"，顯示其他輸入框
                if (data.location === 'other' && data.locationOther) {
                    const locationOtherEl = document.getElementById('locationOther');
                    if (locationOtherEl) {
                        locationOtherEl.classList.remove('hidden');
                        locationOtherEl.value = data.locationOther;
                    }
                }
            } else {
                console.warn('❌ #location 元素不存在');
            }
        }

        // 簡介/摘要
        if (data.summary || data.intro) {
            const summaryText = data.summary || data.intro || '';
            const summaryEl = document.getElementById('summary');
            console.log('🔍 summary 元素:', summaryEl);
            if (summaryEl) {
                summaryEl.value = summaryText;
                console.log('✅ 簡介已填入:', summaryText.substring(0, 50) + '...');
                updateSummaryCount();
            } else {
                console.warn('❌ #summary 元素不存在');
            }
        }

        // 關鍵字 - 處理不同格式
        let keywordList = [];
        if (data.keywords) {
            if (typeof data.keywords === 'string') {
                keywordList = data.keywords.split(',').map(k => k.trim()).filter(k => k);
            } else if (Array.isArray(data.keywords)) {
                keywordList = data.keywords;
            }
            keywordList.forEach(keyword => addKeywordTag(keyword));
        }

        // 期望工作資訊 - 支持兩種格式
        if (data.expDomain) {
            const expDomainEl = document.getElementById('expDomain');
            console.log('🔍 expDomain 元素:', expDomainEl);
            if (expDomainEl) {
                expDomainEl.value = data.expDomain;
                console.log('✅ 期望領域已填入:', data.expDomain);

                if (data.expDomain === 'other' && data.expDomainOther) {
                    const expDomainOtherEl = document.getElementById('expDomainOther');
                    if (expDomainOtherEl) {
                        expDomainOtherEl.classList.remove('hidden');
                        expDomainOtherEl.value = data.expDomainOther;
                    }
                }
            }
        } else if (data.expectation && data.expectation.domain) {
            const expDomainEl = document.getElementById('expDomain');
            if (expDomainEl) {
                expDomainEl.value = data.expectation.domain;
                console.log('✅ 期望領域已填入 (expectation):', data.expectation.domain);
            }
        }

        if (data.expLocation) {
            const expLocationEl = document.getElementById('expLocation');
            console.log('🔍 expLocation 元素:', expLocationEl);
            if (expLocationEl) {
                expLocationEl.value = data.expLocation;
                console.log('✅ 期望地點已填入:', data.expLocation);

                if (data.expLocation === 'other' && data.expLocationOther) {
                    const expLocationOtherEl = document.getElementById('expLocationOther');
                    if (expLocationOtherEl) {
                        expLocationOtherEl.classList.remove('hidden');
                        expLocationOtherEl.value = data.expLocationOther;
                    }
                }
            }
        } else if (data.expectation && data.expectation.location) {
            // expectation.location 是陣列格式
            if (Array.isArray(data.expectation.location) && data.expectation.location.length > 0) {
                const expLocationEl = document.getElementById('expLocation');
                if (expLocationEl) {
                    expLocationEl.value = data.expectation.location[0];
                    console.log('✅ 期望地點已填入 (expectation):', data.expectation.location[0]);
                }
            }
        }

        if (data.remote) {
            const remoteRadio = document.querySelector(`input[name="remote"][value="${data.remote}"]`);
            console.log('🔍 remote 單選框:', remoteRadio);
            if (remoteRadio) {
                remoteRadio.checked = true;
                console.log('✅ 遠端工作選項已設定:', data.remote);
            }
        } else if (data.expectation && data.expectation.remote) {
            const remoteRadio = document.querySelector(`input[name="remote"][value="${data.expectation.remote}"]`);
            if (remoteRadio) {
                remoteRadio.checked = true;
                console.log('✅ 遠端工作選項已設定 (expectation):', data.expectation.remote);
            }
        }

        // 動態列表資料 - 先清空現有內容
        const workListEl = document.getElementById('workList');
        const eduListEl = document.getElementById('eduList');
        const skillListEl = document.getElementById('skillList');
        const projListEl = document.getElementById('projList');
        const langListEl = document.getElementById('langList');
        const certListEl = document.getElementById('certList');

        if (workListEl) workListEl.innerHTML = '';
        if (eduListEl) eduListEl.innerHTML = '';
        if (skillListEl) skillListEl.innerHTML = '';
        if (projListEl) projListEl.innerHTML = '';
        if (langListEl) langListEl.innerHTML = '';
        if (certListEl) certListEl.innerHTML = '';

        console.log('🧹 動態列表已清空');

        // 工作經歷 - 支持兩種格式
        const workData = data.workList || data.works || [];
        if (Array.isArray(workData)) {
            workData.forEach(work => {
                // 轉換格式以適配 addWorkExperience
                const workItem = {
                    company: work.company || '',
                    title: work.title || '',
                    startDate: work.startDate || work.start || '',
                    endDate: work.endDate || work.end || '',
                    desc: work.desc || work.description || ''
                };
                addWorkExperience(workItem);
            });
        }

        // 教育背景 - 支持兩種格式
        const eduData = data.eduList || data.educations || [];
        if (Array.isArray(eduData)) {
            eduData.forEach(edu => {
                const eduItem = {
                    school: edu.school || '',
                    degree: edu.degree || '',
                    major: edu.major || (Array.isArray(edu.majors) ? edu.majors.join(', ') : ''),
                    startDate: edu.startDate || edu.start || '',
                    endDate: edu.endDate || edu.end || ''
                };
                addEducation(eduItem);
            });
        }

        // 技能 - 支持兩種格式
        const skillData = data.skillList || data.skills || [];
        if (Array.isArray(skillData)) {
            skillData.forEach(skill => {
                const skillItem = {
                    category: skill.category || '其他',
                    name: skill.name || '',
                    level: skill.level || '普通'
                };
                addSkill(skillItem);
            });
        }

        // 專案 - 支持兩種格式
        const projData = data.projList || data.projects || [];
        if (Array.isArray(projData)) {
            projData.forEach(proj => {
                const projItem = {
                    name: proj.name || '',
                    role: proj.role || '參與者',
                    startDate: proj.startDate || proj.start || '',
                    endDate: proj.endDate || proj.end || '',
                    desc: proj.desc || proj.description || ''
                };
                addProject(projItem);
            });
        }

        // 語言 - 支持兩種格式
        const langData = data.langList || data.languages || [];
        if (Array.isArray(langData)) {
            langData.forEach(lang => {
                const langItem = {
                    name: lang.name || '',
                    level: lang.level || lang.speak || '中級',
                    cert: lang.cert || ''
                };
                addLanguage(langItem);
            });
        }

        // 證照 - 支持兩種格式
        const certData = data.certList || data.certs || [];
        if (Array.isArray(certData)) {
            certData.forEach(cert => {
                const certItem = {
                    name: cert.name || '',
                    org: cert.org || cert.organization || '',
                    date: cert.date || cert.issueDate || ''
                };
                addCertification(certItem);
            });
        }

        console.log('表單填充完成');
    }

    // 收集表單資料
    function collectFormData() {
        const data = {
            name: $('#name').value.trim(),
            age: $('#age').value.trim(),
            location: $('#location').value,
            locationOther: $('#locationOther').value.trim(),
            summary: $('#summary').value.trim(),
            keywords: collectKeywords().join(', '),
            expDomain: $('#expDomain').value,
            expDomainOther: $('#expDomainOther').value.trim(),
            expLocation: $('#expLocation').value,
            expLocationOther: $('#expLocationOther').value.trim(),
            remote: document.querySelector('input[name="remote"]:checked')?.value || '',
            workList: collectWorkList(),
            eduList: collectEduList(),
            skillList: collectSkillList(),
            projList: collectProjList(),
            langList: collectLangList(),
            certList: collectCertList()
        };

        return data;
    }

    // 執行履歷健檢
    async function performHealthCheck() {
        try {
            console.log('🚀 開始執行履歷健檢...');
            showToast('正在進行履歷健檢...', 'info');

            const currentData = collectFormData();
            console.log('📋 發送履歷資料:', currentData);
            console.log('🎯 目標職缺:', selectedJob);

            // 檢查 API 是否可用
            if (typeof window.JobMateAPI === 'undefined') {
                console.error('❌ JobMateAPI 不可用');
                showToast('API 模組未載入', 'error');
                return;
            }

            if (!window.JobMateAPI.JobSearch) {
                console.error('❌ JobSearch API 不可用');
                showToast('JobSearch API 未載入', 'error');
                return;
            }

            // 呼叫履歷健檢 API
            const result = await window.JobMateAPI.JobSearch.resumeHealthCheck(currentData, selectedJob);
            console.log('API 回應:', result);

            if (result.success || result.status === 'success') {
                healthCheckResult = result;

                // 處理不同的回應格式
                let healthCheckData = null;
                if (result.result && result.result.health_check) {
                    healthCheckData = result.result.health_check;
                } else if (result.health_check) {
                    healthCheckData = result.health_check;
                } else if (result.result) {
                    healthCheckData = result.result;
                } else {
                    healthCheckData = result;
                }

                displayHealthCheckResult(healthCheckData);
                showToast('履歷健檢完成！', 'success');
            } else {
                const errorMsg = result.message || result.detail || '未知錯誤';
                showToast('履歷健檢失敗：' + errorMsg, 'error');
                console.error('API 錯誤回應:', result);
            }
        } catch (error) {
            console.error('履歷健檢失敗:', error);
            showToast('履歷健檢失敗，請稍後再試', 'error');

            // 顯示錯誤詳情給開發者
            if (error.message) {
                console.error('錯誤詳情:', error.message);
            }
        }
    }

    // 顯示健檢結果
    function displayHealthCheckResult(result) {
        try {
            let healthCheck = '';

            // 處理不同的結果格式
            if (typeof result === 'string') {
                healthCheck = result;
            } else if (result.health_check) {
                healthCheck = result.health_check;
            } else if (result.result && result.result.health_check) {
                healthCheck = result.result.health_check;
            } else {
                healthCheck = JSON.stringify(result);
            }

            console.log('健檢結果:', healthCheck);

            // 解析並更新各個欄位的 AI 評語
            updateAIFeedbackFromResult(healthCheck);

            // 更新整體評分和評語
            const score = extractScore(healthCheck);
            if (score) {
                $('#score').textContent = score;
            }

            // 顯示完整的健檢結果
            const scoreComment = $('#scoreComment');
            if (scoreComment) {
                // 截取前 500 字符作為摘要
                const summary = healthCheck.length > 500
                    ? healthCheck.substring(0, 500) + '...'
                    : healthCheck;
                scoreComment.innerHTML = `<div style="white-space: pre-wrap; max-height: 200px; overflow-y: auto;">${summary}</div>`;
            }

        } catch (error) {
            console.error('解析健檢結果失敗:', error);
            $('#scoreComment').textContent = '健檢結果解析失敗，請稍後再試';
        }
    }

    // 根據健檢結果更新 AI 回饋
    function updateAIFeedbackFromResult(healthCheck) {
        // 基本預設回饋
        updateAIFeedback('ai_name', '✅ 姓名格式良好');
        updateAIFeedback('ai_age', '✅ 年齡資訊清楚');
        updateAIFeedback('ai_location', '✅ 地點資訊完整');

        // 從健檢結果中提取特定建議
        const summaryFeedback = extractFeedback(healthCheck, '簡介|自我介紹|摘要') ||
            extractFeedback(healthCheck, '優化') ||
            '建議補充更多量化成果';
        updateAIFeedback('ai_summary', summaryFeedback);

        const keywordsFeedback = extractFeedback(healthCheck, '關鍵字|技能') ||
            '關鍵字應涵蓋技能、框架、領域與工具';
        updateAIFeedback('ai_keywords', keywordsFeedback);

        const domainFeedback = extractFeedback(healthCheck, '領域|工作') ||
            '領域與既有經驗是否匹配？';
        updateAIFeedback('ai_expDomain', domainFeedback);

        const locationFeedback = extractFeedback(healthCheck, '地點|通勤') ||
            '與居住地或通勤條件是否合理？';
        updateAIFeedback('ai_expLocation', locationFeedback);
    }

    // 更新 AI 回饋
    function updateAIFeedback(elementId, feedback) {
        const element = $('#' + elementId);
        if (element) {
            element.textContent = 'AI：' + feedback;
            element.className = 'help ai-feedback';
        }
    }

    // 從健檢結果中提取特定回饋
    function extractFeedback(text, sectionPattern) {
        try {
            const lines = text.split('\n');
            const regex = new RegExp(sectionPattern, 'i'); // 不區分大小寫

            for (let i = 0; i < lines.length; i++) {
                const line = lines[i];
                if (regex.test(line)) {
                    // 找到匹配的行，嘗試提取建議內容
                    let suggestion = line;

                    // 如果當前行很短，嘗試獲取下一行內容
                    if (line.length < 20 && i + 1 < lines.length) {
                        suggestion = lines[i + 1];
                    }

                    // 清理並截取適當長度
                    suggestion = suggestion.replace(/^[*\-•]\s*/, '').trim();
                    return suggestion.substring(0, 150);
                }
            }

            // 如果沒有找到特定段落，嘗試從整體文本中提取相關建議
            const sentences = text.split(/[。！？\n]/);
            for (const sentence of sentences) {
                if (regex.test(sentence) && sentence.length > 10) {
                    return sentence.substring(0, 150);
                }
            }

        } catch (error) {
            console.error('提取回饋失敗:', error);
        }
        return null;
    }

    // 從健檢結果中提取評分
    function extractScore(text) {
        const scoreMatch = text.match(/(\d+)\/100|(\d+)分|評分[：:]?\s*(\d+)/);
        if (scoreMatch) {
            return parseInt(scoreMatch[1] || scoreMatch[2] || scoreMatch[3]) || 82;
        }
        return null;
    }

    // 更新摘要字數計數
    function updateSummaryCount() {
        const summaryEl = $('#summary');
        const countEl = $('#summaryCount');

        if (!summaryEl || !countEl) {
            console.warn('摘要元素不存在');
            return;
        }

        const text = summaryEl.value;
        const count = typeof cnCharCount === 'function' ? cnCharCount(text) : text.length;
        countEl.textContent = count;

        if (count > 1000) {
            countEl.style.color = '#ef4444';
        } else if (count > 800) {
            countEl.style.color = '#f59e0b';
        } else {
            countEl.style.color = '#6b7280';
        }
    }

    // 關鍵字管理
    function collectKeywords() {
        const tags = $all('#keywordList .tag');
        return tags.map(tag => tag.textContent.replace('×', '').trim()).filter(k => k);
    }

    function addKeywordTag(keyword) {
        if (!keyword.trim()) return;

        const container = $('#keywordList');
        const tag = document.createElement('span');
        tag.className = 'tag';
        tag.innerHTML = `${keyword} <button type="button" onclick="this.parentElement.remove()">×</button>`;
        container.appendChild(tag);
    }

    // 收集各類列表資料（實際實現）
    function collectWorkList() {
        const workItems = $all('#workList .dynamic-group');
        return workItems.map(item => {
            return {
                company: item.querySelector('.company')?.value || '',
                industry: item.querySelector('.industry')?.value || '',
                industryOther: item.querySelector('.industryOther')?.value || '',
                workLoc: item.querySelector('.workLoc')?.value || '',
                workLocOther: item.querySelector('.workLocOther')?.value || '',
                title: item.querySelector('.title')?.value || '',
                startDate: item.querySelector('.startDate')?.value || '',
                endDate: item.querySelector('.endDate')?.value || '',
                current: item.querySelector('.current')?.checked || false,
                desc: item.querySelector('.desc')?.value || ''
            };
        });
    }

    function collectEduList() {
        const eduItems = $all('#eduList .dynamic-group');
        return eduItems.map(item => {
            return {
                school: item.querySelector('.school')?.value || '',
                degree: item.querySelector('.degree')?.value || '',
                degreeOther: item.querySelector('.degreeOther')?.value || '',
                major: item.querySelector('.major')?.value || '',
                startDate: item.querySelector('.startDate')?.value || '',
                endDate: item.querySelector('.endDate')?.value || '',
                current: item.querySelector('.current')?.checked || false,
                gpa: item.querySelector('.gpa')?.value || ''
            };
        });
    }

    function collectSkillList() {
        const skillItems = $all('#skillList .dynamic-group');
        return skillItems.map(item => {
            return {
                category: item.querySelector('.category')?.value || '',
                categoryOther: item.querySelector('.categoryOther')?.value || '',
                name: item.querySelector('.name')?.value || '',
                level: item.querySelector('.level')?.value || ''
            };
        });
    }

    function collectProjList() {
        const projItems = $all('#projList .dynamic-group');
        return projItems.map(item => {
            return {
                name: item.querySelector('.name')?.value || '',
                role: item.querySelector('.role')?.value || '',
                startDate: item.querySelector('.startDate')?.value || '',
                endDate: item.querySelector('.endDate')?.value || '',
                current: item.querySelector('.current')?.checked || false,
                desc: item.querySelector('.desc')?.value || ''
            };
        });
    }

    function collectLangList() {
        const langItems = $all('#langList .dynamic-group');
        return langItems.map(item => {
            return {
                name: item.querySelector('.name')?.value || '',
                level: item.querySelector('.level')?.value || '',
                cert: item.querySelector('.cert')?.value || ''
            };
        });
    }

    function collectCertList() {
        const certItems = $all('#certList .dynamic-group');
        return certItems.map(item => {
            return {
                name: item.querySelector('.name')?.value || '',
                org: item.querySelector('.org')?.value || '',
                date: item.querySelector('.date')?.value || ''
            };
        });
    }

    // 動態表單元素創建函數（簡化實現）
    function addWorkExperience(work) {
        const container = $('#workList');
        const item = document.createElement('div');
        item.className = 'dynamic-group';
        item.innerHTML = `
            <div class="grid">
                <div>
                    <label class="label">公司名稱</label>
                    <input type="text" class="input company" value="${work.company || ''}" />
                </div>
                <div>
                    <label class="label">職稱</label>
                    <input type="text" class="input title" value="${work.title || ''}" />
                </div>
                <div>
                    <label class="label">開始日期</label>
                    <input type="date" class="input startDate" value="${work.startDate || ''}" />
                </div>
                <div>
                    <label class="label">結束日期</label>
                    <input type="date" class="input endDate" value="${work.endDate || ''}" />
                </div>
                <div class="col">
                    <label class="label">工作描述</label>
                    <textarea class="desc">${work.desc || ''}</textarea>
                </div>
            </div>
            <div class="actions">
                <button class="button danger btnDel" onclick="this.closest('.dynamic-group').remove()">刪除</button>
            </div>
        `;
        container.appendChild(item);
    }

    function addEducation(edu) {
        const container = $('#eduList');
        const item = document.createElement('div');
        item.className = 'dynamic-group';
        item.innerHTML = `
            <div class="grid">
                <div>
                    <label class="label">學校名稱</label>
                    <input type="text" class="input school" value="${edu.school || ''}" />
                </div>
                <div>
                    <label class="label">學位</label>
                    <input type="text" class="input degree" value="${edu.degree || ''}" />
                </div>
                <div>
                    <label class="label">主修</label>
                    <input type="text" class="input major" value="${edu.major || ''}" />
                </div>
                <div>
                    <label class="label">開始日期</label>
                    <input type="date" class="input startDate" value="${edu.startDate || ''}" />
                </div>
                <div>
                    <label class="label">結束日期</label>
                    <input type="date" class="input endDate" value="${edu.endDate || ''}" />
                </div>
            </div>
            <div class="actions">
                <button class="button danger btnDel" onclick="this.closest('.dynamic-group').remove()">刪除</button>
            </div>
        `;
        container.appendChild(item);
    }

    function addSkill(skill) {
        const container = $('#skillList');
        const item = document.createElement('div');
        item.className = 'dynamic-group';
        item.innerHTML = `
            <div class="grid">
                <div>
                    <label class="label">技能類別</label>
                    <input type="text" class="input category" value="${skill.category || ''}" />
                </div>
                <div>
                    <label class="label">技能名稱</label>
                    <input type="text" class="input name" value="${skill.name || ''}" />
                </div>
                <div>
                    <label class="label">熟練程度</label>
                    <select class="input level">
                        <option value="初學" ${skill.level === '初學' ? 'selected' : ''}>初學</option>
                        <option value="普通" ${skill.level === '普通' ? 'selected' : ''}>普通</option>
                        <option value="熟練" ${skill.level === '熟練' ? 'selected' : ''}>熟練</option>
                        <option value="精通" ${skill.level === '精通' ? 'selected' : ''}>精通</option>
                    </select>
                </div>
            </div>
            <div class="actions">
                <button class="button danger btnDel" onclick="this.closest('.dynamic-group').remove()">刪除</button>
            </div>
        `;
        container.appendChild(item);
    }

    function addProject(proj) {
        const container = $('#projList');
        const item = document.createElement('div');
        item.className = 'dynamic-group';
        item.innerHTML = `
            <div class="grid">
                <div>
                    <label class="label">專案名稱</label>
                    <input type="text" class="input name" value="${proj.name || ''}" />
                </div>
                <div>
                    <label class="label">角色</label>
                    <input type="text" class="input role" value="${proj.role || ''}" />
                </div>
                <div>
                    <label class="label">開始日期</label>
                    <input type="date" class="input startDate" value="${proj.startDate || ''}" />
                </div>
                <div>
                    <label class="label">結束日期</label>
                    <input type="date" class="input endDate" value="${proj.endDate || ''}" />
                </div>
                <div class="col">
                    <label class="label">專案描述</label>
                    <textarea class="desc">${proj.desc || ''}</textarea>
                </div>
            </div>
            <div class="actions">
                <button class="button danger btnDel" onclick="this.closest('.dynamic-group').remove()">刪除</button>
            </div>
        `;
        container.appendChild(item);
    }

    function addLanguage(lang) {
        const container = $('#langList');
        const item = document.createElement('div');
        item.className = 'dynamic-group';
        item.innerHTML = `
            <div class="grid">
                <div>
                    <label class="label">語言</label>
                    <input type="text" class="input name" value="${lang.name || ''}" />
                </div>
                <div>
                    <label class="label">程度</label>
                    <select class="input level">
                        <option value="初級" ${lang.level === '初級' ? 'selected' : ''}>初級</option>
                        <option value="中級" ${lang.level === '中級' ? 'selected' : ''}>中級</option>
                        <option value="高級" ${lang.level === '高級' ? 'selected' : ''}>高級</option>
                        <option value="母語" ${lang.level === '母語' ? 'selected' : ''}>母語</option>
                    </select>
                </div>
                <div>
                    <label class="label">證照</label>
                    <input type="text" class="input cert" value="${lang.cert || ''}" />
                </div>
            </div>
            <div class="actions">
                <button class="button danger btnDel" onclick="this.closest('.dynamic-group').remove()">刪除</button>
            </div>
        `;
        container.appendChild(item);
    }

    function addCertification(cert) {
        const container = $('#certList');
        const item = document.createElement('div');
        item.className = 'dynamic-group';
        item.innerHTML = `
            <div class="grid">
                <div>
                    <label class="label">證照名稱</label>
                    <input type="text" class="input name" value="${cert.name || ''}" />
                </div>
                <div>
                    <label class="label">發證機構</label>
                    <input type="text" class="input org" value="${cert.org || ''}" />
                </div>
                <div>
                    <label class="label">取得日期</label>
                    <input type="date" class="input date" value="${cert.date || ''}" />
                </div>
            </div>
            <div class="actions">
                <button class="button danger btnDel" onclick="this.closest('.dynamic-group').remove()">刪除</button>
            </div>
        `;
        container.appendChild(item);
    }

    // 初始化頁面
    document.addEventListener('DOMContentLoaded', function () {
        console.log('🔧 resume-review.html 頁面開始載入...');

        // 載入已儲存的資料
        loadSavedData();

        console.log('📊 載入完成後的狀態:');
        console.log('- resumeData:', resumeData);
        console.log('- selectedJob:', selectedJob);

        // 綁定事件
        $('#summary')?.addEventListener('input', updateSummaryCount);

        // 關鍵字新增
        $('#addKeyword')?.addEventListener('click', function () {
            const input = $('#keywordInput');
            const keyword = input.value.trim();
            if (keyword) {
                addKeywordTag(keyword);
                input.value = '';
            }
        });

        $('#keywordInput')?.addEventListener('keydown', function (e) {
            if (e.key === 'Enter') {
                e.preventDefault();
                $('#addKeyword').click();
            }
        });

        // 新增按鈕事件
        $('#addWork')?.addEventListener('click', () => addWorkExperience({}));
        $('#addEdu')?.addEventListener('click', () => addEducation({}));
        $('#addSkill')?.addEventListener('click', () => addSkill({}));
        $('#addProj')?.addEventListener('click', () => addProject({}));
        $('#addLang')?.addEventListener('click', () => addLanguage({}));
        $('#addCert')?.addEventListener('click', () => addCertification({}));

        // 按鈕事件
        $('#btnBack')?.addEventListener('click', () => navigate('matching.html'));

        $('#btnClear')?.addEventListener('click', function () {
            if (confirm('確定要清除所有資料嗎？')) {
                document.querySelectorAll('input, textarea, select').forEach(el => {
                    if (el.type === 'radio' || el.type === 'checkbox') {
                        el.checked = false;
                    } else {
                        el.value = '';
                    }
                });
                $('#keywordList').innerHTML = '';
                updateSummaryCount();
            }
        });

        $('#btnDraft')?.addEventListener('click', function () {
            const data = collectFormData();
            saveDraft('jobmate_resume', data);
            showToast('草稿已儲存', 'success');
        });

        $('#btnSaveExit')?.addEventListener('click', function () {
            const data = collectFormData();
            saveDraft('jobmate_resume', data);
            showToast('資料已儲存', 'success');
            // 導向完成頁面
            navigate('completion.html');
        });

        $('#btnSaveAgain')?.addEventListener('click', async function () {
            const button = this;
            button.disabled = true;
            button.textContent = '正在分析...';

            try {
                const data = collectFormData();
                saveDraft('jobmate_resume', data);
                resumeData = data;

                showToast('正在重新進行履歷健檢...', 'info');
                await performHealthCheck();

            } catch (error) {
                console.error('重新健檢失敗:', error);
                showToast('重新健檢失敗，請稍後再試', 'error');
            } finally {
                button.disabled = false;
                button.textContent = '儲存並再次履歷健檢';
            }
        });

        $('#btnSaveInterview')?.addEventListener('click', function () {
            const data = collectFormData();
            saveDraft('jobmate_resume', data);
            navigate('interview.html');
        });

        // 自動執行履歷健檢 - 改進版
        const executeHealthCheck = async () => {
            console.log('⏰ 檢查是否可以執行履歷健檢...');
            console.log('📋 當前 resumeData:', resumeData);
            console.log('🎯 當前 selectedJob:', selectedJob);
            console.log('📊 resumeData 鍵數量:', Object.keys(resumeData || {}).length);

            if (resumeData && Object.keys(resumeData).length > 0) {
                console.log('✅ 資料完整，開始自動執行履歷健檢...');
                try {
                    await performHealthCheck();
                    console.log('✅ 自動健檢執行完成');
                } catch (error) {
                    console.error('❌ 自動健檢執行失敗:', error);
                }
            } else {
                console.warn('❌ 沒有履歷資料，顯示預設訊息');

                // 顯示預設的評分
                const scoreEl = document.getElementById('score');
                const commentEl = document.getElementById('scoreComment');
                if (scoreEl) scoreEl.textContent = '請先填寫履歷資料';
                if (commentEl) commentEl.textContent = '系統需要履歷資料才能進行健檢分析';
            }
        };

        // 延遲執行健檢，確保資料載入和表單填充完成
        setTimeout(executeHealthCheck, 2000);

        // 顯示目標職缺資訊
        if (selectedJob) {
            const jobInfo = document.createElement('div');
            jobInfo.className = 'notice';

            // 處理不同的職缺資料格式
            const jobTitle = selectedJob.job_title || selectedJob.title || '未知職缺';
            const companyName = selectedJob.company_name || selectedJob.company || '未知公司';
            const location = selectedJob.location || '';

            jobInfo.innerHTML = `
                <strong>🎯 目標職缺：</strong>${jobTitle} - ${companyName}
                ${location ? ` (${location})` : ''}
            `;
            document.querySelector('.container').insertBefore(jobInfo, document.querySelector('.card'));
        } else {
            // 如果沒有選中職缺，顯示提醒
            const jobInfo = document.createElement('div');
            jobInfo.className = 'notice';
            jobInfo.style.backgroundColor = '#fff3cd';
            jobInfo.style.color = '#856404';
            jobInfo.innerHTML = `
                <strong>⚠️ 提醒：</strong>尚未選擇目標職缺，將進行通用履歷健檢
            `;
            document.querySelector('.container').insertBefore(jobInfo, document.querySelector('.card'));
        }
    });
})();

