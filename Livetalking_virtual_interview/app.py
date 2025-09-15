###############################################################################
#  Copyright (C) 2024 LiveTalking@lipku https://github.com/lipku/LiveTalking
#  email: lipku@foxmail.com
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
###############################################################################

import sys

sys.stdout.reconfigure(encoding="utf-8")


import argparse
import asyncio
import base64
import gc
import json
import random
import os

# GPU 環境變數設置（在 logger 導入之前）
def setup_gpu_env_vars():
    """設置 GPU 環境變數"""
    # 設置 CUDA 相關環境變數
    os.environ["CUDA_VISIBLE_DEVICES"] = "0"  # 使用第一個 GPU
    os.environ["CUDA_LAUNCH_BLOCKING"] = "1"  # 同步執行，便於調試
    
    # 設置 PyTorch 相關環境變數
    os.environ["TORCH_CUDNN_V8_API_ENABLED"] = "1"  # 啟用 cuDNN v8
    os.environ["TORCH_CUDNN_V8_API_DISABLED"] = "0"
    
    # 設置 FFmpeg 硬體編碼器
    os.environ["FFMPEG_HWACCEL"] = "nvdec"
    os.environ["FFMPEG_VIDEO_CODEC"] = "h264_nvenc"
    os.environ["FFMPEG_AUDIO_CODEC"] = "aac"
    
    # 設置 NVIDIA 相關環境變數
    os.environ["NVIDIA_TF32_OVERRIDE"] = "1"  # 啟用 TF32 精度
    os.environ["CUDA_CACHE_DISABLE"] = "0"    # 啟用 CUDA 快取
    
    print("GPU 環境變數設置完成")

# 在導入其他模組之前設置 GPU 環境變數
setup_gpu_env_vars()

# import gevent
# from gevent import pywsgi
# from geventwebsocket.handler import WebSocketHandler
import re
import shutil
from threading import Event, Thread
from typing import Dict

import aiohttp
import aiohttp_cors
import numpy as np
import torch

# GPU 檢測和優化設置（在 torch 導入後）
def setup_gpu_optimization():
    """設置 GPU 優化配置"""
    if torch.cuda.is_available():
        # 設置 CUDA 優化選項
        torch.backends.cudnn.benchmark = True
        torch.backends.cudnn.deterministic = False
        torch.backends.cudnn.allow_tf32 = True
        
        print("GPU 優化設置完成 - 使用 CUDA")
        print(f"CUDA 版本: {torch.version.cuda}")
        print(f"cuDNN 版本: {torch.backends.cudnn.version()}")
        print(f"可用 GPU 數量: {torch.cuda.device_count()}")
        print(f"當前 GPU: {torch.cuda.get_device_name(0)}")
        
        return True
    else:
        # 檢查是否有 MPS (Apple Silicon)
        if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            print("GPU 優化設置完成 - 使用 MPS (Apple Silicon)")
            return True
        else:
            print("未檢測到 GPU，將使用 CPU 運行")
            return False

# 設置 GPU 優化
setup_gpu_optimization()

# import multiprocessing
import torch.multiprocessing as mp
from aiohttp import web
from aiortc import (
    RTCConfiguration,
    RTCIceServer,
    RTCPeerConnection,
    RTCSessionDescription,
)
from aiortc.rtcrtpsender import RTCRtpSender

# server.py
from flask import Flask, jsonify, render_template, request, send_from_directory
from flask_sockets import Sockets

from basereal import BaseReal
from llm import llm_response
from logger import logger
from webrtc import HumanPlayer

# # ---- force UTF-8 console on Windows (must run before importing logger) ----
# import sys, io, os
# if os.name == "nt":
#     try:
#         sys.stdout.reconfigure(encoding="utf-8", errors="replace")
#         sys.stderr.reconfigure(encoding="utf-8", errors="replace")
#     except Exception:
#         sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
#         sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
# # ---------------------------------------------------------------------------


app = Flask(__name__)
# sockets = Sockets(app)
# 安全的 session 管理類
class SafeSessionManager:
    def __init__(self):
        self._sessions: Dict[int, BaseReal] = {}
        self._lock = asyncio.Lock()
    
    async def set_session(self, sessionid: int, session: BaseReal):
        async with self._lock:
            self._sessions[sessionid] = session
    
    async def get_session(self, sessionid: int) -> BaseReal:
        async with self._lock:
            return self._sessions.get(sessionid)
    
    async def delete_session(self, sessionid: int) -> bool:
        async with self._lock:
            if sessionid in self._sessions:
                del self._sessions[sessionid]
                return True
            return False
    
    async def has_session(self, sessionid: int) -> bool:
        async with self._lock:
            return sessionid in self._sessions
    
    async def safe_operation(self, sessionid: int, operation, *args, **kwargs):
        """安全地執行操作，如果 session 不存在則返回 None"""
        session = await self.get_session(sessionid)
        if session is None:
            logger.warning(f"Session {sessionid} not found for operation {operation.__name__}")
            return None
        try:
            return operation(session, *args, **kwargs)
        except Exception as e:
            logger.error(f"Error in operation {operation.__name__} for session {sessionid}: {e}")
            return None

# 使用安全的 session 管理器
session_manager = SafeSessionManager()
nerfreals: Dict[int, BaseReal] = {}  # 保留原有變數以維持相容性
opt = None
model = None
avatar = None


#####webrtc###############################
pcs = set()


def randN(N) -> int:
    """生成长度为 N的随机数"""
    min = pow(10, N - 1)
    max = pow(10, N)
    return random.randint(min, max - 1)


def build_nerfreal(sessionid: int) -> BaseReal:
    opt.sessionid = sessionid
    if opt.model == "wav2lip":
        from lipreal import LipReal
        nerfreal = LipReal(opt, model, avatar)
        return nerfreal
    elif opt.model == "simple":
        # 簡化模式，創建一個基本的 BaseReal 實例
        from basereal import BaseReal
        try:
            # BaseReal 只接受 opt 參數，不需要 model 和 avatar
            nerfreal = BaseReal(opt)
            logger.info(f"Simple mode BaseReal created successfully for session {sessionid}")
            return nerfreal
        except Exception as e:
            logger.error(f"Failed to create BaseReal in simple mode: {e}")
            # 如果失敗，嘗試使用 wav2lip 作為備用
            from lipreal import LipReal
            nerfreal = LipReal(opt, model, avatar)
            return nerfreal
    else:
        # 預設模式
        from basereal import BaseReal
        nerfreal = BaseReal(opt)
        return nerfreal


# @app.route('/offer', methods=['POST'])
async def offer(request):
    params = await request.json()
    offer = RTCSessionDescription(sdp=params["sdp"], type=params["type"])

    # if len(nerfreals) >= opt.max_session:
    #     logger.info('reach max session')
    #     return web.Response(
    #         content_type="application/json",
    #         text=json.dumps(
    #             {"code": -1, "msg": "reach max session"}
    #         ),
    #     )
    sessionid = randN(6)  # len(nerfreals)
    nerfreals[sessionid] = None
    logger.info("sessionid=%d, session num=%d", sessionid, len(nerfreals))
    nerfreal = await asyncio.get_event_loop().run_in_executor(
        None, build_nerfreal, sessionid
    )
    nerfreals[sessionid] = nerfreal

    # ice_server = RTCIceServer(urls='stun:stun.l.google.com:19302')
    ice_server = RTCIceServer(urls="stun:stun.miwifi.com:3478")
    
    # GPU 優化的 WebRTC 配置
    rtc_config = RTCConfiguration(
        iceServers=[ice_server]
    )
    
    pc = RTCPeerConnection(configuration=rtc_config)
    pcs.add(pc)
    
    # GPU 硬體編碼器優化設置
    if torch.cuda.is_available():
        # 設置 FFmpeg 使用 NVIDIA 硬體編碼器
        os.environ["FFMPEG_HWACCEL"] = "nvdec"
        os.environ["FFMPEG_VIDEO_CODEC"] = "h264_nvenc"
        os.environ["FFMPEG_AUDIO_CODEC"] = "aac"
        
        # 設置 NVIDIA 編碼器參數
        os.environ["NVENC_PRESET"] = "p7"  # 最高品質預設
        os.environ["NVENC_TUNE"] = "hq"    # 高品質調優
        os.environ["NVENC_RC"] = "vbr"     # 可變位元率
        
        logger.info("已設置 NVIDIA 硬體編碼器環境變數")
    else:
        logger.info("使用軟體編碼器")

    @pc.on("connectionstatechange")
    async def on_connectionstatechange():
        logger.info("Connection state is %s" % pc.connectionState)
        if pc.connectionState == "failed":
            await pc.close()
            pcs.discard(pc)
            # 使用安全的 session 管理器刪除 session
            await session_manager.delete_session(sessionid)
            # 保持向後相容性
            if sessionid in nerfreals:
                del nerfreals[sessionid]
        if pc.connectionState == "closed":
            pcs.discard(pc)
            # 使用安全的 session 管理器刪除 session
            await session_manager.delete_session(sessionid)
            # 保持向後相容性
            if sessionid in nerfreals:
                del nerfreals[sessionid]
            gc.collect()

    player = HumanPlayer(nerfreals[sessionid])
    audio_sender = pc.addTrack(player.audio)
    video_sender = pc.addTrack(player.video)
    # GPU 優化的編碼器偏好設置
    capabilities = RTCRtpSender.getCapabilities("video")
    
    # 優先選擇 H.264 硬體編碼器
    h264_codecs = list(filter(lambda x: x.name == "H264", capabilities.codecs))
    vp8_codecs = list(filter(lambda x: x.name == "VP8", capabilities.codecs))
    rtx_codecs = list(filter(lambda x: x.name == "rtx", capabilities.codecs))
    
    # GPU 優化的編碼器選擇
    if torch.cuda.is_available() and h264_codecs:
        # 優先使用 H.264 硬體編碼器
        preferences = h264_codecs + rtx_codecs
        logger.info("GPU 模式：使用 H.264 硬體編碼器進行視訊編碼")
        
        # 設置硬體編碼器參數
        for codec in h264_codecs:
            if hasattr(codec, 'parameters'):
                codec.parameters['profile-level-id'] = '42e01f'  # H.264 High Profile
                codec.parameters['level-asymmetry-allowed'] = '1'
    else:
        # 備用編碼器
        preferences = vp8_codecs + rtx_codecs
        logger.info("使用 VP8 編碼器進行視訊編碼")
    
    # 設置編碼器偏好
    try:
        transceiver = pc.getTransceivers()[1]
        transceiver.setCodecPreferences(preferences)
        logger.info("WebRTC 編碼器偏好設置完成")
    except Exception as e:
        logger.warning(f"設置編碼器偏好失敗: {e}")

    try:
        await pc.setRemoteDescription(offer)
    except ValueError as e:
        if "ICE username fragment or password is missing" in str(e):
            logger.warning("SDP 缺少 ICE 憑證，嘗試修復...")
            # 創建一個新的 offer 對象，添加 ICE 憑證
            import re
            
            # 修復 SDP
            sdp = params["sdp"]
            if "a=ice-ufrag:" not in sdp:
                sdp += "\r\na=ice-ufrag:fixed123"
            if "a=ice-pwd:" not in sdp:
                sdp += "\r\na=ice-pwd:fixed456"
            
            # 創建修復後的 offer
            fixed_offer = RTCSessionDescription(sdp=sdp, type=params["type"])
            await pc.setRemoteDescription(fixed_offer)
            logger.info("SDP 修復成功")
        else:
            raise e

    answer = await pc.createAnswer()
    await pc.setLocalDescription(answer)

    # return jsonify({"sdp": pc.localDescription.sdp, "type": pc.localDescription.type})

    return web.Response(
        content_type="application/json",
        text=json.dumps(
            {
                "sdp": pc.localDescription.sdp,
                "type": pc.localDescription.type,
                "sessionid": sessionid,
            }
        ),
    )


async def human(request):
    try:
        params = await request.json()

        sessionid = params.get("sessionid", 0)
        if params.get("interrupt"):
            nerfreals[sessionid].flush_talk()

        if params["type"] == "echo":
            nerfreals[sessionid].put_msg_txt(params["text"])
        elif params["type"] == "chat":
            asyncio.get_event_loop().run_in_executor(
                None, llm_response, params["text"], nerfreals[sessionid]
            )
            # nerfreals[sessionid].put_msg_txt(res)

        return web.Response(
            content_type="application/json",
            text=json.dumps({"code": 0, "msg": "ok"}),
        )
    except Exception as e:
        logger.exception("exception:")
        return web.Response(
            content_type="application/json",
            text=json.dumps({"code": -1, "msg": str(e)}),
        )


async def interrupt_talk(request):
    try:
        params = await request.json()

        sessionid = params.get("sessionid", 0)
        nerfreals[sessionid].flush_talk()

        return web.Response(
            content_type="application/json",
            text=json.dumps({"code": 0, "msg": "ok"}),
        )
    except Exception as e:
        logger.exception("exception:")
        return web.Response(
            content_type="application/json",
            text=json.dumps({"code": -1, "msg": str(e)}),
        )


async def humanaudio(request):
    try:
        form = await request.post()
        sessionid = int(form.get("sessionid", 0))
        fileobj = form["file"]
        filename = fileobj.filename
        filebytes = fileobj.file.read()
        nerfreals[sessionid].put_audio_file(filebytes)

        return web.Response(
            content_type="application/json",
            text=json.dumps({"code": 0, "msg": "ok"}),
        )
    except Exception as e:
        logger.exception("exception:")
        return web.Response(
            content_type="application/json",
            text=json.dumps({"code": -1, "msg": str(e)}),
        )


async def set_audiotype(request):
    try:
        params = await request.json()

        sessionid = params.get("sessionid", 0)
        nerfreals[sessionid].set_custom_state(params["audiotype"], params["reinit"])

        return web.Response(
            content_type="application/json",
            text=json.dumps({"code": 0, "msg": "ok"}),
        )
    except Exception as e:
        logger.exception("exception:")
        return web.Response(
            content_type="application/json",
            text=json.dumps({"code": -1, "msg": str(e)}),
        )


async def record(request):
    try:
        params = await request.json()

        sessionid = params.get("sessionid", 0)
        if params["type"] == "start_record":
            # nerfreals[sessionid].put_msg_txt(params['text'])
            nerfreals[sessionid].start_recording()
        elif params["type"] == "end_record":
            nerfreals[sessionid].stop_recording()
        return web.Response(
            content_type="application/json",
            text=json.dumps({"code": 0, "msg": "ok"}),
        )
    except Exception as e:
        logger.exception("exception:")
        return web.Response(
            content_type="application/json",
            text=json.dumps({"code": -1, "msg": str(e)}),
        )


async def is_speaking(request):
    params = await request.json()

    sessionid = params.get("sessionid", 0)
    return web.Response(
        content_type="application/json",
        text=json.dumps({"code": 0, "data": nerfreals[sessionid].is_speaking()}),
    )


async def on_shutdown(app):
    # close peer connections
    coros = [pc.close() for pc in pcs]
    await asyncio.gather(*coros)
    pcs.clear()


async def post(url, data):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, data=data) as response:
                return await response.text()
    except aiohttp.ClientError as e:
        logger.info(f"Error: {e}")


async def run(push_url, sessionid):
    nerfreal = await asyncio.get_event_loop().run_in_executor(
        None, build_nerfreal, sessionid
    )
    nerfreals[sessionid] = nerfreal

    pc = RTCPeerConnection()
    pcs.add(pc)

    @pc.on("connectionstatechange")
    async def on_connectionstatechange():
        logger.info("Connection state is %s" % pc.connectionState)
        if pc.connectionState == "failed":
            await pc.close()
            pcs.discard(pc)

    player = HumanPlayer(nerfreals[sessionid])
    audio_sender = pc.addTrack(player.audio)
    video_sender = pc.addTrack(player.video)

    await pc.setLocalDescription(await pc.createOffer())
    answer = await post(push_url, pc.localDescription.sdp)
    await pc.setRemoteDescription(RTCSessionDescription(sdp=answer, type="answer"))


##########################################
# os.environ['MKL_SERVICE_FORCE_INTEL'] = '1'
# os.environ['MULTIPROCESSING_METHOD'] = 'forkserver'
if __name__ == "__main__":
    mp.set_start_method("spawn")
    parser = argparse.ArgumentParser()

    # audio FPS
    parser.add_argument("--fps", type=int, default=50, help="audio fps,must be 50")
    # sliding window left-middle-right length (unit: 20ms)
    parser.add_argument("-l", type=int, default=10)
    parser.add_argument("-m", type=int, default=8)
    parser.add_argument("-r", type=int, default=10)

    parser.add_argument("--W", type=int, default=450, help="GUI width")
    parser.add_argument("--H", type=int, default=450, help="GUI height")

    # musetalk opt
    parser.add_argument(
        "--avatar_id",
        type=str,
        default="avator_1",
        help="define which avatar in data/avatars",
    )
    # parser.add_argument('--bbox_shift', type=int, default=5)
    parser.add_argument("--batch_size", type=int, default=16, help="infer batch")

    parser.add_argument(
        "--customvideo_config", type=str, default="", help="custom action json"
    )

    parser.add_argument(
        "--tts", type=str, default="edgetts", help="tts service type"
    )  # xtts gpt-sovits cosyvoice
    parser.add_argument("--REF_FILE", type=str, default="zh-TW-HsiaoChenNeural")
    parser.add_argument("--REF_TEXT", type=str, default=None)
    parser.add_argument(
        "--TTS_SERVER", type=str, default="http://127.0.0.1:9880"
    )  # http://localhost:9000
    # parser.add_argument('--CHARACTER', type=str, default='test')
    # parser.add_argument('--EMOTION', type=str, default='default')

    parser.add_argument(
        "--model", type=str, default="musetalk"
    )  # musetalk wav2lip ultralight

    parser.add_argument(
        "--transport", type=str, default="rtcpush"
    )  # webrtc rtcpush virtualcam
    parser.add_argument(
        "--push_url",
        type=str,
        default="http://localhost:1985/rtc/v1/whip/?app=live&stream=livestream",
    )  # rtmp://localhost/live/livestream

    parser.add_argument("--max_session", type=int, default=1)  # multi session count
    parser.add_argument("--listenport", type=int, default=8010, help="web listen port")

    opt = parser.parse_args()
    # app.config.from_object(opt)
    # print(app.config)
    opt.customopt = []
    if opt.customvideo_config != "":
        with open(opt.customvideo_config, "r") as file:
            opt.customopt = json.load(file)

    # if opt.model == 'ernerf':
    #     from nerfreal import NeRFReal,load_model,load_avatar
    #     model = load_model(opt)
    #     avatar = load_avatar(opt)
    if opt.model == "musetalk":
        from musereal import MuseReal, load_avatar, load_model, warm_up

        logger.info(opt)
        model = load_model()
        avatar = load_avatar(opt.avatar_id)
        warm_up(opt.batch_size, model)
    elif opt.model == "wav2lip":
        from lipreal import LipReal, load_avatar, load_model, warm_up

        logger.info(opt)
        model = load_model("../models/wav2lip.pth")

        avatar = load_avatar(opt.avatar_id)
        warm_up(opt.batch_size, model, 256)
    elif opt.model == "ultralight":
        from lightreal import LightReal, load_avatar, load_model, warm_up

        logger.info(opt)
        model = load_model(opt)
        avatar = load_avatar(opt.avatar_id)
        warm_up(opt.batch_size, avatar, 160)

    # if opt.transport=='rtmp':
    #     thread_quit = Event()
    #     nerfreals[0] = build_nerfreal(0)
    #     rendthrd = Thread(target=nerfreals[0].render,args=(thread_quit,))
    #     rendthrd.start()
    if opt.transport == "virtualcam":
        thread_quit = Event()
        nerfreals[0] = build_nerfreal(0)
        rendthrd = Thread(target=nerfreals[0].render, args=(thread_quit,))
        rendthrd.start()

    #############################################################################
    appasync = web.Application(client_max_size=1024**2 * 100)
    appasync.on_shutdown.append(on_shutdown)
    appasync.router.add_post("/offer", offer)
    appasync.router.add_post("/human", human)
    appasync.router.add_post("/humanaudio", humanaudio)
    appasync.router.add_post("/set_audiotype", set_audiotype)
    appasync.router.add_post("/record", record)
    appasync.router.add_post("/interrupt_talk", interrupt_talk)
    appasync.router.add_post("/is_speaking", is_speaking)
    appasync.router.add_static("/", path="web")

    # Configure default CORS settings.
    cors = aiohttp_cors.setup(
        appasync,
        defaults={
            "*": aiohttp_cors.ResourceOptions(
                allow_credentials=True,
                expose_headers="*",
                allow_headers="*",
            )
        },
    )
    # Configure CORS on all routes.
    for route in list(appasync.router.routes()):
        cors.add(route)

    pagename = "webrtcapi.html"
    if opt.transport == "rtmp":
        pagename = "echoapi.html"
    elif opt.transport == "rtcpush":
        pagename = "rtcpushapi.html"
    logger.info(
        "start http server; http://<serverip>:" + str(opt.listenport) + "/" + pagename
    )
    logger.info(
        "If using WebRTC, open: http://<serverip>:%s/dashboard.html", opt.listenport
    )

    def run_server(runner):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(runner.setup())
        site = web.TCPSite(runner, "0.0.0.0", opt.listenport)
        loop.run_until_complete(site.start())
        if opt.transport == "rtcpush":
            for k in range(opt.max_session):
                push_url = opt.push_url
                if k != 0:
                    push_url = opt.push_url + str(k)
                loop.run_until_complete(run(push_url, k))
        loop.run_forever()

    # Thread(target=run_server, args=(web.AppRunner(appasync),)).start()
    run_server(web.AppRunner(appasync))

    # app.on_shutdown.append(on_shutdown)
    # app.router.add_post("/offer", offer)

    # print('start websocket server')
    # server = pywsgi.WSGIServer(('0.0.0.0', 8000), app, handler_class=WebSocketHandler)
    # server.serve_forever()
