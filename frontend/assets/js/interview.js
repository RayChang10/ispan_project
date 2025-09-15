(function () {
    const { $, navigate, attachSpeechToInput } = window.JobMate;
    const chat = document.getElementById('chat');
    let timerId = null, seconds = 0;
    let interviewModePromptShown = false; // 追蹤面試模式提示是否已顯示
    let interviewEnded = false; // 追蹤面試是否已結束，避免重複處理
    let userCompletedIntro = false; // 追蹤用戶是否明確完成了自我介紹
    let interviewStarted = false; // 追蹤面試是否已經開始（用戶是否按過開始面試按鈕）
    let avatarNotificationShown = false; // 追蹤虛擬人服務不可用通知是否已顯示
    let buttonCheckInterval = null; // 追蹤按鈕檢查的 interval
    let stateSaveInterval = null; // 追蹤狀態保存的 interval
    let syncStatusInterval = null; // 追蹤同步狀態更新的 interval

    // 階段管理器
    const InterviewStage = {
        INITIAL: 'initial',           // 初始狀態
        INTRO_COLLECTION: 'intro',    // 自我介紹收集階段
        INTRO_ANALYSIS: 'intro_analysis',  // 自我介紹分析階段
        INTERVIEW: 'interview',       // 面試階段
        QUESTIONING: 'questioning',   // 問答階段
        FINISHED: 'finished'          // 結束階段
    };

    let currentStage = InterviewStage.INITIAL;

    function fmt(n) { return n.toString().padStart(2, '0'); }

    // 階段管理函數
    function setCurrentStage(stage) {
        console.log(`🔄 階段變更: ${currentStage} -> ${stage}`);
        const previousStage = currentStage;
        currentStage = stage;
        localStorage.setItem('current_interview_stage', stage);

        // 立即保存詳細狀態
        saveInterviewState('running', stage);

        // 檢查是否有暫存的下一題需要顯示（從自介分析階段切換到面試階段時）
        if (previousStage === InterviewStage.INTRO_ANALYSIS &&
            (stage === InterviewStage.INTERVIEW || stage === InterviewStage.QUESTIONING) &&
            window.pendingNextQuestion) {

            console.log('🎯 檢測到階段切換到面試階段，顯示暫存的下一題');
            const pendingQuestion = window.pendingNextQuestion;
            window.pendingNextQuestion = null; // 清除暫存

            // 延遲顯示，確保階段切換完成
            setTimeout(() => {
                const nextQuestionText = `🎯 **下一題已準備好！**

問題：${pendingQuestion.question}
來源：${pendingQuestion.source}

💡 請仔細思考後回答，回答完成後我會進行分析並提供下一題。`;

                push('assistant', nextQuestionText);

                // 顯示快捷按鈕
                setTimeout(() => {
                    if (userCompletedIntro) {
                        renderQuickActions();
                    }
                }, 1000);
            }, 2000);
        }
    }

    function getCurrentStage() {
        return currentStage;
    }

    function isStageAllowed(allowedStages) {
        const allowed = Array.isArray(allowedStages) ? allowedStages : [allowedStages];
        const isAllowed = allowed.includes(currentStage);
        console.log(`🔍 階段檢查: 當前階段=${currentStage}, 允許階段=${allowed.join(',')}, 結果=${isAllowed}`);
        return isAllowed;
    }
    function renderTimer() { $('#timer').textContent = `${fmt(Math.floor(seconds / 60))}:${fmt(seconds % 60)}`; }
    function startTimer() {
        if (timerId) return;
        timerId = setInterval(() => {
            seconds++;
            renderTimer();
            // 每10秒保存一次狀態
            if (seconds % 10 === 0) {
                saveInterviewState('running');
            }
        }, 1000);
    }
    function pauseTimer() { if (!timerId) return; clearInterval(timerId); timerId = null; }
    function resetTimer() { pauseTimer(); seconds = 0; renderTimer(); }

    // Markdown 解析函數
    function parseMarkdown(text) {
        // 先處理換行，保留原始格式
        let html = text
            // 標題
            .replace(/^### (.*$)/gim, '<h3>$1</h3>')
            .replace(/^## (.*$)/gim, '<h2>$1</h2>')
            .replace(/^# (.*$)/gim, '<h1>$1</h1>')
            // 粗體
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            // 斜體（避免與粗體衝突）
            .replace(/(?<!\*)\*([^*]+?)\*(?!\*)/g, '<em>$1</em>')
            // 行內代碼
            .replace(/`(.*?)`/g, '<code>$1</code>')
            // 列表項目
            .replace(/^[\•·] (.*$)/gim, '<li>$1</li>')
            .replace(/^\d+\.\s+(.*$)/gim, '<li>$1</li>')
            // 數字項目（1️⃣ 2️⃣ 等）
            .replace(/^[0-9]️⃣\s+(.*$)/gim, '<li>$1</li>')
            // 雙換行變段落分隔
            .replace(/\n\n/g, '<br><br>')
            // 單換行
            .replace(/\n/g, '<br>');

        // 包裹列表項目為 ul
        html = html.replace(/(<li>.*?<\/li>(\s*<br>\s*<li>.*?<\/li>)*)/g, '<ul>$1</ul>');

        return html;
    }

    // 格式化時間戳記
    function formatTimestamp() {
        const now = new Date();
        return now.toLocaleTimeString('zh-TW', {
            hour: '2-digit',
            minute: '2-digit',
            hour12: false
        });
    }

    // 輸入指示器函數
    function showTypingIndicator() {
        hideTypingIndicator(); // 先移除現有的指示器

        const indicator = document.createElement('div');
        indicator.className = 'typing-indicator';
        indicator.id = 'typing-indicator';
        indicator.innerHTML = `
            <div class="role">面試官</div>
            <div class="bubble">
                <div class="typing-dots">
                    <span></span>
                    <span></span>
                    <span></span>
                </div>
            </div>
        `;

        chat.appendChild(indicator);

        // 平滑顯示
        setTimeout(() => {
            indicator.classList.add('show');
        }, 10);

        // 滾動到底部
        setTimeout(() => {
            chat.scrollTo({
                top: chat.scrollHeight,
                behavior: 'smooth'
            });
        }, 100);
    }

    function hideTypingIndicator() {
        const indicator = document.getElementById('typing-indicator');
        if (indicator) {
            indicator.remove();
        }
    }

    function push(role, text, actions, messageType = 'normal') {
        // 隱藏輸入指示器
        hideTypingIndicator();

        const el = document.createElement('div');
        el.className = `message ${role}`;

        // 添加特殊訊息類型的樣式
        if (messageType !== 'normal') {
            el.className += ` ${messageType}`;
        }

        const roleLabel = role === 'user' ? '你' : '面試官';
        const timestamp = formatTimestamp();

        // 解析 Markdown 格式
        const parsedText = parseMarkdown(text);

        // 左右對齊：assistant 左側有角色標籤、user 右側僅泡泡
        if (role === 'assistant') {
            el.innerHTML = `
                <div class="role">${roleLabel}</div>
                <div class="bubble">${parsedText}</div>
                <div class="timestamp">${timestamp}</div>
            `;
        } else {
            el.innerHTML = `
                <div class="bubble">${parsedText}</div>
                <div class="timestamp">${timestamp}</div>
            `;
        }

        chat.appendChild(el);

        // 添加操作按鈕
        if (actions && actions.length) {
            const wrap = document.createElement('div');
            wrap.className = 'actions';
            actions.forEach(a => {
                const b = document.createElement('button');
                b.className = 'button secondary';
                b.textContent = a.label;
                b.addEventListener('click', a.onClick);
                wrap.appendChild(b);
            });
            chat.appendChild(wrap);
        }

        // 平滑滾動到底部
        setTimeout(() => {
            chat.scrollTo({
                top: chat.scrollHeight,
                behavior: 'smooth'
            });
        }, 100);

        // 保存對話歷史到 localStorage
        saveChatHistory();
    }

    function renderQuickActions() {
        console.log('renderQuickActions 被調用');
        console.log('interviewModePromptShown:', interviewModePromptShown);
        console.log('userCompletedIntro:', userCompletedIntro);
        console.log('interviewEnded:', interviewEnded);
        console.log('currentStage:', currentStage);

        // 階段限制：只有在面試或問答階段才顯示快捷按鈕
        if (!isStageAllowed([InterviewStage.INTERVIEW, InterviewStage.QUESTIONING])) {
            console.log('❌ renderQuickActions 被拒絕：不在允許的階段');
            return;
        }

        // 根據流程.txt：只有在自我介紹真正完成後才進入面試模式階段
        if (userCompletedIntro && !interviewEnded) {
            console.log('✅ 自我介紹已完成，切換到面試階段按鈕配置');
            // 切換到面試階段的按鈕配置
            setButtonsForStage('interview');

            // 檢查是否已經顯示過面試模式提示，避免重複
            if (!interviewModePromptShown) {
                console.log('顯示面試模式已啟動提示');
                // 在聊天區域顯示提示訊息（移除快捷按鈕的說明）
                push('assistant', '🎯 **面試模式已啟動！**\n\n💡 **提示：**\n• 系統會持續出下一題\n• 輸入「結束面試」可完成面試', null, 'system');
                interviewModePromptShown = true; // 標記為已顯示
            }
        } else {
            console.log('❌ 條件不符合，不切換到面試模式，原因:');
            console.log('- interviewModePromptShown:', interviewModePromptShown);
            console.log('- userCompletedIntro:', userCompletedIntro);
            console.log('- interviewEnded:', interviewEnded);

            // 如果自我介紹還沒完成，保持初始狀態
            if (!userCompletedIntro) {
                console.log('🔧 保持初始狀態按鈕配置');
                setButtonsForStage('initial');
            }
        }
    }

    function hideQuickActions() {
        // 現在不再使用面試階段的快捷按鈕（重新開始/結束面試）
        const restartInterviewBtn = $('#restart-interview');
        const endInterviewBtn = $('#end-interview');
        if (restartInterviewBtn) restartInterviewBtn.remove();
        if (endInterviewBtn) endInterviewBtn.remove();
    }

    // 按鈕狀態管理函數
    function setButtonsForStage(stage) {
        console.log("setButtonsForStage 函式被觸發", new Error().stack);
        console.log("setButtonsForStage 參數 stage:", stage);

        const introActions = $('#intro-actions');
        const mainActions = document.getElementById('main-actions');
        const startBtn = $('#start');
        const pauseBtn = $('#pause');
        const stopBtn = $('#stop');
        const restartInterviewBtn = $('#restart-interview');
        const exitInterviewBtn = $('#exit-interview');

        // 按鈕顯示由各階段邏輯決定

        switch (stage) {
            case 'initial':
                // 初始狀態：顯示基本控制按鈕，隱藏面試專用按鈕
                console.log('🔧 設置initial階段按鈕');
                if (introActions) introActions.style.display = 'none';
                if (mainActions) mainActions.style.display = 'flex';

                // 顯示基本控制按鈕，確保開始按鈕文字為「開始面試」
                if (startBtn) {
                    startBtn.style.display = 'inline-block';
                    startBtn.textContent = '開始面試';
                }
                if (pauseBtn) pauseBtn.style.display = 'inline-block';
                if (stopBtn) stopBtn.style.display = 'inline-block';

                // 隱藏面試專用按鈕
                if (restartInterviewBtn) restartInterviewBtn.style.display = 'none';
                if (exitInterviewBtn) exitInterviewBtn.style.display = 'none';
                saveInterviewState('initial', stage);
                break;

            case 'interview':
                // 面試階段：開始按鈕變成重新開始，顯示結束面試按鈕
                console.log('🔧 設置interview階段按鈕');
                if (introActions) introActions.style.display = 'none';
                if (mainActions) mainActions.style.display = 'flex';

                // 開始按鈕變成重新開始
                if (startBtn) {
                    startBtn.style.display = 'inline-block';
                    startBtn.textContent = '重新開始';
                }
                if (pauseBtn) pauseBtn.style.display = 'none';

                // 顯示結束面試按鈕
                if (stopBtn) {
                    stopBtn.style.display = 'inline-block';
                    stopBtn.textContent = '結束面試';
                }

                // 移除左側快捷按鈕（如存在）
                if (restartInterviewBtn) restartInterviewBtn.remove();
                if (exitInterviewBtn) exitInterviewBtn.remove();
                saveInterviewState('interview', stage);
                break;

            case 'questioning':
                // 面試問答階段：開始按鈕變成重新開始，顯示結束面試按鈕
                console.log('🔧 設置questioning階段按鈕');
                if (introActions) introActions.style.display = 'none';
                if (mainActions) mainActions.style.display = 'flex';

                // 開始按鈕變成重新開始
                if (startBtn) {
                    startBtn.style.display = 'inline-block';
                    startBtn.textContent = '重新開始';
                }
                if (pauseBtn) pauseBtn.style.display = 'none';

                // 顯示結束面試按鈕
                if (stopBtn) {
                    stopBtn.style.display = 'inline-block';
                    stopBtn.textContent = '結束面試';
                }

                // 移除左側快捷按鈕（如存在）
                if (restartInterviewBtn) restartInterviewBtn.remove();
                if (exitInterviewBtn) exitInterviewBtn.remove();
                saveInterviewState('questioning', stage);
                break;

            case 'finished':
                // 結束狀態：顯示基本控制按鈕和重新開始按鈕
                console.log('🔧 設置finished階段按鈕');
                if (introActions) introActions.style.display = 'none';
                if (mainActions) mainActions.style.display = 'flex';

                // 顯示基本控制按鈕，開始按鈕文字改為「重新開始」
                if (startBtn) {
                    startBtn.style.display = 'inline-block';
                    startBtn.textContent = '重新開始';
                }
                if (pauseBtn) pauseBtn.style.display = 'inline-block';
                if (stopBtn) stopBtn.style.display = 'inline-block';

                // 移除左側快捷按鈕（如存在）
                if (restartInterviewBtn) restartInterviewBtn.remove();
                if (exitInterviewBtn) exitInterviewBtn.remove();
                saveInterviewState('finished', stage);
                break;
        }
    }

    function resetInterviewModePrompt() {
        // 重置面試模式提示狀態，允許重新顯示
        interviewModePromptShown = false;
    }

    // 統一的重新開始處理函數
    async function handleRestartCommand() {
        console.log("handleRestartCommand 函式被觸發", new Error().stack);

        if (confirm('確定要重新開始面試嗎？所有進度將被重置。')) {
            // 清空輸入框和重置相關狀態
            const msgInput = $('#msg');
            if (msgInput) {
                msgInput.value = '';
                msgInput.disabled = false;
            }

            // 推送用戶訊息
            push('user', '重新開始');

            // 重置前端狀態，確保完全乾淨
            resetTimer();
            resetInterviewModePrompt();

            // ===== 完全清除聊天區域和所有動態元素 =====
            chat.innerHTML = '';

            // 清除所有自我介紹評分面板
            const scoreDisplays = document.querySelectorAll('.intro-score-display');
            scoreDisplays.forEach(element => element.remove());

            // 清除所有面試總結面板
            const summaryDisplays = document.querySelectorAll('.interview-summary-display');
            summaryDisplays.forEach(element => element.remove());

            // 清除所有面試建議面板
            const suggestionsDisplays = document.querySelectorAll('.interview-suggestions-display');
            suggestionsDisplays.forEach(element => element.remove());

            // 清除所有輸入指示器
            const typingIndicators = document.querySelectorAll('.typing-indicator');
            typingIndicators.forEach(element => element.remove());

            // 清除動態添加的樣式元素
            const dynamicStyles = document.querySelectorAll('#intro-score-styles, #interview-summary-styles, #interview-suggestions-styles');
            dynamicStyles.forEach(element => element.remove());

            // 清除所有動作按鈕容器
            const actionContainers = document.querySelectorAll('.actions');
            actionContainers.forEach(element => {
                // 只清除聊天區域內的動作按鈕，保留控制區域的按鈕
                if (chat.contains(element)) {
                    element.remove();
                }
            });

            // 重置所有狀態變數
            interviewModePromptShown = false;
            interviewEnded = false;
            userCompletedIntro = false;
            interviewStarted = false;
            avatarNotificationShown = false;

            // 清除暫存的下一題
            window.pendingNextQuestion = null;

            // 清理所有定期執行的 intervals
            if (buttonCheckInterval) {
                clearInterval(buttonCheckInterval);
                buttonCheckInterval = null;
            }
            if (stateSaveInterval) {
                clearInterval(stateSaveInterval);
                stateSaveInterval = null;
            }
            if (syncStatusInterval) {
                clearInterval(syncStatusInterval);
                syncStatusInterval = null;
            }

            // 重置階段到初始狀態
            setCurrentStage(InterviewStage.INITIAL);
            console.log('🔄 重新開始：階段已重置為', currentStage);

            // 清除保存的面試狀態
            clearInterviewState();

            // 重置頂部徽章狀態
            const badge = document.querySelector('.badge');
            if (badge) {
                badge.textContent = '步驟 3/3';
            }

            // 重新顯示所有控制按鈕
            const startBtn = $('#start');
            const pauseBtn = $('#pause');
            const stopBtn = $('#stop');
            if (startBtn) startBtn.style.display = 'inline-block';
            if (pauseBtn) pauseBtn.style.display = 'inline-block';
            if (stopBtn) stopBtn.style.display = 'inline-block';

            // 設置為初始狀態的按鈕配置
            setButtonsForStage('initial');

            // 顯示純淨的初始狀態訊息
            push('assistant', '👋 歡迎進入 JobMate360 虛擬面試系統！\n\n💬 **使用說明：**\n• 點擊「開始面試」開始正式面試流程\n• 或直接開始自我介紹，我會記錄您的內容\n• 完成後輸入「完成自介」，我會先分析再出題\n\n🎯 **面試流程：**\n1️⃣ 自我介紹階段 → 2️⃣ 面試問答階段 → 3️⃣ 面試總結');

            // 延遲發送後端指令，確保前端完全重置完成
            setTimeout(() => {
                callInterview('重新開始').catch(e => {
                    console.error('重新開始失敗:', e);
                    push('assistant', '重新開始時發生錯誤，請刷新頁面重試。', null, 'error');
                });
            }, 200);
        }
    }

    function renderIntroScore(score, grade, completionRate, analysis, suggestions) {
        console.log('🎯 renderIntroScore 被調用');
        console.log('參數:', { score, grade, completionRate, analysis, suggestions });

        // 階段限制：只有在自我介紹分析階段才能顯示評分
        if (!isStageAllowed(InterviewStage.INTRO_ANALYSIS)) {
            console.log('❌ renderIntroScore 被拒絕：不在允許的階段');
            console.log('當前階段:', currentStage);
            return;
        }

        // 創建評分顯示元素
        const scoreElement = document.createElement('div');
        scoreElement.className = 'intro-score-display';
        scoreElement.innerHTML = `
            <div class="score-header">
                <h3>🎉 自我介紹評分結果</h3>
            </div>
            <div class="score-main">
                <div class="score-number">
                    <span class="score-value">${score}</span>
                    <span class="score-max">/100</span>
                </div>
                <div class="score-grade">${grade}</div>
                <div class="completion-rate">${completionRate}</div>
            </div>
            <div class="score-details">
                <h4>📋 分析摘要</h4>
                <div class="analysis-items">
                    ${analysis.map(item => `<div class="analysis-item">${item}</div>`).join('')}
                </div>
                <h4>🔍 改進建議</h4>
                <div class="suggestion-items">
                    ${suggestions.map(item => `<div class="suggestion-item">${item}</div>`).join('')}
                </div>
            </div>
        `;

        console.log('評分元素已創建:', scoreElement);

        // 添加到聊天區域
        chat.appendChild(scoreElement);
        chat.scrollTop = chat.scrollHeight;

        console.log('評分元素已添加到聊天區域');

        // 保存評分數據到 localStorage
        const scoreData = { score, grade, completionRate, analysis, suggestions };
        saveScoreData(scoreData);

        // 添加樣式
        if (!document.getElementById('intro-score-styles')) {
            const style = document.createElement('style');
            style.id = 'intro-score-styles';
            style.textContent = `
                .intro-score-display {
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    border-radius: 12px;
                    padding: 20px;
                    margin: 15px 0;
                    color: white;
                    box-shadow: 0 8px 32px rgba(0,0,0,0.3);
                }
                .score-header h3 {
                    margin: 0 0 15px 0;
                    text-align: center;
                    font-size: 1.2em;
                }
                .score-main {
                    text-align: center;
                    margin-bottom: 20px;
                }
                .score-number {
                    font-size: 2.5em;
                    font-weight: bold;
                    margin-bottom: 10px;
                }
                .score-value {
                    color: #ffd700;
                }
                .score-max {
                    font-size: 0.6em;
                    opacity: 0.8;
                }
                .score-grade {
                    font-size: 1.3em;
                    font-weight: bold;
                    color: #ffd700;
                    margin-bottom: 5px;
                }
                .completion-rate {
                    font-size: 0.9em;
                    opacity: 0.9;
                }
                .score-details h4 {
                    margin: 15px 0 10px 0;
                    color: #ffd700;
                    font-size: 1.1em;
                }
                .analysis-items, .suggestion-items {
                    margin-bottom: 15px;
                }
                .analysis-item, .suggestion-item {
                    background: rgba(255,255,255,0.1);
                    padding: 8px 12px;
                    margin: 5px 0;
                    border-radius: 6px;
                    font-size: 0.9em;
                    line-height: 1.4;
                }
            `;
            document.head.appendChild(style);
            console.log('樣式已添加');
        }

        console.log('🎯 renderIntroScore 完成');
    }

    function renderInterviewSummary(summaryData) {
        console.log('🎯 renderInterviewSummary 被調用');
        console.log('參數:', summaryData);

        if (!summaryData || !summaryData.summary) {
            console.log('沒有面試總結數據');
            return;
        }

        // 創建面試總結顯示元素
        const summaryElement = document.createElement('div');
        summaryElement.className = 'interview-summary-display';

        // 將總結文本轉換為 HTML 格式
        const summaryHtml = summaryData.summary
            .replace(/🎯 \*\*(.*?)\*\*/g, '<h3>🎯 $1</h3>')
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/(\d+\.\s.*?)(?=\n)/g, '<li>$1</li>')
            .replace(/•\s(.*?)(?=\n|$)/g, '<li>$1</li>')
            .replace(/✅(.*?)(?=\n|$)/g, '<div class="summary-item success">✅$1</div>')
            .replace(/📝(.*?)(?=\n|$)/g, '<div class="summary-item info">📝$1</div>')
            .replace(/📈(.*?)(?=\n|$)/g, '<div class="summary-item metric">📈$1</div>')
            .replace(/🎯(.*?)(?=\n|$)/g, '<div class="summary-item target">🎯$1</div>')
            .replace(/\n\n/g, '<br><br>')
            .replace(/\n/g, '<br>');

        summaryElement.innerHTML = `
            <div class="summary-header">
                <h2>🏁 面試結語</h2>
            </div>
            <div class="summary-content">
                ${summaryHtml}
            </div>
            <div class="summary-footer">
                <p>🌟 感謝您參與本次模擬面試！</p>
                <p>💪 繼續努力，您一定會在真正的面試中表現出色！</p>
            </div>
        `;

        console.log('面試總結元素已創建:', summaryElement);

        // 添加到聊天區域
        chat.appendChild(summaryElement);
        chat.scrollTop = chat.scrollHeight;

        console.log('面試總結元素已添加到聊天區域');

        // 添加樣式
        if (!document.getElementById('interview-summary-styles')) {
            const style = document.createElement('style');
            style.id = 'interview-summary-styles';
            style.textContent = `
                .interview-summary-display {
                    background: linear-gradient(135deg, #ff6b6b 0%, #ee5a52 100%);
                    border-radius: 15px;
                    padding: 25px;
                    margin: 20px 0;
                    color: white;
                    box-shadow: 0 10px 40px rgba(0,0,0,0.3);
                    animation: fadeIn 0.5s ease-in;
                }
                @keyframes fadeIn {
                    from { opacity: 0; transform: translateY(20px); }
                    to { opacity: 1; transform: translateY(0); }
                }
                .summary-header h2 {
                    margin: 0 0 20px 0;
                    text-align: center;
                    font-size: 1.5em;
                    font-weight: bold;
                }
                .summary-content {
                    margin-bottom: 20px;
                    line-height: 1.6;
                }
                .summary-content h3 {
                    color: #ffd700;
                    margin: 15px 0 10px 0;
                    font-size: 1.2em;
                }
                .summary-content strong {
                    color: #ffd700;
                }
                .summary-item {
                    background: rgba(255,255,255,0.1);
                    padding: 10px 15px;
                    margin: 8px 0;
                    border-radius: 8px;
                    border-left: 4px solid;
                }
                .summary-item.success {
                    border-left-color: #4caf50;
                }
                .summary-item.info {
                    border-left-color: #2196f3;
                }
                .summary-item.metric {
                    border-left-color: #ff9800;
                }
                .summary-item.target {
                    border-left-color: #e91e63;
                }
                .summary-content li {
                    background: rgba(255,255,255,0.1);
                    padding: 8px 12px;
                    margin: 5px 0;
                    border-radius: 6px;
                    list-style: none;
                }
                .summary-footer {
                    text-align: center;
                    padding-top: 15px;
                    border-top: 1px solid rgba(255,255,255,0.3);
                }
                .summary-footer p {
                    margin: 5px 0;
                    font-weight: bold;
                }
            `;
            document.head.appendChild(style);
            console.log('面試總結樣式已添加');
        }

        console.log('🎯 renderInterviewSummary 完成');
    }

    // 生成面試建議
    function generateInterviewSuggestions() {
        console.log('🎯 generateInterviewSuggestions 被調用');

        // 獲取自我介紹評分數據
        const introScoreData = getScoreData();
        console.log('自我介紹評分數據:', introScoreData);

        // 從聊天記錄中分析面試表現
        const chatMessages = chat.querySelectorAll('.message.assistant');
        let questionCount = 0;
        let hasAnalysisResults = false;

        chatMessages.forEach(msg => {
            const content = msg.textContent;
            if (content.includes('🎯') && (content.includes('問題') || content.includes('Question'))) {
                questionCount++;
            }
            if (content.includes('📊 分析結果') || content.includes('評分：')) {
                hasAnalysisResults = true;
            }
        });

        console.log(`檢測到 ${questionCount} 個面試問題，分析結果: ${hasAnalysisResults}`);

        // 生成建議內容
        let suggestions = {
            introSuggestions: [],
            answerSuggestions: [],
            generalSuggestions: []
        };

        // 自我介紹建議
        if (introScoreData) {
            const score = introScoreData.score || 0;
            if (score < 60) {
                suggestions.introSuggestions.push('加強自我介紹的結構性，建議使用「背景-經歷-技能-目標」的框架');
                suggestions.introSuggestions.push('增加具體的工作成果和數據來支撐您的能力描述');
                suggestions.introSuggestions.push('練習在2-3分鐘內簡潔有力地介紹自己');
            } else if (score < 80) {
                suggestions.introSuggestions.push('自我介紹基礎良好，可以增加更多個人特色和差異化優勢');
                suggestions.introSuggestions.push('嘗試加入一些具體的專案經驗或解決問題的案例');
            } else {
                suggestions.introSuggestions.push('自我介紹表現優秀！繼續保持這種結構化和具體化的表達方式');
            }

            // 根據具體分析和建議添加更多建議
            if (introScoreData.suggestions && introScoreData.suggestions.length > 0) {
                suggestions.introSuggestions.push(...introScoreData.suggestions);
            }
        } else {
            suggestions.introSuggestions.push('建議多練習自我介紹，確保能夠簡潔清晰地表達個人背景和優勢');
        }

        // 回答問題建議
        if (questionCount > 0) {
            suggestions.answerSuggestions.push('回答技術問題時，建議使用STAR法則（情境-任務-行動-結果）');
            suggestions.answerSuggestions.push('準備一些常見問題的回答模板，但要避免過於制式化');
            suggestions.answerSuggestions.push('多練習將理論知識與實際經驗結合的表達方式');

            if (hasAnalysisResults) {
                suggestions.answerSuggestions.push('注意回答的完整性和邏輯性，確保涵蓋問題的核心要點');
                suggestions.answerSuggestions.push('增加具體的技術細節和實作經驗分享');
            }
        } else {
            suggestions.answerSuggestions.push('建議多練習回答技術問題，準備常見的面試題目');
        }

        // 通用建議
        suggestions.generalSuggestions = [
            '面試前充分了解公司背景和職位要求',
            '準備幾個有深度的問題來詢問面試官',
            '保持自信和積極的態度，展現學習熱忱',
            '定期練習面試技巧，可以請朋友或同事協助模擬',
            '建立個人作品集或技術部落格來展示專業能力'
        ];

        return suggestions;
    }

    // 渲染面試建議
    function renderInterviewSuggestions(suggestions) {
        console.log('🎯 renderInterviewSuggestions 被調用');
        console.log('建議數據:', suggestions);

        const suggestionsElement = document.createElement('div');
        suggestionsElement.className = 'interview-suggestions-display';

        let suggestionsHtml = `
            <div class="suggestions-header">
                <h3>💡 個人化面試建議</h3>
                <p>基於您的表現，我們為您準備了以下改進建議：</p>
            </div>
        `;

        // 自我介紹建議
        if (suggestions.introSuggestions.length > 0) {
            suggestionsHtml += `
                <div class="suggestion-section">
                    <h4>🎯 自我介紹改進建議</h4>
                    <ul>
                        ${suggestions.introSuggestions.map(suggestion => `<li>${suggestion}</li>`).join('')}
                    </ul>
                </div>
            `;
        }

        // 回答問題建議
        if (suggestions.answerSuggestions.length > 0) {
            suggestionsHtml += `
                <div class="suggestion-section">
                    <h4>📝 問題回答技巧</h4>
                    <ul>
                        ${suggestions.answerSuggestions.map(suggestion => `<li>${suggestion}</li>`).join('')}
                    </ul>
                </div>
            `;
        }

        // 通用建議
        if (suggestions.generalSuggestions.length > 0) {
            suggestionsHtml += `
                <div class="suggestion-section">
                    <h4>🚀 通用面試建議</h4>
                    <ul>
                        ${suggestions.generalSuggestions.map(suggestion => `<li>${suggestion}</li>`).join('')}
                    </ul>
                </div>
            `;
        }

        suggestionsHtml += `
            <div class="suggestions-footer">
                <p>🎉 繼續加油！每次面試都是學習和成長的機會。</p>
            </div>
        `;

        suggestionsElement.innerHTML = suggestionsHtml;
        chat.appendChild(suggestionsElement);

        // 滾動到底部
        setTimeout(() => {
            chat.scrollTo({
                top: chat.scrollHeight,
                behavior: 'smooth'
            });
        }, 100);

        // 添加樣式
        if (!document.getElementById('interview-suggestions-styles')) {
            const style = document.createElement('style');
            style.id = 'interview-suggestions-styles';
            style.textContent = `
                .interview-suggestions-display {
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    border-radius: 15px;
                    padding: 25px;
                    margin: 20px 0;
                    color: white;
                    box-shadow: 0 10px 40px rgba(0,0,0,0.3);
                    animation: fadeIn 0.5s ease-in;
                }
                
                .suggestions-header h3 {
                    margin: 0 0 10px 0;
                    font-size: 1.4em;
                    font-weight: bold;
                }
                
                .suggestions-header p {
                    margin: 0 0 20px 0;
                    opacity: 0.9;
                }
                
                .suggestion-section {
                    margin: 20px 0;
                    padding: 15px;
                    background: rgba(255, 255, 255, 0.1);
                    border-radius: 10px;
                    border-left: 4px solid rgba(255, 255, 255, 0.3);
                }
                
                .suggestion-section h4 {
                    margin: 0 0 15px 0;
                    font-size: 1.1em;
                    font-weight: bold;
                }
                
                .suggestion-section ul {
                    margin: 0;
                    padding-left: 20px;
                }
                
                .suggestion-section li {
                    margin: 8px 0;
                    line-height: 1.5;
                }
                
                .suggestions-footer {
                    text-align: center;
                    margin-top: 20px;
                    padding: 15px;
                    background: rgba(255, 255, 255, 0.1);
                    border-radius: 10px;
                }
                
                .suggestions-footer p {
                    margin: 0;
                    font-weight: bold;
                    font-size: 1.1em;
                }
            `;
            document.head.appendChild(style);
        }

        console.log('面試建議元素已添加到聊天區域');
    }

    // 生成前端面試總結
    function generateFrontendSummary() {
        console.log('🎯 generateFrontendSummary 被調用');

        // 獲取自我介紹評分數據
        const introScoreData = getScoreData();

        // 分析聊天記錄
        const chatMessages = chat.querySelectorAll('.message');
        let questionCount = 0;
        let userAnswerCount = 0;
        let hasAnalysisResults = false;

        chatMessages.forEach(msg => {
            const content = msg.textContent;
            if (msg.classList.contains('assistant')) {
                if (content.includes('🎯') && (content.includes('問題') || content.includes('Question'))) {
                    questionCount++;
                }
                if (content.includes('📊 分析結果') || content.includes('評分：')) {
                    hasAnalysisResults = true;
                }
            } else if (msg.classList.contains('user')) {
                // 排除系統指令
                if (!content.includes('完成自介') && !content.includes('結束面試') && !content.includes('重新開始')) {
                    userAnswerCount++;
                }
            }
        });

        // 計算面試時長
        const interviewDuration = Math.floor(seconds / 60);

        // 生成動態總結
        let summaryText = '🎯 **面試表現總結**\n\n';

        // 基本統計
        summaryText += '📊 **基本統計**\n';
        summaryText += `• 面試時長：${interviewDuration} 分鐘\n`;
        summaryText += `• 回答問題數：${questionCount} 題\n`;
        summaryText += `• 互動次數：${userAnswerCount} 次\n\n`;

        // 自我介紹表現
        if (introScoreData) {
            summaryText += '🎯 **自我介紹表現**\n';
            summaryText += `• 評分：${introScoreData.score}/100\n`;
            summaryText += `• 等級：${introScoreData.grade || '良好'}\n`;
            summaryText += `• 完整度：${introScoreData.completionRate || '80'}%\n\n`;
        }

        // 問答表現
        summaryText += '💬 **問答表現**\n';
        if (questionCount > 0) {
            if (hasAnalysisResults) {
                summaryText += '• 積極參與面試問答環節\n';
                summaryText += '• 所有回答都有進行分析評估\n';
            } else {
                summaryText += '• 參與了面試問答環節\n';
                summaryText += '• 展現了良好的溝通意願\n';
            }

            if (questionCount >= 3) {
                summaryText += '• 回答問題數量充足，展現全面性\n';
            } else if (questionCount >= 1) {
                summaryText += '• 回答了基本問題，建議增加更多練習\n';
            }
        } else {
            summaryText += '• 主要進行了自我介紹環節\n';
            summaryText += '• 建議下次嘗試完整的問答流程\n';
        }

        summaryText += '\n📈 **整體評價**\n';

        // 根據表現生成動態評價
        let overallScore = 0;
        if (introScoreData) overallScore += Math.min(introScoreData.score || 0, 40);
        if (questionCount > 0) overallScore += 30;
        if (hasAnalysisResults) overallScore += 20;
        if (interviewDuration >= 5) overallScore += 10;

        if (overallScore >= 80) {
            summaryText += '• ✅ 表現優秀！具備良好的面試基礎\n';
            summaryText += '• ✅ 展現了積極的學習態度\n';
            summaryText += '• ✅ 建議繼續保持並精進技能\n';
        } else if (overallScore >= 60) {
            summaryText += '• 📝 表現良好，有進步空間\n';
            summaryText += '• 📝 建議加強特定領域的準備\n';
            summaryText += '• 📝 多練習可以獲得更好效果\n';
        } else {
            summaryText += '• 💡 這是很好的開始！\n';
            summaryText += '• 💡 建議多練習自我介紹和問答\n';
            summaryText += '• 💡 每次練習都是寶貴的學習機會\n';
        }

        return { summary: summaryText };
    }

    // ---- 與後端面試 API 串接 ----
    let INTERVIEW_API = '';
    async function resolveInterviewApi() {
        if (INTERVIEW_API) return INTERVIEW_API;
        const candidates = [
            '/api/interview',
            'http://localhost:5000/api/interview',
            'http://localhost:8001/api/interview',
            'http://localhost:8080/api/interview'
        ];
        for (const url of candidates) {
            try {
                const res = await fetch(url, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ message: 'ping', user_id: 'default_user' })
                });
                if (res.ok || res.status === 400) { INTERVIEW_API = url; return INTERVIEW_API; }
            } catch (e) { /* ignore */ }
        }
        INTERVIEW_API = '/api/interview';
        return INTERVIEW_API;
    }

    async function callInterview(message) {
        const endpoint = await resolveInterviewApi();
        const userId = localStorage.getItem('jobmate_user_id') || 'default_user';
        const res = await fetch(endpoint, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message, user_id: userId })
        });
        let data = {};
        try { data = await res.json(); } catch (_) { }

        // 返回完整的響應數據，而不只是文本
        return data;
    }

    // 覆蓋 send，改為呼叫後端
    async function userSend(text) {
        const v = (text ?? $('#msg').value).trim(); if (!v) return;

        // 特殊處理：檢查是否為重新開始指令
        if (v === '重新開始' || v === '重新开始' || v.toLowerCase() === 'restart') {
            handleRestartCommand();
            return;
        }

        push('user', v);
        if (!text) $('#msg').value = '';

        // 檢查面試是否已經開始
        if (!interviewStarted) {
            // 面試還沒開始，統一回覆請按開始面試
            push('assistant', '請按「開始面試」按鈕開始面試流程。');
            return;
        }

        // 顯示輸入指示器
        showTypingIndicator();

        try {
            const response = await callInterview(v);

            // 處理響應數據
            let reply = '';
            let introScoreData = null;
            let interviewSummary = null;
            let nextQuestionData = null;

            if (response && response.data) {
                reply = response.data.response || '';
                introScoreData = response.data.intro_score_result;
                interviewSummary = response.data.interview_summary;
                nextQuestionData = response.data.next_question;  // 獲取下一題數據
                console.log('📊 響應數據:', response.data);
                console.log('📝 回應內容:', reply);
                console.log('📋 評分數據:', introScoreData);
                console.log('🏁 面試總結:', interviewSummary);
                console.log('🎯 下一題數據:', nextQuestionData);
            } else if (response && response.result) {
                reply = response.result;
                console.log('📊 響應結果:', response.result);
            } else if (response && response.message) {
                reply = response.message;
                console.log('📊 響應訊息:', response.message);
            } else {
                reply = '系統忙碌中，請稍後再試。';
                console.log('⚠️ 無效響應:', response);
            }

            // 檢查是否面試結束，如果是則顯示面試總結
            // 只要檢測到面試結束狀態就觸發（不強制要求總結數據）
            if (response.data && response.data.current_state === 'finished' && !interviewEnded) {
                console.log('檢測到面試結束，準備顯示總結');
                interviewEnded = true; // 標記面試已結束

                // 先顯示簡單的結束訊息
                push('assistant', '🏁 **面試已結束！**\n\n正在生成您的面試總結...');

                // 顯示面試總結（如果有的話）
                setTimeout(() => {
                    if (interviewSummary) {
                        renderInterviewSummary(interviewSummary);
                    } else {
                        // 如果沒有後端總結，生成前端總結
                        const frontendSummary = generateFrontendSummary();
                        renderInterviewSummary(frontendSummary);
                    }

                    // 在總結顯示後，生成並顯示個人化建議
                    setTimeout(() => {
                        const suggestions = generateInterviewSuggestions();
                        renderInterviewSuggestions(suggestions);

                        // 在建議顯示後，提供跳轉選項
                        setTimeout(() => {
                            push('assistant', '💡 **面試已完成！**\n\n🎉 感謝您的參與！\n\n📋 **接下來您可以：**\n• 輸入「重新開始」開始新的面試\n• 或等待 8 秒後自動跳轉到完成頁面');

                            // 8秒後自動跳轉到完成頁面（延長時間讓用戶閱讀建議）
                            setTimeout(() => {
                                navigate('completion.html');
                            }, 8000);
                        }, 2000); // 讓用戶有時間閱讀建議
                    }, 3000); // 讓用戶有足夠時間閱讀總結
                }, 1000); // 延遲1秒顯示總結，讓用戶看到結束訊息

                // 設置為結束狀態
                setButtonsForStage('finished');

                return; // 跳過後續處理
            }

            // 檢查是否自我介紹已完成並顯示評分
            if (text === '開始面試' ||
                text === '完成自我介紹' ||
                text === '完成自介') {

                // 設置為自我介紹分析階段
                setCurrentStage(InterviewStage.INTRO_ANALYSIS);

                // 先不標記完成，等待後端回應後再決定
                // userCompletedIntro = true; // 移到後端回應處理中

                // 重置面試結束標記，因為開始新的面試流程
                interviewEnded = false;

                // 重置頂部徽章狀態，從「面試完成」改回「步驟 3/3」
                const badge = document.querySelector('.badge');
                if (badge) {
                    badge.textContent = '步驟 3/3';
                }

                console.log('檢測到自我介紹完成指令，檢查評分數據');
                console.log('introScoreData:', introScoreData);
                console.log('response.data.intro_score_result:', response.data?.intro_score_result);

                // 檢查是否有結構化評分數據
                if (introScoreData || (response.data && response.data.intro_score_result)) {
                    console.log('自我介紹評分完成，顯示結果');

                    const scoreData = introScoreData || response.data.intro_score_result;
                    console.log('評分數據:', scoreData);

                    // 只有在有評分數據時才標記自我介紹完成
                    userCompletedIntro = true;

                    // 顯示自我介紹評分結果
                    renderIntroScore(
                        scoreData.score,
                        scoreData.grade,
                        scoreData.completion_rate,
                        scoreData.analysis || [],
                        scoreData.suggestions || []
                    );

                    // 評分顯示完成後，轉換到面試階段
                    setTimeout(() => {
                        setCurrentStage(InterviewStage.QUESTIONING);
                        setButtonsForStage('questioning');
                        // 保存狀態變更
                        saveInterviewState('questioning', 'questioning');
                    }, 1000);

                    // 顯示完成提示
                    push('assistant', '🎉 **自我介紹分析完成！**\n\n📊 評分結果已顯示在下方面板中\n\n🎯 **現在進入面試模式！**', null, 'success');

                    // 檢查回應中是否包含面試題目，如果有則延遲顯示
                    if (reply && reply.includes('🎯 面試問題')) {
                        console.log('檢測到面試題目，延遲顯示以確保正確順序');
                        // 延遲顯示面試題目，等待「面試模式已啟動！」提示先顯示
                        setTimeout(() => {
                            // 提取面試題目部分
                            const questionMatch = reply.match(/🎯 面試問題[\s\S]*/);
                            if (questionMatch) {
                                const questionText = questionMatch[0].trim();
                                console.log('顯示面試題目:', questionText);
                                // 階段檢查：只在適當階段顯示面試題目
                                if (isStageAllowed([InterviewStage.INTERVIEW, InterviewStage.QUESTIONING])) {
                                    push('assistant', questionText);
                                } else {
                                    console.log('❌ 階段不符，不顯示面試題目');
                                }
                            } else {
                                // 如果正則表達式失敗，直接顯示完整回應
                                console.log('正則表達式提取失敗，顯示完整回應');
                                // 階段檢查：只在適當階段顯示
                                if (isStageAllowed([InterviewStage.INTERVIEW, InterviewStage.QUESTIONING])) {
                                    push('assistant', reply);
                                } else {
                                    console.log('❌ 階段不符，不顯示完整回應');
                                }
                            }
                        }, 3500); // 3.5秒後顯示，確保在「面試模式已啟動！」之後
                    } else if (reply && reply.includes('面試問題')) {
                        // 備用檢查：如果沒有 🎯 符號但有「面試問題」文字
                        console.log('檢測到面試問題（備用檢查），延遲顯示');
                        setTimeout(() => {
                            // 階段檢查：只在適當階段顯示
                            if (isStageAllowed([InterviewStage.INTERVIEW, InterviewStage.QUESTIONING])) {
                                push('assistant', reply);
                            } else {
                                console.log('❌ 階段不符，不顯示面試問題');
                            }
                        }, 3500); // 3.5秒後顯示
                    }

                    // 延遲一下再顯示快捷按鈕，讓用戶先看到評分
                    setTimeout(() => {
                        if (userCompletedIntro) {
                            renderQuickActions();
                        }
                    }, 3000); // 3秒後顯示快捷按鈕

                    // 跳過後續的通用檢查，避免重複推送
                    return;
                } else {
                    console.log('沒有評分數據，等待後端處理');
                }
            }

            // 條件檢查：根據流程.txt，只在用戶明確完成自我介紹時才顯示評分數據
            if (response.data && response.data.intro_score_result && !introScoreData &&
                (text === '完成自我介紹' || text === '完成自介' || text === '開始面試' ||
                    (response.data.stage === 'questioning' && response.data.status === 'intro_finished'))) {
                console.log('✅ 檢測到自我介紹完成並有評分數據，顯示評分面板');
                const scoreData = response.data.intro_score_result;
                console.log('評分數據:', scoreData);
                renderIntroScore(
                    scoreData.score,
                    scoreData.grade,
                    scoreData.completion_rate,
                    scoreData.analysis || [],
                    scoreData.suggestions || []
                );

                // 根據流程.txt第59行：給完建議後，馬上進入面試模式階段
                userCompletedIntro = true;
                setTimeout(() => {
                    setCurrentStage(InterviewStage.QUESTIONING);
                    setButtonsForStage('questioning');
                }, 1000);
                console.log('🎯 已設置為questioning階段，按鈕應該顯示');
            } else {
                console.log('❌ 條件不符合，不顯示評分面板');
                console.log('- 用戶輸入:', text);
                console.log('- 有評分數據:', !!(response.data && response.data.intro_score_result));
                console.log('- introScoreData為空:', !introScoreData);
            }

            // 推送後端回應（如果還沒有推送過的話）
            // 避免重複推送面試結束相關的訊息
            // 階段限制：在自我介紹收集與分析階段都不推送面試評分內容
            if (reply &&
                !reply.includes('自我介紹分析完成') &&
                !reply.includes('面試已結束') &&
                !interviewEnded) {

                const isIntroStage = (currentStage === InterviewStage.INTRO_COLLECTION || currentStage === InterviewStage.INTRO_ANALYSIS);
                const containsScore = (
                    reply.includes('📊 分析結果') ||
                    reply.includes('評分：') ||
                    reply.includes('相似度：') ||
                    reply.includes('標準答案：') ||
                    reply.includes('🔍 具體差異：')
                );

                if (isIntroStage && containsScore) {
                    console.log('❌ 阻止在自我介紹階段顯示面試評分內容');
                    console.log('當前階段:', currentStage);
                    console.log('回應內容包含面試評分，已阻止顯示');
                } else {
                    push('assistant', reply);
                }
            }

            // 如果有下一題數據，在分析結果後單獨顯示
            if (nextQuestionData && nextQuestionData.question) {
                // 強化階段檢查：只在面試或問答階段顯示下一題
                // 特別注意：自介分析完成時後端會同時返回 intro_score_result 和 next_question
                // 此時應該等待階段切換到 INTERVIEW 後再顯示題目
                const isValidStageForQuestion = (currentStage === InterviewStage.INTERVIEW || currentStage === InterviewStage.QUESTIONING);

                if (!isValidStageForQuestion) {
                    console.log('❌ 階段不符，不顯示下一題');
                    console.log('當前階段:', currentStage);
                    console.log('需要的階段: INTERVIEW 或 QUESTIONING');

                    // 如果是自介分析階段收到下一題，暫存起來等階段切換後再顯示
                    if (currentStage === InterviewStage.INTRO_ANALYSIS) {
                        console.log('💾 自介分析階段收到下一題，暫存等待階段切換');
                        window.pendingNextQuestion = nextQuestionData;
                    }
                    return; // 直接返回，不顯示下一題
                }

                // 延遲一下再顯示下一題，讓用戶先看到分析結果
                setTimeout(() => {
                    const nextQuestionText = `🎯 **下一題已準備好！**

問題：${nextQuestionData.question}
來源：${nextQuestionData.source}

請回答這個問題，然後使用 analyze_answer 功能來分析您的回答。`;

                    push('assistant', nextQuestionText);

                    // 在下一題顯示後，顯示快捷按鈕
                    setTimeout(() => {
                        if (userCompletedIntro) {
                            renderQuickActions();
                        }
                    }, 1000);

                }, 3000); // 3秒後顯示下一題，讓用戶有足夠時間閱讀分析結果
            } else {
                // 如果沒有下一題，直接顯示快捷按鈕
                setTimeout(() => {
                    if (userCompletedIntro) {
                        renderQuickActions();
                    }
                }, 2000);
            }

            // 優先檢查是否自我介紹內容不足，避免誤觸發其他邏輯
            if (reply.includes('自我介紹內容不足') ||
                reply.includes('intro_incomplete') ||
                reply.includes('自我介紹內容為空') ||
                reply.includes('請繼續完善')) {
                // 自我介紹內容不足，不顯示快捷按鈕，繼續收集階段
                console.log('自我介紹內容不足，繼續收集階段');
                console.log('當前 userCompletedIntro 狀態:', userCompletedIntro);
                // 確保自我介紹未完成狀態
                userCompletedIntro = false;
                // 保持自我介紹階段按鈕可見
                const introActions = $('#intro-actions');
                if (introActions) introActions.style.display = 'block';
                // 隱藏面試階段按鈕
                hideQuickActions();
                // 不顯示額外的對話框，只顯示後端返回的原始訊息
                // 移除自動推送的「繼續收集自我介紹內容」對話框
                return; // 提前返回，避免執行後續邏輯
            }

            // 檢查是否自我介紹已完成，如果是則顯示快捷按鈕
            // 只有在用戶明確完成自我介紹後才進入面試模式
            if (userCompletedIntro &&
                (reply.includes('現在進入面試模式') ||
                    reply.includes('status') && reply.includes('intro_finished') ||
                    reply.includes('stage') && reply.includes('questioning') ||
                    reply.includes('面試問題') ||
                    reply.includes('請回答以下問題')) &&
                !interviewModePromptShown) { // 使用全域變數檢查

                // 延遲顯示快捷按鈕，避免與評分結果同時出現
                setTimeout(() => {
                    renderQuickActions();
                }, 1000);
            }

            // 檢查是否在自我介紹收集階段
            if (reply.includes('自我介紹內容已記錄') ||
                reply.includes('已記錄您的自我介紹') ||
                reply.includes('繼續完善')) {
                // 顯示收集進度提示
                console.log('自我介紹收集階段');
                // 確保自我介紹階段按鈕可見
                const introActions = $('#intro-actions');
                if (introActions) introActions.style.display = 'block';
                // 隱藏面試階段按鈕
                hideQuickActions();
            }

            // 通用檢查：如果響應中沒有明確指示階段變化，保持當前按鈕狀態
            if (!reply.includes('現在進入面試模式') &&
                !reply.includes('面試問題') &&
                !reply.includes('請回答以下問題') &&
                !reply.includes('自我介紹內容不足') &&
                !reply.includes('intro_incomplete') &&
                !reply.includes('自我介紹內容為空') &&
                !reply.includes('請繼續完善') &&
                !reply.includes('自我介紹內容已記錄') &&
                !reply.includes('已記錄您的自我介紹') &&
                !reply.includes('繼續完善')) {
                // 如果沒有明確的階段指示，檢查響應狀態
                if (response.data && response.data.current_state === 'intro') {
                    // 仍在自我介紹階段，保持按鈕可見
                    const introActions = $('#intro-actions');
                    if (introActions) introActions.style.display = 'block';
                    hideQuickActions();
                }
            }
        } catch (e) {
            push('assistant', '❌ 呼叫面試服務失敗，請稍後再試。', null, 'error');
            console.error('面試服務錯誤:', e);
        }
    }

    // 初始化面試狀態（頁面載入時使用）
    async function initializeInterviewState() {
        try {
            console.log('🔄 初始化面試狀態');

            // 清空輸入框
            if ($('#msg')) {
                $('#msg').value = '';
            }

            // 重置前端狀態，確保完全乾淨
            resetTimer();
            resetInterviewModePrompt();

            // 清除聊天記錄，確保完全乾淨的狀態
            chat.innerHTML = '';

            // 重置所有狀態變數
            interviewModePromptShown = false;
            interviewEnded = false;
            userCompletedIntro = false;
            interviewStarted = false;

            // 重置階段到初始狀態
            setCurrentStage(InterviewStage.INITIAL);

            // 清除保存的面試狀態
            clearInterviewState();

            // 重置頂部徽章狀態
            const badge = document.querySelector('.badge');
            if (badge) {
                badge.textContent = '步驟 3/3';
            }

            // 重新顯示所有控制按鈕
            const startBtn = $('#start');
            const pauseBtn = $('#pause');
            const stopBtn = $('#stop');
            if (startBtn) startBtn.style.display = 'inline-block';
            if (pauseBtn) pauseBtn.style.display = 'inline-block';
            if (stopBtn) stopBtn.style.display = 'inline-block';

            // 顯示初始狀態（完全乾淨的面試開始狀態）
            push('assistant', '👋 歡迎進入 JobMate360 虛擬面試系統！\n\n💬 **使用說明：**\n• 點擊「開始面試」開始正式面試流程\n• 或直接開始自我介紹，我會記錄您的內容\n• 完成後輸入「完成自介」，我會先分析再出題\n\n🎯 **面試流程：**\n1️⃣ 自我介紹階段 → 2️⃣ 面試問答階段 → 3️⃣ 面試總結');

            // 設置為初始狀態的按鈕配置
            setButtonsForStage('initial');

            console.log('✅ 面試狀態初始化完成');

        } catch (error) {
            console.error('面試狀態初始化失敗:', error);
            // 發生錯誤時也顯示默認歡迎訊息
            chat.innerHTML = '';
            push('assistant', '👋 歡迎進入 JobMate360 虛擬面試系統！\n\n💬 **使用說明：**\n• 點擊「開始面試」開始正式面試流程\n• 或直接開始自我介紹，我會記錄您的內容\n• 完成後輸入「完成自介」，我會先分析再出題\n\n🎯 **面試流程：**\n1️⃣ 自我介紹階段 → 2️⃣ 面試問答階段 → 3️⃣ 面試總結');
            setButtonsForStage('initial');
        }
    }

    // 保存面試狀態
    function saveInterviewState(state, stage) {
        try {
            const userId = localStorage.getItem('jobmate_user_id') || 'default_user';

            // 保存基本狀態
            localStorage.setItem('interview_state_' + userId, state);
            localStorage.setItem('interview_timer_' + userId, seconds.toString());
            if (stage) {
                localStorage.setItem('interview_stage_' + userId, stage);
            }

            // 保存當前階段到新的存儲系統
            localStorage.setItem('current_interview_stage', currentStage);

            // 保存關鍵狀態變數
            const stateVars = {
                userCompletedIntro,
                interviewEnded,
                interviewModePromptShown,
                interviewStarted,
                currentStage
            };
            localStorage.setItem('interview_vars_' + userId, JSON.stringify(stateVars));

            // 保存詳細的面試狀態快照
            const detailedState = {
                timestamp: Date.now(),
                currentStage,
                userCompletedIntro,
                interviewEnded,
                interviewModePromptShown,
                interviewStarted,
                timerSeconds: seconds,
                state,
                stage,
                buttonStates: {
                    startBtnText: $('#start')?.textContent || '開始面試'
                }
            };
            localStorage.setItem('interview_detailed_state_' + userId, JSON.stringify(detailedState));

            console.log('💾 面試狀態已保存:', { state, stage, timer: seconds, currentStage, vars: stateVars });
        } catch (error) {
            console.error('保存面試狀態失敗:', error);
        }
    }

    // 保存評分數據
    function saveScoreData(scoreData) {
        try {
            const userId = localStorage.getItem('jobmate_user_id') || 'default_user';
            localStorage.setItem('interview_score_' + userId, JSON.stringify(scoreData));
            console.log('💾 評分數據已保存');
        } catch (error) {
            console.error('保存評分數據失敗:', error);
        }
    }

    // 獲取評分數據
    function getScoreData() {
        try {
            const userId = localStorage.getItem('jobmate_user_id') || 'default_user';
            const savedScore = localStorage.getItem('interview_score_' + userId);
            if (savedScore) {
                return JSON.parse(savedScore);
            }
            return null;
        } catch (error) {
            console.error('獲取評分數據失敗:', error);
            return null;
        }
    }

    // 恢復面試狀態
    function restoreInterviewState() {
        try {
            const userId = localStorage.getItem('jobmate_user_id') || 'default_user';

            // 嘗試恢復詳細狀態
            const detailedStateStr = localStorage.getItem('interview_detailed_state_' + userId);
            if (detailedStateStr) {
                const detailedState = JSON.parse(detailedStateStr);
                console.log('🔄 恢復詳細狀態:', detailedState);

                // 檢查狀態是否過期（超過24小時）
                const now = Date.now();
                const stateAge = now - (detailedState.timestamp || 0);
                const maxAge = 24 * 60 * 60 * 1000; // 24小時

                if (stateAge > maxAge) {
                    console.log('⏰ 狀態已過期，清除舊狀態');
                    clearInterviewState();
                    return null;
                }

                // 恢復所有狀態變數
                currentStage = detailedState.currentStage || InterviewStage.INITIAL;
                userCompletedIntro = detailedState.userCompletedIntro || false;
                interviewEnded = detailedState.interviewEnded || false;
                interviewModePromptShown = detailedState.interviewModePromptShown || false;
                interviewStarted = detailedState.interviewStarted || false;
                seconds = detailedState.timerSeconds || 0;

                // 恢復計時器顯示
                renderTimer();

                console.log('✅ 詳細狀態已完全恢復');
                return detailedState;
            }

            // 回退到舊的狀態恢復方式
            const savedVars = localStorage.getItem('interview_vars_' + userId);
            if (savedVars) {
                const stateVars = JSON.parse(savedVars);
                userCompletedIntro = stateVars.userCompletedIntro || false;
                interviewEnded = stateVars.interviewEnded || false;
                interviewModePromptShown = stateVars.interviewModePromptShown || false;
                interviewStarted = stateVars.interviewStarted || false;
                if (stateVars.currentStage) {
                    currentStage = stateVars.currentStage;
                }
                console.log('✅ 基本狀態變數已恢復:', stateVars);
                return stateVars;
            }

            return null;
        } catch (error) {
            console.error('恢復面試狀態失敗:', error);
            return null;
        }
    }

    // 清除面試狀態
    function clearInterviewState() {
        try {
            const userId = localStorage.getItem('jobmate_user_id') || 'default_user';
            localStorage.removeItem('interview_state_' + userId);
            localStorage.removeItem('interview_timer_' + userId);
            localStorage.removeItem('interview_stage_' + userId);
            localStorage.removeItem('interview_chat_' + userId);
            localStorage.removeItem('interview_score_' + userId);
            localStorage.removeItem('interview_vars_' + userId);
            localStorage.removeItem('interview_detailed_state_' + userId);
            // 清除新的階段存儲
            localStorage.removeItem('current_interview_stage');
            console.log('🗑️ 面試狀態已清除');
        } catch (error) {
            console.error('清除面試狀態失敗:', error);
        }
    }

    // 保存對話歷史
    function saveChatHistory() {
        try {
            const userId = localStorage.getItem('jobmate_user_id') || 'default_user';
            const chatHTML = chat.innerHTML;
            localStorage.setItem('interview_chat_' + userId, chatHTML);
        } catch (error) {
            console.error('保存對話歷史失敗:', error);
        }
    }



    let send = userSend;

    let __interviewAppInitialized = false;
    document.addEventListener('DOMContentLoaded', async function () {
        if (__interviewAppInitialized) {
            console.log('⚠️ 初始化已執行，跳過重複初始化');
            return;
        }
        __interviewAppInitialized = true;
        // 若尚未有使用者識別，產生一組本機唯一 ID，避免彼此干擾
        if (!localStorage.getItem('jobmate_user_id')) {
            const uid = 'u-' + Math.random().toString(36).slice(2) + Date.now().toString(36);
            localStorage.setItem('jobmate_user_id', uid);
        }

        // 監聽虛擬人服務狀態
        window.addEventListener('avatarServiceUnavailable', function (event) {
            console.log('[Interview] 收到虛擬人服務不可用事件:', event.detail);
            // 只顯示一次通知
            if (!avatarNotificationShown) {
                push('assistant', '💡 **系統提示**\n\n虛擬人服務暫時無法使用，但對話功能完全正常。\n\n您可以繼續進行面試，所有功能都會正常運作！', null, 'info');
                avatarNotificationShown = true;
            }
        });

        // 添加 F5 按鍵事件監聽器
        document.addEventListener('keydown', function (e) {
            // 檢查是否為 F5 鍵（keyCode 116 或 key === 'F5'）
            if (e.key === 'F5' || e.keyCode === 116) {
                e.preventDefault(); // 防止瀏覽器默認的頁面重新載入
                console.log('F5 鍵被按下，開始重置面試...');

                // 直接觸發重新開始功能，與重新開始按鈕行為完全一致
                handleRestartCommand();
            }
        });

        attachSpeechToInput($('#mic'), $('#msg'));
        $('#send').addEventListener('click', () => send());
        $('#msg').addEventListener('keydown', e => { if (e.key === 'Enter') send(); });

        // 初始化面試狀態
        await initializeInterviewState();

        // 嘗試從 localStorage 恢復階段並套用對應按鈕（避免刷新後按鈕不一致）
        try {
            const savedStage = localStorage.getItem('current_interview_stage');
            if (savedStage && Object.values(InterviewStage).includes(savedStage)) {
                console.log('🔁 刷新後恢復階段並套用按鈕:', savedStage);
                setCurrentStage(savedStage);
                setButtonsForStage(savedStage);
            } else {
                // 若無有效階段，保持初始顯示
                setButtonsForStage('initial');
            }
        } catch (e) {
            console.warn('恢復並套用階段狀態失敗，回退到 initial:', e);
            setButtonsForStage('initial');
        }

        // 初始化虛擬人同步控制
        initializeSyncControls();

        // 確保控制面板按鈕可見（不覆蓋上方恢復的狀態）

        // 強制顯示所有控制面板按鈕
        setTimeout(() => {
            console.log("強制顯示按鈕 setTimeout 被觸發", new Error().stack);

            const startBtn = $('#start');
            const pauseBtn = $('#pause');
            const stopBtn = $('#stop');
            const actionsDiv = document.querySelector('.actions');

            if (startBtn) {
                startBtn.style.display = 'inline-block';
                startBtn.style.visibility = 'visible';
                startBtn.style.width = '120px';
                startBtn.style.minWidth = '120px';
                startBtn.style.maxWidth = '120px';
                startBtn.disabled = false;
            }
            if (pauseBtn) {
                pauseBtn.style.display = 'inline-block';
                pauseBtn.style.visibility = 'visible';
                pauseBtn.style.width = '120px';
                pauseBtn.style.minWidth = '120px';
                pauseBtn.style.maxWidth = '120px';
            }
            if (stopBtn) {
                stopBtn.style.display = 'inline-block';
                stopBtn.style.visibility = 'visible';
                stopBtn.style.width = '120px';
                stopBtn.style.minWidth = '120px';
                stopBtn.style.maxWidth = '120px';
            }
            if (actionsDiv) {
                actionsDiv.style.display = 'flex';
                actionsDiv.style.visibility = 'visible';
            }

            console.log('控制面板按鈕已強制顯示', new Error().stack);
            console.log('按鈕設置結果:', {
                startBtn: startBtn?.style?.display,
                pauseBtn: pauseBtn?.style?.display,
                stopBtn: stopBtn?.style?.display,
                actionsDiv: actionsDiv?.style?.display
            });
        }, 500);

        // 定期檢查並確保開始按鈕可見且大小固定
        buttonCheckInterval = setInterval(() => {
            // 簡化日誌，避免在正常輪詢時輸出 Error 堆疊
            console.log('定期檢查按鈕 setInterval 被觸發');

            const startBtn = $('#start');
            const pauseBtn = $('#pause');
            const stopBtn = $('#stop');

            // 詳細記錄按鈕狀態
            console.log('按鈕狀態檢查:', {
                startBtnExists: !!startBtn,
                startBtnDisplay: startBtn?.style?.display,
                startBtnVisibility: startBtn?.style?.visibility,
                startBtnWidth: startBtn?.style?.width,
                startBtnDisabled: startBtn?.disabled,
                startBtnText: startBtn?.textContent
            });

            if (startBtn && (startBtn.style.display === 'none' || startBtn.style.visibility === 'hidden')) {
                console.log('檢測到開始按鈕被隱藏，強制顯示', new Error().stack);
                console.log('開始按鈕當前狀態:', {
                    display: startBtn.style.display,
                    visibility: startBtn.style.visibility,
                    width: startBtn.style.width
                });
                startBtn.style.display = 'inline-block';
                startBtn.style.visibility = 'visible';
                startBtn.style.width = '120px';
                startBtn.style.minWidth = '120px';
                startBtn.style.maxWidth = '120px';
                startBtn.disabled = false;

                console.log('按鈕修復後狀態:', {
                    display: startBtn.style.display,
                    visibility: startBtn.style.visibility,
                    width: startBtn.style.width
                });
            }

            // 確保所有按鈕大小固定
            if (startBtn) {
                startBtn.style.width = '120px';
                startBtn.style.minWidth = '120px';
                startBtn.style.maxWidth = '120px';
            }
            if (pauseBtn) {
                pauseBtn.style.width = '120px';
                pauseBtn.style.minWidth = '120px';
                pauseBtn.style.maxWidth = '120px';
            }
            if (stopBtn) {
                stopBtn.style.width = '120px';
                stopBtn.style.minWidth = '120px';
                stopBtn.style.maxWidth = '120px';
                // 確保結束面試按鈕在面試階段可見
                if (currentStage === InterviewStage.INTERVIEW || currentStage === InterviewStage.QUESTIONING) {
                    stopBtn.style.display = 'inline-block';
                    stopBtn.style.visibility = 'visible';
                }
            }
        }, 2000); // 每2秒檢查一次

        // 調試：確保按鈕可見
        setTimeout(() => {
            console.log("調試按鈕可見 setTimeout 被觸發", new Error().stack);

            const startBtn = $('#start');
            const pauseBtn = $('#pause');
            const stopBtn = $('#stop');
            const actionsDiv = document.querySelector('.actions');

            console.log('調試按鈕狀態:', new Error().stack);
            console.log('startBtn:', startBtn, startBtn?.style?.display, startBtn?.style?.visibility);
            console.log('pauseBtn:', pauseBtn, pauseBtn?.style?.display, pauseBtn?.style?.visibility);
            console.log('stopBtn:', stopBtn, stopBtn?.style?.display, stopBtn?.style?.visibility);
            console.log('actionsDiv:', actionsDiv, actionsDiv?.style?.display, actionsDiv?.style?.visibility);

            // 強制顯示按鈕
            if (startBtn) {
                startBtn.style.display = 'inline-block';
                startBtn.style.visibility = 'visible';
            }
            if (pauseBtn) {
                pauseBtn.style.display = 'inline-block';
                pauseBtn.style.visibility = 'visible';
            }
            if (stopBtn) {
                stopBtn.style.display = 'inline-block';
                stopBtn.style.visibility = 'visible';
            }
            if (actionsDiv) {
                actionsDiv.style.display = 'flex';
                actionsDiv.style.visibility = 'visible';
            }

            console.log('按鈕狀態已強制設置為可見', new Error().stack);
        }, 1000);

        $('#start').addEventListener('click', () => {
            console.log("開始面試按鈕點擊事件被觸發", new Error().stack);
            console.log("當前階段:", currentStage);
            console.log("InterviewStage.INITIAL:", InterviewStage.INITIAL);
            console.log("InterviewStage.FINISHED:", InterviewStage.FINISHED);
            console.log("階段比較結果:", currentStage === InterviewStage.INITIAL || currentStage === InterviewStage.FINISHED);

            // 在面試和問答階段，開始按鈕作為重新開始使用
            if (currentStage === InterviewStage.INTERVIEW ||
                currentStage === InterviewStage.QUESTIONING) {
                console.log("面試階段，開始按鈕作為重新開始使用");
                handleRestartCommand();
                return;
            }

            // 在完成階段，開始按鈕作為重新開始使用
            if (currentStage === InterviewStage.FINISHED) {
                console.log("完成階段，執行重新開始邏輯");
                handleRestartCommand();
                return;
            }

            if (currentStage === InterviewStage.INITIAL) {
                // 設置為自我介紹收集階段
                setCurrentStage(InterviewStage.INTRO_COLLECTION);

                // 標記面試已經開始
                interviewStarted = true;

                startTimer();
                resetInterviewModePrompt(); // 重置面試模式提示狀態，允許顯示

                // 重置面試結束標記
                interviewEnded = false;

                // 保存面試開始狀態
                saveInterviewState('started', 'intro_collection');

                // 重置頂部徽章狀態，從「面試完成」改回「步驟 3/3」
                const badge = document.querySelector('.badge');
                if (badge) {
                    badge.textContent = '步驟 3/3';
                }

                push('assistant', '🎯 面試開始！請先進行自我介紹。\n\n📋 **自我介紹結構建議：**\n1. 開場簡介（身份與專業定位）\n2. 學經歷概述\n3. 核心技能與強項\n4. 代表成果\n5. 與職缺的連結\n6. 結語與期待\n\n💡 完成後點「完成自介」或輸入「完成自介」，我會先分析再出題。');
                // 設置為初始狀態（自我介紹階段）
                setButtonsForStage('initial');
            } else if (currentStage === 'intro') {
                // 完成自我介紹
                console.log("完成自我介紹");
                // 這裡可以添加完成自我介紹的邏輯
                // 例如發送請求到後端處理自我介紹完成
            }

            // 強制確保開始按鈕可見且大小固定（即使在其他邏輯中被隱藏）
            setTimeout(() => {
                console.log("開始按鈕點擊後的強制顯示 setTimeout 被觸發", new Error().stack);

                const startBtn = $('#start');
                if (startBtn) {
                    startBtn.style.display = 'inline-block';
                    startBtn.style.visibility = 'visible';
                    startBtn.style.width = '120px';
                    startBtn.style.minWidth = '120px';
                    startBtn.style.maxWidth = '120px';
                }
            }, 100);
        });
        $('#pause').addEventListener('click', () => pauseTimer());
        $('#stop').addEventListener('click', async () => {
            if (confirm('確定要結束面試嗎？系統將生成面試總結。')) {
                console.log('用戶點擊結束面試按鈕');

                // 檢查面試是否已經開始
                if (!interviewStarted) {
                    push('assistant', '面試尚未開始，無需結束。');
                    return;
                }

                // 發送結束面試指令到後端
                try {
                    await userSend('結束面試');
                } catch (error) {
                    console.error('結束面試失敗:', error);
                    push('assistant', '結束面試時發生錯誤，請重試或直接輸入「結束面試」。', null, 'error');
                }
            }
        });

        // 自我介紹階段按鈕事件
        const completeIntroBtn = $('#complete-intro');
        if (completeIntroBtn) {
            completeIntroBtn.addEventListener('click', async () => {
                // 先不標記完成，等待後端回應後再決定
                // userCompletedIntro = true; // 移到後端回應處理中

                // 重置面試結束標記，因為開始新的面試流程
                interviewEnded = false;

                // 重置頂部徽章狀態，從「面試完成」改回「步驟 3/3」
                const badge = document.querySelector('.badge');
                if (badge) {
                    badge.textContent = '步驟 3/3';
                }

                // 發送完成自我介紹，系統會自動分析並給出第一題
                await userSend('完成自我介紹');
                // 注意：不要在這裡隱藏按鈕，讓系統根據響應結果決定是否隱藏
            });
        }

        const restartIntroBtn = $('#restart-intro');
        if (restartIntroBtn) {
            restartIntroBtn.addEventListener('click', () => {
                handleRestartCommand();
            });
        }

        // 移除面試階段的快捷按鈕事件（不再使用）
        const restartInterviewBtn = $('#restart-interview');
        if (restartInterviewBtn) {
            restartInterviewBtn.remove();
        }

        const endInterviewBtn = $('#end-interview');
        if (endInterviewBtn) {
            endInterviewBtn.remove();
            /* 若未來需要保留結束面試流程，請改走主控制區邏輯
            endInterviewBtn.addEventListener('click', async () => {
                if (confirm('確定要結束面試嗎？系統將生成面試總結。')) {
                    // 標記面試已結束，避免重複處理
                    interviewEnded = true;

                    // 先停止計時器
                    pauseTimer();

                    // 設置為結束狀態
                    setButtonsForStage('finished');

                    // 重置前端狀態，確保與後端狀態一致
                    resetTimer();
                    // 不要重置 interviewModePromptShown，避免在結束面試後顯示面試模式提示
                    // resetInterviewModePrompt();
                    // interviewModePromptShown = false;

                    // 更新步驟指示器
                    const badge = document.querySelector('.badge');
                    if (badge) {
                        badge.textContent = '面試完成';
                    }

                    // 發送結束面試指令，讓後端處理並返回總結
                    await userSend('結束面試');

                    // 延遲顯示操作指引和跳轉選項
                    setTimeout(() => {
                        push('assistant', '💡 **面試已完成！**\n\n🎉 感謝您的參與！\n\n📋 **接下來您可以：**\n• 輸入「重新開始」開始新的面試\n• 或等待 5 秒後自動跳轉到完成頁面');

                        // 5秒後自動跳轉到完成頁面
                        setTimeout(() => {
                            navigate('completion.html');
                        }, 5000);
                    }, 2000);
                }
            });
            */
        }

        // 退出面試按鈕事件處理程式
        const exitInterviewBtn = $('#exit-interview');
        if (exitInterviewBtn) {
            exitInterviewBtn.addEventListener('click', () => {
                if (confirm('確定要退出面試嗎？所有進度將會丟失。')) {
                    // 標記面試已結束
                    interviewEnded = true;

                    // 停止計時器
                    pauseTimer();

                    // 重置所有狀態
                    resetTimer();
                    resetInterviewModePrompt();

                    // 清空聊天記錄
                    const chatContainer = document.getElementById('chat');
                    if (chatContainer) {
                        chatContainer.innerHTML = '';
                    }

                    // 重置階段到初始狀態
                    setCurrentStage(InterviewStage.INITIAL);
                    setButtonsForStage('initial');

                    // 更新步驟指示器
                    const badge = document.querySelector('.badge');
                    if (badge) {
                        badge.textContent = '準備開始';
                    }

                    // 顯示退出訊息
                    push('system', '📋 面試已退出，您可以重新開始面試或返回首頁。');

                    // 可選：延遲後跳轉回首頁或重新整理頁面
                    setTimeout(() => {
                        if (confirm('是否要返回首頁？')) {
                            window.location.href = '/';
                        } else {
                            // 重新整理頁面，回到初始狀態
                            window.location.reload();
                        }
                    }, 2000);
                }
            });
        }

        renderTimer();
    });

    // 虛擬人同步控制初始化
    function initializeSyncControls() {
        // 延遲執行，確保所有DOM元素都已載入
        setTimeout(() => {
            const enableSyncCheckbox = document.getElementById('enable-sync');
            const syncNowButton = document.getElementById('sync-now');
            const syncStatusSpan = document.getElementById('sync-status');

            if (!enableSyncCheckbox || !syncNowButton || !syncStatusSpan) {
                console.warn('同步控制元素未找到，可能是因為元素還未載入或不存在於此頁面');
                return;
            }

            console.log('同步控制元素初始化成功');

            // 更新同步狀態顯示
            function updateSyncStatus() {
                if (window.LT && window.LT.getSyncConfig) {
                    const config = window.LT.getSyncConfig();
                    const sharedId = localStorage.getItem('lt_shared_session_id');
                    if (config.syncWithDashboard && sharedId) {
                        syncStatusSpan.textContent = `已同步 (${sharedId.slice(-6)})`;
                        syncStatusSpan.style.color = '#4ade80';
                    } else if (config.syncWithDashboard) {
                        syncStatusSpan.textContent = '等待同步';
                        syncStatusSpan.style.color = '#fbbf24';
                    } else {
                        syncStatusSpan.textContent = '同步已停用';
                        syncStatusSpan.style.color = '#9ca3af';
                    }
                }
            }

            // 同步開關
            enableSyncCheckbox.addEventListener('change', (e) => {
                const enabled = e.target.checked;
                if (window.LT && window.LT.setSyncMode) {
                    window.LT.setSyncMode(enabled);
                    updateSyncStatus();
                    console.log('同步模式:', enabled ? '啟用' : '停用');
                }
            });

            // 立即同步按鈕
            syncNowButton.addEventListener('click', async () => {
                syncNowButton.disabled = true;
                syncNowButton.textContent = '同步中...';

                try {
                    // 嘗試從 dashboard 獲取最新 session
                    const response = await fetch('/ltapi/index.json');
                    if (response.ok) {
                        const data = await response.json();
                        if (data.sessionid) {
                            localStorage.setItem('lt_shared_session_id', data.sessionid);
                            if (window.LT && window.LT.syncToSession) {
                                window.LT.syncToSession(data.sessionid);
                            }
                            push('assistant', `🔄 已同步到虛擬人 Session: ${data.sessionid}`, null, 'info');
                        }
                    } else {
                        push('assistant', '⚠️ 無法獲取虛擬人 Session，請確保 LiveTalking 服務正在運行', null, 'warning');
                    }
                } catch (error) {
                    console.error('同步失敗:', error);
                    push('assistant', '❌ 同步失敗，請檢查虛擬人服務狀態', null, 'error');
                } finally {
                    syncNowButton.disabled = false;
                    syncNowButton.textContent = '立即同步';
                    updateSyncStatus();
                }
            });

            // 定期更新狀態顯示
            syncStatusInterval = setInterval(updateSyncStatus, 2000);
            updateSyncStatus();
        }, 100); // 延遲100ms確保DOM完全載入
    }

    // 頁面載入時的階段初始化
    document.addEventListener('DOMContentLoaded', function () {
        if (__interviewAppInitialized) {
            console.log('⚠️ 第二階段初始化偵測到已初始化，跳過');
            return;
        }
        console.log('🚀 開始面試系統初始化...');

        // 嘗試恢復完整的面試狀態
        const restoredState = restoreInterviewState();

        if (restoredState) {
            console.log('✅ 已恢復之前的面試狀態');

            // 根據恢復的狀態設置按鈕
            setButtonsForStage(currentStage);

            // 如果面試正在進行中，恢復計時器
            if (interviewStarted && !interviewEnded) {
                startTimer();
                console.log('⏰ 計時器已恢復');
            }

            // 根據當前階段顯示適當的歡迎訊息
            if (currentStage === InterviewStage.INTRO_COLLECTION) {
                push('assistant', '🔄 **面試狀態已恢復**\n\n您正在進行自我介紹階段。\n\n💡 完成後點「完成自介」或輸入「完成自介」，我會先分析再出題。');
            } else if (currentStage === InterviewStage.INTERVIEW || currentStage === InterviewStage.QUESTIONING) {
                push('assistant', '🔄 **面試狀態已恢復**\n\n您正在進行面試問答階段。\n\n💡 可以繼續回答問題或使用快捷按鈕操作。');
            } else if (currentStage === InterviewStage.FINISHED) {
                push('assistant', '🔄 **面試狀態已恢復**\n\n面試已完成。\n\n💡 您可以查看結果或重新開始面試。');
            }
        } else {
            // 沒有找到之前的狀態，進行正常初始化
            console.log('🆕 沒有找到之前的狀態，進行全新初始化');

            // 初始化階段 - 嘗試從基本 localStorage 恢復
            const savedStage = localStorage.getItem('current_interview_stage');
            const userId = localStorage.getItem('jobmate_user_id') || 'default_user';
            const savedUserStage = localStorage.getItem('interview_stage_' + userId);

            console.log('🔍 基本階段恢復調試信息:');
            console.log('- savedStage:', savedStage);
            console.log('- savedUserStage:', savedUserStage);
            console.log('- InterviewStage values:', Object.values(InterviewStage));

            if (savedStage && Object.values(InterviewStage).includes(savedStage)) {
                currentStage = savedStage;
                console.log('🔄 從 localStorage 恢復階段:', savedStage);
            } else if (savedUserStage && Object.values(InterviewStage).includes(savedUserStage)) {
                setCurrentStage(savedUserStage);
                console.log('🔄 從舊格式 localStorage 恢復階段:', savedUserStage);
            } else {
                setCurrentStage(InterviewStage.INITIAL);
                console.log('🆕 設置初始階段:', InterviewStage.INITIAL);
            }

            // 設置按鈕狀態
            setButtonsForStage(currentStage);
        }

        console.log('🏁 面試系統初始化完成，當前階段:', currentStage);
        console.log('📊 當前狀態變數:', {
            userCompletedIntro,
            interviewEnded,
            interviewModePromptShown,
            interviewStarted,
            timerSeconds: seconds
        });

        // 設置定期狀態保存（每30秒保存一次）
        stateSaveInterval = setInterval(() => {
            if (interviewStarted && !interviewEnded) {
                console.log('⏰ 定期保存面試狀態');
                saveInterviewState('running', currentStage);
            }
        }, 30000); // 30秒

        // 監聽頁面關閉事件，保存狀態
        window.addEventListener('beforeunload', () => {
            console.log('📤 頁面關閉前保存狀態');
            saveInterviewState('paused', currentStage);
        });

        // 監聽頁面可見性變化，在頁面隱藏時保存狀態
        document.addEventListener('visibilitychange', () => {
            if (document.hidden && (interviewStarted || userCompletedIntro)) {
                console.log('👁️ 頁面隱藏，保存狀態');
                saveInterviewState('backgrounded', currentStage);
            }
        });
    });
})();



