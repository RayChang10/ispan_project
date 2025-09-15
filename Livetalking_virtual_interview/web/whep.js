var pc = null;

function negotiate() {
    var host = window.location.hostname
    pc.addTransceiver('video', { direction: 'recvonly' });
    pc.addTransceiver('audio', { direction: 'recvonly' });
    return pc.createOffer().then((offer) => {
        return pc.setLocalDescription(offer);
    }).then(() => {
        // wait for ICE gathering to complete
        return new Promise((resolve) => {
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
    }).then(() => {
        var offer = pc.localDescription;
        return fetch("http://" + host + ":1985/rtc/v1/whep/?app=live&stream=livestream", {
            body: offer.sdp,
            headers: {
                'Content-Type': 'application/sdp'
            },
            method: 'POST'
        });
    }).then((response) => {
        console.log(response)
        return response.data;
    }).then((answer) => {
        return pc.setRemoteDescription({ sdp: answer, type: 'answer' });
    }).catch((e) => {
        console.error('WebRTC connection failed:', e);
        throw e; // 重新拋出錯誤，讓調用者處理
    });
}

function start() {
    var config = {
        sdpSemantics: 'unified-plan'
    };

    if (document.getElementById('use-stun').checked) {
        config.iceServers = [{ urls: ['stun:stun.l.google.com:19302'] }];
    }

    pc = new RTCPeerConnection(config);

    // connect audio / video
    pc.addEventListener('track', (evt) => {
        if (evt.track.kind == 'video') {
            document.getElementById('video').srcObject = evt.streams[0];
        } else {
            document.getElementById('audio').srcObject = evt.streams[0];
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
