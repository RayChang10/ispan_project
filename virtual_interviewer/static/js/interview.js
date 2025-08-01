/**
 * 虛擬面試顧問 - 面試頁面功能
 */

let currentUserId = null;
let isInterviewActive = false;
let chatHistory = [];
let autoNextQuestion = true; // 新增自動下一題開關

// 面試管理器
const InterviewManager = {
    /**
     * 初始化面試介面
     */
    init: function () {
        this.bindEvents();
        this.loadChatHistory();
        this.checkMicrophonePermission();
        // 新增自動下一題開關
        const toggleHtml = `
            <div class="form-check form-switch mb-3">
                <input class="form-check-input" type="checkbox" id="autoNextToggle" checked>
                <label class="form-check-label" for="autoNextToggle">
                    <i class="fas fa-forward me-1"></i>自動下一題
                </label>
            </div>
            <div class="mb-3">
                <button class="btn btn-danger btn-sm w-100" id="endInterview">
                    <i class="fas fa-stop me-1"></i>結束面試
                </button>
            </div>
        `;
        $('#startInterview').before(toggleHtml);
        $('#autoNextToggle').on('change', function () {
            autoNextQuestion = this.checked;
            Utils.showNotification(
                autoNextQuestion ? '已啟用自動下一題' : '已停用自動下一題',
                'info'
            );
        });
        // 新增結束面試按鈕事件
        $('#endInterview').on('click', () => {
            this.endInterview();
        });
    },

    /**
     * 綁定事件監聽器
     */
    bindEvents: function () {
        // 發送訊息按鈕
        $('#sendMessage').on('click', () => {
            this.sendMessage();
        });

        // Enter鍵發送訊息
        $('#messageInput').on('keypress', (e) => {
            if (e.which === 13 && !e.shiftKey) {
                e.preventDefault();
                this.sendMessage();
            }
        });

        // 開始面試按鈕
        $('#startInterview').on('click', () => {
            this.startInterview();
        });

        // 重新開始按鈕
        $('#resetInterview').on('click', () => {
            this.resetInterview();
        });

        // 語音輸入按鈕
        $('#voiceInput').on('click', () => {
            this.toggleVoiceInput();
        });

        // 檔案上傳按鈕
        $('#fileUpload').on('click', () => {
            $('#fileInput').click();
        });

        // 檔案選擇事件
        $('#fileInput').on('change', (e) => {
            this.handleFileUpload(e.target.files[0]);
        });

        // 確認輸入按鈕
        $('#confirmInput').on('click', () => {
            this.confirmInput();
        });

        // 監聽輸入框變化
        $('#messageInput').on('input', () => {
            this.updateConfirmButton();
        });


    },

    /**
     * 發送訊息
     */
    sendMessage: function () {
        const message = $('#messageInput').val().trim();
        if (!message) return;

        // 顯示用戶訊息
        this.displayMessage(message, 'user');

        // 清空輸入框
        $('#messageInput').val('');
        this.updateConfirmButton();

        // 顯示AI正在思考
        this.showTypingIndicator();

        // 優先使用 MCP 伺服器，如果失敗則使用後端
        this.sendToMCP(message).then((mcpResponse) => {
            this.hideTypingIndicator();
            console.log('MCP 成功回應:', mcpResponse);

            // MCP 回應格式檢查
            if (mcpResponse && mcpResponse.response) {
                this.displayMessage(mcpResponse.response, 'ai');

                // 儲存對話記錄
                chatHistory.push({
                    user: message,
                    ai: mcpResponse.response,
                    timestamp: new Date().toISOString(),
                    tool_used: mcpResponse.tool_used || 'mcp'
                });
                this.saveChatHistory();
                // 自動下一題判斷
                this.checkAutoNextQuestion(mcpResponse.response);
            } else {
                console.log('MCP 回應格式錯誤，使用後端');
                this.sendToBackend(message);
            }
        }).catch((error) => {
            console.log('MCP 連接失敗，錯誤:', error);
            this.hideTypingIndicator();
            // MCP 連接失敗，使用後端
            this.sendToBackend(message);
        });
    },

    /**
     * 發送到 MCP 伺服器
     */
    sendToMCP: function (message) {
        return new Promise((resolve, reject) => {
            $.ajax({
                url: 'http://localhost:8080/api/chat',
                type: 'POST',
                contentType: 'application/json',
                data: JSON.stringify({ message: message }),
                timeout: 5000,
                crossDomain: true
            }).done((response) => {
                console.log('MCP 回應:', response);
                resolve(response);
            }).fail((xhr, status, error) => {
                console.log('MCP 連接失敗，狀態:', status, '錯誤:', error);
                console.log('HTTP 狀態:', xhr.status, '回應:', xhr.responseText);
                reject(error);
            });
        });
    },

    /**
     * 發送到後端
     */
    sendToBackend: function (message) {
        API.post('/interview', {
            message: message,
            user_id: currentUserId
        }).done((response) => {
            this.hideTypingIndicator();
            if (response.success) {
                this.displayMessage(response.response, 'ai');

                // 儲存對話記錄
                chatHistory.push({
                    user: message,
                    ai: response.response,
                    timestamp: new Date().toISOString(),
                    tool_used: 'backend'
                });
                this.saveChatHistory();
                // 自動下一題判斷
                this.checkAutoNextQuestion(response.response);
            }
        }).fail((xhr) => {
            this.hideTypingIndicator();
            this.displayMessage('抱歉，我現在無法回應。請稍後再試。', 'ai');
        });
    },

    /**
     * 顯示訊息
     */
    displayMessage: function (message, sender) {
        const timestamp = Utils.formatRelativeTime(new Date());
        const isUser = sender === 'user';
        const avatarUrl = isUser ?
            'https://via.placeholder.com/40x40/28a745/ffffff?text=U' :
            'https://via.placeholder.com/40x40/007bff/ffffff?text=AI';

        const messageHtml = `
            <div class="message ${isUser ? 'user-message' : 'ai-message'} mb-3 fade-in">
                <div class="d-flex align-items-start ${isUser ? 'flex-row-reverse' : ''}">
                    <div class="avatar ${isUser ? 'ms-3' : 'me-3'}">
                        <img src="${avatarUrl}" class="rounded-circle" width="40" height="40">
                    </div>
                    <div class="message-content">
                        <div class="bg-primary text-white rounded-3 p-3 ${isUser ? 'slide-in-right' : 'slide-in-left'}">
                            <p class="mb-0">${this.formatMessage(message)}</p>
                        </div>
                        <small class="text-muted ms-1">${timestamp}</small>
                    </div>
                </div>
            </div>
        `;

        $('#chatMessages').append(messageHtml);
        this.scrollToBottom();
    },

    /**
     * 格式化訊息內容
     */
    formatMessage: function (message) {
        // 簡單的文字格式化
        return message
            .replace(/\n/g, '<br>')
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\*(.*?)\*/g, '<em>$1</em>');
    },

    /**
     * 顯示打字指示器
     */
    showTypingIndicator: function () {
        const typingHtml = `
            <div class="typing-indicator message ai-message mb-3" id="typingIndicator">
                <div class="d-flex align-items-start">
                    <div class="avatar me-3">
                        <img src="https://via.placeholder.com/40x40/007bff/ffffff?text=AI" 
                             class="rounded-circle" width="40" height="40">
                    </div>
                    <div class="message-content">
                        <div class="bg-primary text-white rounded-3 p-3">
                            <div class="typing-animation">
                                <span></span><span></span><span></span>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;

        $('#chatMessages').append(typingHtml);
        this.scrollToBottom();
    },

    /**
     * 隱藏打字指示器
     */
    hideTypingIndicator: function () {
        $('#typingIndicator').remove();
    },

    /**
     * 滾動到底部
     */
    scrollToBottom: function () {
        const chatMessages = document.getElementById('chatMessages');
        chatMessages.scrollTop = chatMessages.scrollHeight;
    },

    /**
 * 開始面試
 */
    startInterview: function () {
        if (isInterviewActive) return;

        isInterviewActive = true;
        $('#interviewStatus').html('<i class="fas fa-circle me-1"></i>面試進行中').removeClass('bg-success').addClass('bg-warning');
        $('#startInterview').prop('disabled', true).text('面試中...');

        // 使用 MCP 獲取面試問題
        this.sendToMCP('給我一個面試問題').then((response) => {
            if (response.success) {
                this.displayMessage('面試已開始！' + response.response, 'ai');
            } else {
                this.displayMessage('面試已開始！請先自我介紹，然後我會根據您的背景提出相關問題。', 'ai');
            }
        }).catch(() => {
            this.displayMessage('面試已開始！請先自我介紹，然後我會根據您的背景提出相關問題。', 'ai');
        });

        Utils.showNotification('面試已開始，祝您順利！', 'success');
    },

    /**
     * 重新開始面試
     */
    resetInterview: function () {
        if (confirm('確定要重新開始面試嗎？這將清除所有對話記錄。')) {
            isInterviewActive = false;
            chatHistory = [];
            $('#chatMessages').empty();
            $('#interviewStatus').html('<i class="fas fa-circle me-1"></i>準備就緒').removeClass('bg-warning').addClass('bg-success');
            $('#startInterview').prop('disabled', false).text('開始面試');

            // 顯示歡迎訊息
            this.displayMessage('歡迎使用虛擬面試顧問！我會幫助您進行模擬面試。請先建立您的履歷資料，或直接開始對話練習。', 'ai');

            this.saveChatHistory();
            Utils.showNotification('面試已重新開始', 'info');
        }
    },

    /**
     * 切換語音輸入
     */
    toggleVoiceInput: function () {
        if (!this.speechRecognition) {
            Utils.showNotification('您的瀏覽器不支援語音識別功能', 'warning');
            return;
        }

        if (this.isListening) {
            this.stopVoiceInput();
        } else {
            this.startVoiceInput();
        }
    },

    /**
     * 開始語音輸入
     */
    startVoiceInput: function () {
        this.isListening = true;
        $('#voiceInput').removeClass('btn-outline-info').addClass('btn-danger').html('<i class="fas fa-stop me-1"></i>停止錄音');

        this.speechRecognition.start();
        Utils.showNotification('語音識別已開始，請開始說話...', 'info');
    },

    /**
     * 停止語音輸入
     */
    stopVoiceInput: function () {
        this.isListening = false;
        $('#voiceInput').removeClass('btn-danger').addClass('btn-outline-info').html('<i class="fas fa-microphone me-1"></i>語音輸入');

        if (this.speechRecognition) {
            this.speechRecognition.stop();
        }
    },

    /**
     * 檢查麥克風權限
     */
    checkMicrophonePermission: function () {
        if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
            const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
            this.speechRecognition = new SpeechRecognition();
            this.speechRecognition.continuous = false;
            this.speechRecognition.interimResults = false;
            this.speechRecognition.lang = 'zh-TW';

            this.speechRecognition.onresult = (event) => {
                const transcript = event.results[0][0].transcript;
                $('#messageInput').val(transcript);
                this.updateConfirmButton();
                this.stopVoiceInput();
                Utils.showNotification('語音識別完成', 'success');
            };

            this.speechRecognition.onerror = (event) => {
                this.stopVoiceInput();
                Utils.showNotification(`語音識別錯誤: ${event.error}`, 'danger');
            };

            this.speechRecognition.onend = () => {
                this.stopVoiceInput();
            };
        } else {
            $('#voiceInput').prop('disabled', true).attr('title', '瀏覽器不支援語音識別');
        }
    },

    /**
     * 處理檔案上傳
     */
    handleFileUpload: function (file) {
        if (!file) return;

        // 檢查檔案類型
        const allowedTypes = ['application/pdf', 'application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'];
        if (!allowedTypes.includes(file.type)) {
            Utils.showNotification('請上傳PDF或Word文檔格式的履歷', 'warning');
            return;
        }

        // 檢查檔案大小 (5MB)
        if (file.size > 5 * 1024 * 1024) {
            Utils.showNotification('檔案大小不能超過5MB', 'warning');
            return;
        }

        Utils.showLoading('#fileUpload', '上傳中...');

        // 創建FormData
        const formData = new FormData();
        formData.append('file', file);

        // 上傳檔案
        $.ajax({
            url: '/api/upload',
            type: 'POST',
            data: formData,
            processData: false,
            contentType: false
        }).done((response) => {
            Utils.hideLoading('#fileUpload');
            if (response.success) {
                Utils.showNotification('履歷上傳成功！', 'success');
                this.displayMessage('我已經收到您的履歷檔案，正在分析中...', 'ai');

                // TODO: 處理解析後的履歷資料
                setTimeout(() => {
                    this.displayMessage('履歷分析完成！現在可以開始針對您的背景進行面試。', 'ai');
                }, 2000);
            }
        }).fail(() => {
            Utils.hideLoading('#fileUpload');
        });
    },

    /**
     * 確認輸入
     */
    confirmInput: function () {
        const message = $('#messageInput').val().trim();
        if (message) {
            this.sendMessage();
        }
    },

    /**
     * 更新確認按鈕狀態
     */
    updateConfirmButton: function () {
        const hasText = $('#messageInput').val().trim().length > 0;
        $('#confirmInput').prop('disabled', !hasText);
    },

    /**
     * 載入聊天記錄
     */
    loadChatHistory: function () {
        chatHistory = Storage.get('chatHistory', []);
        chatHistory.forEach(chat => {
            this.displayMessage(chat.user, 'user');
            this.displayMessage(chat.ai, 'ai');
        });
    },

    /**
     * 儲存聊天記錄
     */
    saveChatHistory: function () {
        Storage.set('chatHistory', chatHistory);
    },

    // 新增自動下一題判斷
    checkAutoNextQuestion: function (aiMessage) {
        if (!autoNextQuestion || !isInterviewActive) return;
        if (!aiMessage) return;
        const msg = aiMessage.toLowerCase();
        if (msg.includes('評分') || msg.includes('分析結果') || msg.includes('標準答案') || msg.includes('相似度')) {
            setTimeout(() => {
                this.showTypingIndicator();
                this.sendToMCP('給我一個面試問題').then((response) => {
                    this.hideTypingIndicator();
                    if (response && response.response) {
                        this.displayMessage(response.response, 'ai');
                    } else {
                        this.displayMessage('請回答下一個問題...', 'ai');
                    }
                }).catch(() => {
                    this.hideTypingIndicator();
                    this.displayMessage('請回答下一個問題...', 'ai');
                });
            }, 2000);
        }
    },

    // 新增結束面試功能
    endInterview: function () {
        if (!isInterviewActive) {
            Utils.showNotification('面試尚未開始', 'warning');
            return;
        }

        if (confirm('確定要結束面試嗎？')) {
            isInterviewActive = false;
            autoNextQuestion = false; // 關閉自動下一題
            $('#autoNextToggle').prop('checked', false);
            $('#interviewStatus').html('<i class="fas fa-circle me-1"></i>面試已結束').removeClass('bg-warning').addClass('bg-danger');
            $('#startInterview').prop('disabled', false).text('開始面試');

            this.displayMessage('🎯 面試已結束！感謝您的參與。', 'ai');
            Utils.showNotification('面試已結束', 'success');
        }
    },


};

// 當文檔就緒時初始化
$(document).ready(function () {
    InterviewManager.init();

    // 添加打字動畫CSS
    const typingCSS = `
        <style>
        .typing-animation {
            display: flex;
            align-items: center;
            height: 20px;
        }
        .typing-animation span {
            height: 8px;
            width: 8px;
            background-color: white;
            border-radius: 50%;
            display: inline-block;
            margin: 0 2px;
            animation: typing 1.4s infinite ease-in-out;
        }
        .typing-animation span:nth-child(1) { animation-delay: -0.32s; }
        .typing-animation span:nth-child(2) { animation-delay: -0.16s; }
        .typing-animation span:nth-child(3) { animation-delay: 0s; }
        
        @keyframes typing {
            0%, 80%, 100% { transform: scale(0.8); opacity: 0.5; }
            40% { transform: scale(1); opacity: 1; }
        }
        </style>
    `;
    $('head').append(typingCSS);
}); 