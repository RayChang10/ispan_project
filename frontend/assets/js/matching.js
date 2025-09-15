(function () {
    const { $, $all, navigate, attachSpeechToInput, showToast, loadDraft } = window.JobMate;

    const chat = $('#chat');
    let isLoading = false;

    // API 配置
    const API_BASE_URL = ''; // 使用相對路徑，避免 CORS 問題
    const API_VERSION = 'v1.1'; // 版本標記，用於清除快取
    const API_ENDPOINTS = {
        search: '/api/job_search/search',
        searchByResume: '/api/job_search/search_by_resume',
        analyzeFit: '/api/job_search/analyze_fit'
    };

    function push(role, text, actions) {
        const el = document.createElement('div');
        el.className = 'message ' + role;
        el.innerHTML = `<div class="role">${role === 'user' ? '你' : '系統'}</div><div class="bubble">${text}</div>`;
        chat.appendChild(el);
        if (actions && actions.length) {
            const wrap = document.createElement('div');
            wrap.className = 'actions';
            actions.forEach(a => {
                const b = document.createElement('button');
                b.className = 'button ' + (a.className || 'secondary');
                b.textContent = a.label;
                b.addEventListener('click', a.onClick);
                wrap.appendChild(b);
            });
            chat.appendChild(wrap);
        }
        chat.scrollTop = chat.scrollHeight;
    }

    // 顯示載入狀態
    function showLoading() {
        const loadingEl = document.createElement('div');
        loadingEl.className = 'message assistant';
        loadingEl.id = 'loading-message';
        loadingEl.innerHTML = `
            <div class="role">系統</div>
            <div class="bubble">
                <div style="display: flex; align-items: center; gap: 8px;">
                    <div class="loading-spinner"></div>
                    正在搜尋職缺中...
                </div>
            </div>
        `;
        chat.appendChild(loadingEl);
        chat.scrollTop = chat.scrollHeight;
    }

    // 隱藏載入狀態
    function hideLoading() {
        const loadingEl = $('#loading-message');
        if (loadingEl) {
            loadingEl.remove();
        }
    }

    // API 呼叫函數
    async function callAPI(endpoint, data) {
        try {
            console.log('API 呼叫:', `${API_BASE_URL}${endpoint}`, data);
            
            const response = await fetch(`${API_BASE_URL}${endpoint}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(data)
            });

            console.log('API 回應狀態:', response.status, response.statusText);

            if (!response.ok) {
                const errorText = await response.text();
                console.error('API 錯誤回應:', errorText);
                throw new Error(`HTTP ${response.status}: ${response.statusText} - ${errorText}`);
            }

            const result = await response.json();
            console.log('API 回應資料:', result);
            return result;
        } catch (error) {
            console.error('API 呼叫失敗:', error);
            throw error;
        }
    }

    // 職缺搜尋 API 模式
    async function recommendJobs(query) {
        if (isLoading) return;
        isLoading = true;

        try {
            showLoading();

            // 先嘗試從履歷資料搜尋
            const resumeData = loadDraft('jobmate_resume');
            let result;
            
            try {
                if (resumeData && Object.keys(resumeData).length > 0) {
                    // 使用履歷資料搜尋
                    result = await callAPI(API_ENDPOINTS.searchByResume, {
                        resume_data: resumeData,
                        query: query
                    });
                } else {
                    // 一般搜尋
                    result = await callAPI(API_ENDPOINTS.search, {
                        query: query,
                        top_k: 10
                    });
                }
            } catch (apiError) {
                console.error('API 呼叫失敗:', apiError);
                // 如果履歷搜尋失敗，嘗試一般搜尋
                if (resumeData && Object.keys(resumeData).length > 0) {
                    try {
                        result = await callAPI(API_ENDPOINTS.search, {
                            query: query,
                            top_k: 10
                        });
                    } catch (fallbackError) {
                        console.error('備用搜尋也失敗:', fallbackError);
                        throw fallbackError;
                    }
                } else {
                    throw apiError;
                }
            }

            hideLoading();

            if (result && result.success && result.jobs && Array.isArray(result.jobs) && result.jobs.length > 0) {
                // 轉換 API 回應格式為前端格式
                const items = result.jobs.map(job => ({
                    id: job.job_id || job.id,
                    title: job.job_title || job.title,
                    company: job.company_name || job.company,
                    loc: job.location || job.loc,
                    pay: job.salary_range || job.pay,
                    url: job.job_url || job.url,
                    description: job.description || job.desc,
                    similarity_score: job.similarity_score
                }));

                // 顯示搜尋結果
                let analysisMessage = '';
                if (resumeData && Object.keys(resumeData).length > 0) {
                    analysisMessage = `根據您的履歷背景和「${query}」的要求，我為您分析了目前市場上的相關機會。`;
                } else {
                    analysisMessage = `針對「${query}」的職位需求，我已經為您搜尋並分析了市場上的相關機會。`;
                }
                
                analysisMessage += `\n\n經過 AI 智能分析，我從眾多職缺中為您精選出 ${result.jobs.length} 個最符合條件的優質職缺：`;
                
                // 先顯示分析訊息
                push('assistant', analysisMessage);

                // 然後顯示職缺推薦
                const jobButtons = items.map((job, index) => ({
                    label: `${index + 1}. ${job.title} - ${job.company}`,
                    className: 'primary',
                    onClick: () => selectJob(job, index)
                }));
                
                push('assistant', '根據您的條件，我推薦以下職缺：', jobButtons);

                // 添加引導訊息
                push('assistant', '以上有沒有您感興趣的職缺，👇按下想了解的職缺按鈕來選擇職缺，或輸入新的篩選條件讓我為您搜尋呢？');

                // 如果沒有薪資資訊，顯示提示
                if (items.some(job => !job.pay)) {
                    push('assistant', '💡 點擊職缺查看詳細資訊，找到心儀的職缺後，就可以🖱️點選下一步進入履歷健檢或模擬面試喔!');
                }

            } else {
                console.warn('API 回應格式異常:', result);
                
                if (result && result.jobs && result.jobs.length === 0) {
                    // 沒有找到職缺
                    push('assistant', '抱歉，根據您的條件，目前找不到合適的職缺。您可以試著放寬條件，再問我一次。');
                    
                    // 提供建議搜尋
                    push('assistant', '您可以嘗試以下搜尋條件：', [
                        { label: 'Python 開發工程師', onClick: () => recommendJobs('Python 開發工程師') },
                        { label: '軟體工程師', onClick: () => recommendJobs('軟體工程師') },
                        { label: '資料分析師', onClick: () => recommendJobs('資料分析師') },
                        { label: '前端工程師', onClick: () => recommendJobs('前端工程師') }
                    ]);
                } else {
                    // API 回應格式異常
                    push('assistant', '⚠️ 搜尋結果格式異常，請稍後再試。');
                    console.error('API 回應格式異常:', result);
                }
            }

        } catch (error) {
            hideLoading();
            console.error('職缺搜尋失敗:', error);
            console.error('錯誤詳情:', {
                message: error.message,
                stack: error.stack,
                name: error.name
            });
            
            // 顯示錯誤訊息
            push('assistant', '❌ 搜尋職缺時發生錯誤，請稍後再試。如果問題持續發生，請檢查網路連接或聯繫客服。');
            showToast('職缺搜尋失敗，請稍後再試', 'error');
        } finally {
            isLoading = false;
        }
    }

    let selectedJob = null;
    let selectedJobIndex = -1;
    
    async function selectJob(job, index) {
        selectedJob = job;
        selectedJobIndex = index;
        
        // 儲存選中的職缺到本地儲存
        localStorage.setItem('jobmate_selected_job', JSON.stringify(job));
        localStorage.setItem('jobmate_selected_job_index', index.toString());
        
        push('assistant', `✅ 已選擇職缺：【${job.title}】- ${job.company}`);
        
        // 顯示職缺詳細資訊
        const jobDetails = `
📋 職缺詳情：
• 公司：${job.company || '未提供'}
• 地點：${job.loc || '未提供'}
• 相似度：${job.similarity_score ? (job.similarity_score * 100).toFixed(1) + '%' : '未計算'}
• 連結：${job.url ? '<a href="' + job.url + '" target="_blank">查看職缺</a>' : '未提供'}
        `.trim();
        
        push('assistant', jobDetails);
        
        // 嘗試進行契合度分析
        try {
            const resumeData = loadDraft('jobmate_resume');
            if (resumeData && Object.keys(resumeData).length > 0) {
                push('assistant', '🔍 正在分析契合度，請稍候...');
                
                const fitResult = await callAPI(API_ENDPOINTS.analyzeFit, {
                    resume_data: resumeData,
                    job_data: job
                });
                
                if (fitResult.success) {
                    const analysis = fitResult.analysis || '分析完成';
                    // 只顯示前300字的分析摘要
                    const summary = analysis.length > 300 ? analysis.substring(0, 300) + '...' : analysis;
                    push('assistant', `📊 契合度分析：\n${summary}`);
                } else {
                    push('assistant', '⚠️ 契合度分析失敗，但你仍可以繼續下一步。');
                }
            }
        } catch (error) {
            console.error('契合度分析失敗:', error);
            push('assistant', '⚠️ 契合度分析遇到問題，但你仍可以繼續下一步。');
        }
        
        // 在對話框中顯示下一步行動按鈕
        push('assistant', '🎯 下一步要做什麼？', [
            { label: '📋 履歷健檢', className: 'primary', onClick: () => goToResumeReview() },
            { label: '🎭 虛擬面試', className: 'warning', onClick: () => goToInterview() }
        ]);
    }
    
    function goToResumeReview() {
        if (!selectedJob) {
            showToast('請先選擇一個職缺', 'error');
            return;
        }
        navigate('resume-review.html');
    }
    
    function goToInterview() {
        if (!selectedJob) {
            showToast('請先選擇一個職缺', 'error');
            return;
        }
        navigate('interview.html');
    }

    function send() {
        const v = $('#msg').value.trim();
        if (!v) return;
        push('user', v);
        $('#msg').value = '';
        recommendJobs(v);
    }

    document.addEventListener('DOMContentLoaded', function () {
        $('#send').addEventListener('click', send);
        $('#msg').addEventListener('keydown', e => { if (e.key === 'Enter') send(); });
        attachSpeechToInput($('#mic'), $('#msg'));
        
        // 歡迎訊息和常用搜尋
        push('assistant', '歡迎使用 JobMate360 職缺媒合系統！請描述你想找的職缺條件，或直接點選下方常用需求：', [
            { label: '台北｜後端｜Go｜120萬+', onClick: () => recommendJobs('台北 後端 Go 120萬+') },
            { label: '遠端｜前端｜React｜100萬+', onClick: () => recommendJobs('遠端 前端 React 100萬+') },
            { label: '根據履歷推薦', className: 'secondary', onClick: () => {
                const resumeData = loadDraft('jobmate_resume');
                if (resumeData) {
                    recommendJobs('');
                } else {
                    push('assistant', '請先填寫履歷資料，才能根據履歷推薦職缺。');
                }
            }}
        ]);

        // 底部按鈕事件處理
        $('#toReview')?.addEventListener('click', () => {
            if (!selectedJob) { 
                showToast('請先在對話框內選擇一個職缺', 'error'); 
                return; 
            }
            navigate('resume-review.html');
        });
        
        $('#toInterview')?.addEventListener('click', () => {
            if (!selectedJob) { 
                showToast('請先在對話框內選擇一個職缺', 'error'); 
                return; 
            }
            navigate('interview.html');
        });
    });
})();



