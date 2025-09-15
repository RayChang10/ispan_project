var pc = null;

async function negotiate() {
    // 安全檢查 pc 對象
    if (!pc) {
        throw new Error('RTCPeerConnection not initialized');
    }

    try {
        pc.addTransceiver('video', { direction: 'recvonly' });
        pc.addTransceiver('audio', { direction: 'recvonly' });

        const offer = await pc.createOffer();
        await pc.setLocalDescription(offer);

        // wait for ICE gathering to complete
        await new Promise((resolve) => {
            if (pc.iceGatheringState === 'complete') {
                resolve();
            } else {
                const checkState = () => {
                    if (pc.iceGatheringState === 'complete') {
                        pc.removeEventListener('icegatheringstatechange', checkState);
                        resolve();
                    }
                };
                pc.addEventListener('icegatheringstatechange', checkState);
            }
        });

        const localOffer = pc.localDescription;
        console.log('Local description:', localOffer);

        if (!localOffer || !localOffer.sdp) {
            throw new Error('Failed to create local description');
        }

        console.log('Sending offer to server:', {
            sdp: localOffer.sdp,
            type: localOffer.type
        });

        // 連接到 livetalking 服務的 WebRTC 端點
        // 首先嘗試直接連接 LiveTalking 服務，失敗時嘗試備用端點
        const host = window.location.hostname || 'localhost';
        const port = window.location.port || '5000';

        // 嘗試多個端點：直接 LiveTalking 服務和備用端點
        const endpoints = [
            `http://${host}:8010/offer`,
            `http://${host}:${port}/ltapi/offer`
        ];

        let lastError = null;
        const tryEndpoint = async (url) => {
            console.log(`嘗試連接端點: ${url}`);
            const response = await fetch(url, {
                body: JSON.stringify({
                    sdp: localOffer.sdp,
                    type: localOffer.type,
                }),
                headers: {
                    'Content-Type': 'application/json'
                },
                method: 'POST'
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            const data = await response.json();
            console.log(`端點 ${url} 連接成功:`, data);
            return data;
        };

        // 依序嘗試所有端點
        let answer = null;
        for (const endpoint of endpoints) {
            try {
                answer = await tryEndpoint(endpoint);
                break; // 成功則跳出循環
            } catch (error) {
                console.warn(`端點 ${endpoint} 連接失敗:`, error);
                lastError = error;
                continue;
            }
        }

        // 如果所有端點都失敗，拋出最後一個錯誤
        if (!answer) {
            throw new Error(`所有 WebRTC 端點都失敗了。最後錯誤: ${lastError?.message || 'Unknown error'}`);
        }

        console.log('Received answer from server:', answer);
        if (!answer || !answer.sdp) {
            throw new Error('Invalid answer from server');
        }

        // 安全檢查 sessionid 元素是否存在
        const sessionidElement = document.getElementById('sessionid');
        if (sessionidElement) {
            sessionidElement.value = answer.sessionid;
        }

        // 安全檢查 pc 對象是否存在
        if (!pc) {
            throw new Error('RTCPeerConnection is null');
        }

        await pc.setRemoteDescription(answer);
        console.log('WebRTC 連接成功建立');

    } catch (e) {
        console.error('WebRTC connection failed:', e);
        throw e; // 重新拋出錯誤，讓調用者處理
    }
}

function start() {
    // 檢查必要的 DOM 元素是否存在
    const videoElement = document.getElementById('video');
    let audioElement = document.getElementById('audio');

    // 如果 audio 元素不存在，嘗試創建一個
    if (!audioElement) {
        console.warn('Audio element not found, creating one...');
        audioElement = document.createElement('audio');
        audioElement.id = 'audio';
        audioElement.autoplay = true;
        audioElement.style.display = 'none';
        document.body.appendChild(audioElement);
    }

    if (!videoElement || !audioElement) {
        console.error('Required DOM elements not found');
        console.error('Video element:', !!videoElement);
        console.error('Audio element:', !!audioElement);
        throw new Error('頁面元素載入失敗，請重新整理頁面');
    }

    var config = {
        sdpSemantics: 'unified-plan',
        // 強制使用所有類型的候選
        iceCandidatePoolSize: 10,
        // 預設啟用 STUN 服務器來改善連接性
        iceServers: [
            { urls: ['stun:stun.l.google.com:19302'] },
            { urls: ['stun:stun1.l.google.com:19302'] },
            // 添加公共 TURN 服務器來處理 NAT 穿透問題
            {
                urls: ['turn:openrelay.metered.ca:80'],
                username: 'openrelayproject',
                credential: 'openrelayproject'
            }
        ]
    };

    // 允許使用者選擇性關閉 STUN
    const useStunCheckbox = document.getElementById('use-stun');
    if (useStunCheckbox && !useStunCheckbox.checked) {
        config.iceServers = [];
    }

    pc = new RTCPeerConnection(config);

    // 監控 ICE 連接狀態
    pc.addEventListener('iceconnectionstatechange', () => {
        console.log('ICE 連接狀態:', pc.iceConnectionState);
    });

    pc.addEventListener('connectionstatechange', () => {
        console.log('連接狀態:', pc.connectionState);
    });

    pc.addEventListener('icegatheringstatechange', () => {
        console.log('ICE 收集狀態:', pc.iceGatheringState);
    });

    // 監控 ICE 候選收集
    pc.addEventListener('icecandidate', (event) => {
        if (event.candidate) {
            console.log('收集到 ICE 候選:', event.candidate.type, event.candidate.candidate);
        }
    });

    // connect audio / video
    pc.addEventListener('track', (evt) => {
        if (evt.track.kind == 'video') {
            const videoElement = document.getElementById('video');
            if (videoElement) {
                videoElement.srcObject = evt.streams[0];
            } else {
                console.error('Video element not found');
            }
        } else {
            const audioElement = document.getElementById('audio');
            if (audioElement) {
                audioElement.srcObject = evt.streams[0];
            } else {
                console.error('Audio element not found');
            }
        }
    });

    // 啟動 WebRTC 連接（異步）
    return negotiate().catch((error) => {
        console.error('啟動 WebRTC 連接失敗:', error);
        throw error; // 重新拋出錯誤，讓調用者處理
    });
}

function stop() {
    // 安全地關閉 peer connection
    if (pc) {
        setTimeout(() => {
            pc.close();
            pc = null;
        }, 500);
    } else {
        console.warn('PeerConnection is already null');
    }
}

window.onunload = function (event) {
    // 在这里执行你想要的操作
    if (pc) {
        setTimeout(() => {
            pc.close();
            pc = null;
        }, 500);
    }
};

window.onbeforeunload = function (e) {
    if (pc) {
        setTimeout(() => {
            pc.close();
            pc = null;
        }, 500);
    }
    e = e || window.event
    // 兼容IE8和Firefox 4之前的版本
    if (e) {
        e.returnValue = '关闭提示'
    }
    // Chrome, Safari, Firefox 4+, Opera 12+ , IE 9+
    return '关闭提示'
}