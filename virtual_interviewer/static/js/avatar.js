/**
 * 虛擬面試顧問 - 虛擬人控制模組 (Fay數字人整合)
 * 支援語音表情對嘴、TTS、唇形同步等功能
 */

// 虛擬人狀態管理
let avatarState = {
    isActive: false,
    currentEmotion: 'neutral',
    isSpeaking: false,
    isListening: false,
    fayConnected: false,
    websocketConnection: null
};

// Fay數字人管理器
const FayAvatarManager = {
    /**
     * 初始化Fay數字人系統
     */
    init: function() {
        this.bindEvents();
        this.initializeAvatarDisplay();
        console.log('🤖 Fay數字人管理器已初始化');
    },
    
    /**
     * 綁定事件監聽器
     */
    bindEvents: function() {
        // 啟動Fay連接按鈕
        $('#connectFay').on('click', () => {
            this.connectToFay();
        });
        
        // 表情控制按鈕
        $('.emotion-btn').on('click', (e) => {
            const emotion = $(e.currentTarget).data('emotion');
            this.setEmotion(emotion);
        });
        
        // 測試語音按鈕
        $('#testTTS').on('click', () => {
            this.testTextToSpeech();
        });
    },
    
    /**
     * 初始化虛擬人顯示
     */
    initializeAvatarDisplay: function() {
        const avatarContainer = $('.virtual-avatar');
        
        // 添加Fay控制面板
        const controlPanel = `
            <div class="fay-controls mt-3" style="display: none;">
                <div class="btn-group-vertical w-100" role="group">
                    <button type="button" class="btn btn-sm btn-outline-primary" id="connectFay">
                        <i class="fas fa-plug me-1"></i>連接Fay
                    </button>
                    <div class="btn-group mt-1" role="group">
                        <button type="button" class="btn btn-sm btn-outline-secondary emotion-btn" data-emotion="happy">
                            😊 開心
                        </button>
                        <button type="button" class="btn btn-sm btn-outline-secondary emotion-btn" data-emotion="sad">
                            😢 難過
                        </button>
                        <button type="button" class="btn btn-sm btn-outline-secondary emotion-btn" data-emotion="surprised">
                            😲 驚訝
                        </button>
                    </div>
                    <button type="button" class="btn btn-sm btn-outline-info mt-1" id="testTTS">
                        <i class="fas fa-volume-up me-1"></i>測試語音
                    </button>
                </div>
            </div>
        `;
        
        avatarContainer.append(controlPanel);
        
        // 顯示Fay控制面板 (開發模式)
        if (this.isDevelopmentMode()) {
            $('.fay-controls').show();
        }
    },
    
    /**
     * 連接到Fay系統
     */
    connectToFay: async function() {
        try {
            Utils.showLoading('#connectFay', '連接中...');
            
            const response = await API.post('/fay/integration', {
                command: 'start_conversation'
            });
            
            if (response.success) {
                avatarState.fayConnected = true;
                this.establishWebSocketConnection(response.websocket_url);
                this.updateConnectionStatus(true);
                Utils.showNotification('Fay數字人連接成功！', 'success');
            }
            
        } catch (error) {
            console.error('Fay連接失敗:', error);
            Utils.showNotification('Fay連接失敗，使用本地模式', 'warning');
        } finally {
            Utils.hideLoading('#connectFay');
        }
    },
    
    /**
     * 建立WebSocket連接
     */
    establishWebSocketConnection: function(websocketUrl) {
        try {
            avatarState.websocketConnection = new WebSocket(websocketUrl);
            
            avatarState.websocketConnection.onopen = () => {
                console.log('🌐 Fay WebSocket連接已建立');
                this.sendFayCommand('initialize', { avatar_type: 'interview_consultant' });
            };
            
            avatarState.websocketConnection.onmessage = (event) => {
                const data = JSON.parse(event.data);
                this.handleFayMessage(data);
            };
            
            avatarState.websocketConnection.onerror = (error) => {
                console.error('WebSocket錯誤:', error);
                this.updateConnectionStatus(false);
            };
            
            avatarState.websocketConnection.onclose = () => {
                console.log('WebSocket連接已關閉');
                avatarState.fayConnected = false;
                this.updateConnectionStatus(false);
            };
            
        } catch (error) {
            console.error('WebSocket建立失敗:', error);
        }
    },
    
    /**
     * 處理Fay系統訊息
     */
    handleFayMessage: function(data) {
        console.log('收到Fay訊息:', data);
        
        switch (data.type) {
            case 'speech_started':
                this.onSpeechStarted(data);
                break;
            case 'speech_ended':
                this.onSpeechEnded(data);
                break;
            case 'emotion_changed':
                this.onEmotionChanged(data);
                break;
            case 'lip_sync_data':
                this.onLipSyncData(data);
                break;
        }
    },
    
    /**
     * 讓虛擬人說話
     */
    speak: async function(text, options = {}) {
        try {
            const config = {
                text: text,
                voice: options.voice || 'zh-TW-female',
                emotion: options.emotion || avatarState.currentEmotion,
                speed: options.speed || 1.0
            };
            
            // 先調用TTS生成語音
            const ttsResponse = await API.post('/tts/generate', config);
            
            if (ttsResponse.success) {
                // 調用虛擬人說話API
                const avatarResponse = await API.post('/avatar/control', {
                    action: 'speak',
                    text: text,
                    audio_url: ttsResponse.audio_url,
                    voice_config: config
                });
                
                if (avatarResponse.success) {
                    avatarState.isSpeaking = true;
                    this.updateAvatarVisualState('speaking');
                    
                    // 如果有Fay連接，發送語音指令
                    if (avatarState.fayConnected) {
                        this.sendFayCommand('speak', {
                            text: text,
                            audio_url: ttsResponse.audio_url,
                            lip_sync_data: avatarResponse.lip_sync_data,
                            duration: ttsResponse.duration
                        });
                    }
                    
                    // 模擬語音播放完成
                    setTimeout(() => {
                        this.onSpeechEnded();
                    }, ttsResponse.duration * 1000);
                }
            }
            
        } catch (error) {
            console.error('虛擬人說話失敗:', error);
            Utils.showNotification('語音生成失敗', 'danger');
        }
    },
    
    /**
     * 設定虛擬人表情
     */
    setEmotion: async function(emotion, intensity = 0.8) {
        try {
            const response = await API.post('/avatar/control', {
                action: 'emotion',
                emotion: emotion,
                intensity: intensity
            });
            
            if (response.success) {
                avatarState.currentEmotion = emotion;
                this.updateAvatarVisualState('emotion', emotion);
                
                // 發送到Fay系統
                if (avatarState.fayConnected) {
                    this.sendFayCommand('set_emotion', {
                        emotion: emotion,
                        intensity: intensity
                    });
                }
                
                Utils.showNotification(`表情已切換為: ${emotion}`, 'info', 2000);
            }
            
        } catch (error) {
            console.error('設定表情失敗:', error);
        }
    },
    
    /**
     * 設定聆聽狀態
     */
    setListening: async function(isListening) {
        try {
            const action = isListening ? 'listen' : 'idle';
            const response = await API.post('/avatar/control', { action: action });
            
            if (response.success) {
                avatarState.isListening = isListening;
                this.updateAvatarVisualState(action);
                
                if (avatarState.fayConnected) {
                    this.sendFayCommand(action, {});
                }
            }
            
        } catch (error) {
            console.error('設定聆聽狀態失敗:', error);
        }
    },
    
    /**
     * 發送指令到Fay系統
     */
    sendFayCommand: function(command, data) {
        if (avatarState.websocketConnection && avatarState.fayConnected) {
            const message = {
                command: command,
                data: data,
                timestamp: new Date().toISOString()
            };
            
            avatarState.websocketConnection.send(JSON.stringify(message));
            console.log('發送Fay指令:', message);
        }
    },
    
    /**
     * 更新虛擬人視覺狀態
     */
    updateAvatarVisualState: function(state, extra = null) {
        const avatar = $('.virtual-avatar img');
        const statusElement = $('#interviewStatus');
        
        // 移除所有狀態類別
        avatar.removeClass('speaking listening idle emotion-happy emotion-sad emotion-surprised');
        
        switch (state) {
            case 'speaking':
                avatar.addClass('speaking');
                statusElement.html('<i class="fas fa-volume-up me-1"></i>AI正在說話');
                this.addSpeakingAnimation();
                break;
                
            case 'listening':
                avatar.addClass('listening');
                statusElement.html('<i class="fas fa-ear me-1"></i>AI正在聆聽');
                this.addListeningAnimation();
                break;
                
            case 'emotion':
                avatar.addClass(`emotion-${extra}`);
                statusElement.html(`<i class="fas fa-smile me-1"></i>表情: ${extra}`);
                break;
                
            case 'idle':
                avatar.addClass('idle');
                statusElement.html('<i class="fas fa-circle me-1"></i>準備就緒');
                this.addIdleAnimation();
                break;
        }
    },
    
    /**
     * 添加說話動畫
     */
    addSpeakingAnimation: function() {
        const avatar = $('.virtual-avatar');
        
        // 添加口型動畫效果
        avatar.find('img').css({
            'animation': 'speakingPulse 0.5s ease-in-out infinite alternate',
            'filter': 'brightness(1.1)'
        });
    },
    
    /**
     * 添加聆聽動畫
     */
    addListeningAnimation: function() {
        const avatar = $('.virtual-avatar');
        
        // 添加聆聽指示器
        if (!avatar.find('.listening-indicator').length) {
            avatar.append('<div class="listening-indicator">🎤</div>');
        }
        
        avatar.find('.listening-indicator').css({
            'position': 'absolute',
            'top': '10px',
            'right': '10px',
            'animation': 'pulse 1s infinite'
        });
    },
    
    /**
     * 添加待機動畫
     */
    addIdleAnimation: function() {
        const avatar = $('.virtual-avatar');
        
        // 移除其他動畫元素
        avatar.find('.listening-indicator').remove();
        avatar.find('img').css({
            'animation': 'float 3s ease-in-out infinite',
            'filter': 'none'
        });
    },
    
    /**
     * 語音開始事件
     */
    onSpeechStarted: function(data) {
        console.log('語音開始:', data);
        avatarState.isSpeaking = true;
        this.updateAvatarVisualState('speaking');
    },
    
    /**
     * 語音結束事件
     */
    onSpeechEnded: function(data) {
        console.log('語音結束:', data);
        avatarState.isSpeaking = false;
        this.updateAvatarVisualState('idle');
    },
    
    /**
     * 表情變化事件
     */
    onEmotionChanged: function(data) {
        console.log('表情變化:', data);
        avatarState.currentEmotion = data.emotion;
    },
    
    /**
     * 唇形同步資料事件
     */
    onLipSyncData: function(data) {
        console.log('唇形同步資料:', data);
        // TODO: 處理唇形同步視覺效果
    },
    
    /**
     * 更新連接狀態顯示
     */
    updateConnectionStatus: function(connected) {
        const button = $('#connectFay');
        const statusIcon = connected ? 'fas fa-check-circle' : 'fas fa-times-circle';
        const statusText = connected ? '已連接' : '連接Fay';
        const btnClass = connected ? 'btn-success' : 'btn-outline-primary';
        
        button.removeClass('btn-outline-primary btn-success')
              .addClass(btnClass)
              .html(`<i class="${statusIcon} me-1"></i>${statusText}`);
        
        avatarState.fayConnected = connected;
    },
    
    /**
     * 測試文字轉語音
     */
    testTextToSpeech: function() {
        const testText = "您好！我是您的虛擬面試顧問，很高興為您服務！";
        this.speak(testText, {
            emotion: 'happy',
            voice: 'zh-TW-female'
        });
    },
    
    /**
     * 檢查是否為開發模式
     */
    isDevelopmentMode: function() {
        return window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';
    },
    
    /**
     * 獲取當前狀態
     */
    getStatus: function() {
        return avatarState;
    }
};

// 整合到面試管理器
if (typeof InterviewManager !== 'undefined') {
    // 擴展InterviewManager的displayMessage方法
    const originalDisplayMessage = InterviewManager.displayMessage;
    
    InterviewManager.displayMessage = function(message, sender) {
        // 調用原有顯示方法
        originalDisplayMessage.call(this, message, sender);
        
        // 如果是AI訊息，讓虛擬人說話
        if (sender === 'ai' && FayAvatarManager) {
            setTimeout(() => {
                FayAvatarManager.speak(message, {
                    emotion: 'neutral',
                    voice: 'zh-TW-female'
                });
            }, 500);
        }
    };
}

// 添加必要的CSS動畫
const avatarCSS = `
    <style>
    @keyframes speakingPulse {
        from { transform: scale(1); }
        to { transform: scale(1.05); }
    }
    
    .virtual-avatar.speaking img {
        border: 2px solid #28a745;
        box-shadow: 0 0 20px rgba(40, 167, 69, 0.5);
    }
    
    .virtual-avatar.listening img {
        border: 2px solid #17a2b8;
        box-shadow: 0 0 20px rgba(23, 162, 184, 0.5);
    }
    
    .fay-controls {
        background: rgba(255, 255, 255, 0.9);
        border-radius: 10px;
        padding: 10px;
        backdrop-filter: blur(10px);
    }
    
    .emotion-happy img {
        filter: hue-rotate(45deg) brightness(1.2);
    }
    
    .emotion-sad img {
        filter: hue-rotate(220deg) brightness(0.8);
    }
    
    .emotion-surprised img {
        filter: contrast(1.3) brightness(1.1);
    }
    </style>
`;

// 文檔就緒時初始化
$(document).ready(function() {
    // 添加動畫CSS
    $('head').append(avatarCSS);
    
    // 初始化Fay虛擬人管理器
    FayAvatarManager.init();
    
    // 將管理器暴露到全域
    window.FayAvatarManager = FayAvatarManager;
    window.avatarState = avatarState;
    
    console.log('🎭 虛擬人系統已就緒，支援Fay數字人整合');
}); 