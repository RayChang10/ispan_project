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
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
###############################################################################

import math
import torch
import numpy as np

# GPU 檢測和優化
def setup_gpu_optimization():
    """設置 GPU 優化選項"""
    if torch.cuda.is_available():
        # CUDA 優化設置
        torch.backends.cudnn.benchmark = True
        torch.backends.cudnn.deterministic = False
        torch.backends.cudnn.allow_tf32 = True
        
        # 設置記憶體分配策略
        torch.cuda.set_per_process_memory_fraction(0.9)
        
        # 啟用記憶體池
        torch.cuda.empty_cache()
        
        print(f"GPU 優化已啟用: {torch.cuda.get_device_name(0)}")
        return True
    return False

# 初始化 GPU 優化
setup_gpu_optimization()

import subprocess
import os
import time
import cv2
import glob
import resampy

import queue
from queue import Queue
from threading import Thread, Event
from io import BytesIO
import soundfile as sf

import asyncio
from av import AudioFrame, VideoFrame

import av
from fractions import Fraction

from ttsreal import EdgeTTS,SovitsTTS,XTTS,CosyVoiceTTS,FishTTS,TencentTTS,DoubaoTTS
from logger import logger


#-------------------------------
import cv2

def _clamp(v, lo, hi):
    return max(lo, min(hi, v))

def _safe_box(x1, y1, x2, y2, W, H):
    # 排序 & 邊界夾取
    x1, x2 = min(x1, x2), max(x1, x2)
    y1, y2 = min(y1, y2), max(y1, y2)
    x1 = _clamp(int(round(x1)), 0, W-1)
    y1 = _clamp(int(round(y1)), 0, H-1)
    x2 = _clamp(int(round(x2)), 0, W-1)
    y2 = _clamp(int(round(y2)), 0, H-1)
    # 至少 1×1，避免 0 尺寸
    if x2 == x1: x2 = min(x1+1, W-1)
    if y2 == y1: y2 = min(y1+1, H-1)
    return x1, y1, x2, y2

def _safe_resize(img, w, h):
    tw = max(1, int(round(w)))
    th = max(1, int(round(h)))
    return cv2.resize(img, (tw, th), interpolation=cv2.INTER_LINEAR)  # 注意順序 (W,H)
#-------------------------------

# 添加簡單的 ASR 類來處理 simple 模式
class SimpleASR:
    def __init__(self, opt, parent):
        self.opt = opt
        self.parent = parent
        self.feat_queue = Queue()
        self.output_queue = Queue()
        
    def warm_up(self):
        logger.info("SimpleASR warm up...")
        
    def put_audio_frame(self, audio_chunk, eventpoint=None):
        # 簡單模式下的音頻處理
        pass
        
    def flush_talk(self):
        # 簡單模式下的清空處理
        pass
        
    def run_step(self):
        # 簡單模式下的運行步驟
        pass

from tqdm import tqdm
def read_imgs(img_list):
    frames = []
    logger.info('reading images...')
    for img_path in tqdm(img_list):
        frame = cv2.imread(img_path)
        frames.append(frame)
    return frames

def play_audio(quit_event,queue):        
    import pyaudio
    p = pyaudio.PyAudio()
    stream = p.open(
        rate=16000,
        channels=1,
        format=8,
        output=True,
        output_device_index=1,
    )
    stream.start_stream()
    # while queue.qsize() <= 0:
    #     time.sleep(0.1)
    while not quit_event.is_set():
        stream.write(queue.get(block=True))
    stream.close()

class BaseReal:
    def __init__(self, opt):
        self.opt = opt
        self.sample_rate = 16000
        self.chunk = self.sample_rate // opt.fps # 320 samples per chunk (20ms * 16000 / 1000)
        self.sessionid = self.opt.sessionid

        # 初始化 TTS
        if opt.tts == "edgetts":
            self.tts = EdgeTTS(opt,self)
        elif opt.tts == "gpt-sovits":
            self.tts = SovitsTTS(opt,self)
        elif opt.tts == "xtts":
            self.tts = XTTS(opt,self)
        elif opt.tts == "cosyvoice":
            self.tts = CosyVoiceTTS(opt,self)
        elif opt.tts == "fishtts":
            self.tts = FishTTS(opt,self)
        elif opt.tts == "tencent":
            self.tts = TencentTTS(opt,self)
        elif opt.tts == "doubao":
            self.tts = DoubaoTTS(opt,self)
        else:
            # 如果沒有指定 TTS 或指定的不可用，創建一個簡單的 TTS 實例
            try:
                self.tts = EdgeTTS(opt,self)
            except Exception as e:
                logger.warning(f"Failed to initialize EdgeTTS: {e}, creating SimpleTTS")
                # 創建一個簡單的 TTS 類
                class SimpleTTS:
                    def __init__(self, opt, parent):
                        self.opt = opt
                        self.parent = parent
                    def put_msg_txt(self, msg, eventpoint=None):
                        logger.info(f"SimpleTTS: {msg}")
                    def flush_talk(self):
                        pass
                self.tts = SimpleTTS(opt, self)
        
        # 初始化 ASR - 使用簡單的 ASR 類
        self.asr = SimpleASR(opt, self)
        
        self.speaking = False

        self.recording = False
        self._record_video_pipe = None
        self._record_audio_pipe = None
        self.width = self.height = 0

        self.curr_state=0
        self.custom_img_cycle = {}
        self.custom_audio_cycle = {}
        self.custom_audio_index = {}
        self.custom_index = {}
        self.custom_opt = {}
        self.__loadcustom()

        # ===== NEW: 預設影格清單，延後載入 =====
        self.frame_list_cycle = []   # list[np.ndarray]

    def put_msg_txt(self,msg,eventpoint=None):
        self.tts.put_msg_txt(msg,eventpoint)
    
    def put_audio_frame(self,audio_chunk,eventpoint=None): #16khz 20ms pcm
        self.asr.put_audio_frame(audio_chunk,eventpoint)

    def put_audio_file(self,filebyte): 
        input_stream = BytesIO(filebyte)
        stream = self.__create_bytes_stream(input_stream)
        streamlen = stream.shape[0]
        idx=0
        while streamlen >= self.chunk:  #and self.state==State.RUNNING
            self.put_audio_frame(stream[idx:idx+self.chunk])
            streamlen -= self.chunk
            idx += self.chunk
    
    def __create_bytes_stream(self,byte_stream):
        #byte_stream=BytesIO(buffer)
        stream, sample_rate = sf.read(byte_stream) # [T*sample_rate,] float64
        logger.info(f'[INFO]put audio stream {sample_rate}: {stream.shape}')
        stream = stream.astype(np.float32)

        if stream.ndim > 1:
            logger.info(f'[WARN] audio has {stream.shape[1]} channels, only use the first.')
            stream = stream[:, 0]
    
        if sample_rate != self.sample_rate and stream.shape[0]>0:
            logger.info(f'[WARN] audio sample rate is {sample_rate}, resampling into {self.sample_rate}.')
            stream = resampy.resample(x=stream, sr_orig=sample_rate, sr_new=self.sample_rate)

        return stream

    def flush_talk(self):
        self.tts.flush_talk()
        self.asr.flush_talk()

    def is_speaking(self)->bool:
        return self.speaking
    
    def __loadcustom(self):
        for item in self.opt.customopt:
            logger.info(item)
            input_img_list = glob.glob(os.path.join(item['imgpath'], '*.[jpJP][pnPN]*[gG]'))
            input_img_list = sorted(input_img_list, key=lambda x: int(os.path.splitext(os.path.basename(x))[0]))
            self.custom_img_cycle[item['audiotype']] = read_imgs(input_img_list)
            self.custom_audio_cycle[item['audiotype']], sample_rate = sf.read(item['audiopath'], dtype='float32')
            self.custom_audio_index[item['audiotype']] = 0
            self.custom_index[item['audiotype']] = 0
            self.custom_opt[item['audiotype']] = item

    # ===== NEW: 載入 avatar 影格（優先 face_imgs，其次 body_imgs） =====
    def _resolve_avatar_dir(self) -> str:
        """
        取得 avatar 影格資料夾根目錄：
        1) 若 opt.avatar_dir 存在且有效 → 用它
        2) 否則預設用 Desktop\my_avatar
        """
        # 允許 app.py 傳入 --avatar_dir
        avatar_dir = getattr(self.opt, "avatar_dir", None)
        if avatar_dir and os.path.isdir(avatar_dir):
            return avatar_dir
        # 預設路徑（你現在的產物）
        default_dir = os.path.join(os.path.expanduser("~"), "Desktop", "my_avatar")
        return default_dir

    def _numeric_sort(self, paths):
        """以檔名中的數字排序，沒有數字時改用字典序。"""
        def key(p):
            base = os.path.splitext(os.path.basename(p))[0]
            try:
                return int(base)
            except:
                return base
        return sorted(paths, key=key)

    def _load_avatar_frames(self):
        """實際載入 face/body 影格為 np.ndarray 列表。找不到會留下空陣列並寫 log。"""
        avatar_dir = self._resolve_avatar_dir()
        face_dir = os.path.join(avatar_dir, "face_imgs")
        body_dir = os.path.join(avatar_dir, "body_imgs")

        face_paths = self._numeric_sort(glob.glob(os.path.join(face_dir, "*.png")))
        body_paths = self._numeric_sort(glob.glob(os.path.join(body_dir, "*.png")))

        paths = face_paths if len(face_paths) > 0 else body_paths

        if not paths:
            logger.error("No frames found. Checked: %s and %s", face_dir, body_dir)
            self.frame_list_cycle = []
            return

        frames = []
        for p in paths:
            im = cv2.imread(p)
            if im is None:
                continue
            frames.append(im)

        self.frame_list_cycle = frames
        logger.info("Loaded %d frames from %s", len(self.frame_list_cycle), (face_dir if len(face_paths)>0 else body_dir))

    def _ensure_frames_loaded(self, like_frame=None):
        """確保 self.frame_list_cycle 有內容；若沒有，嘗試載入；仍沒有就用黑畫面。"""
        if not self.frame_list_cycle:
            self._load_avatar_frames()
        if not self.frame_list_cycle:
            # 還是空：給一張黑畫面避免崩潰
            if like_frame is not None:
                h, w = like_frame.shape[:2]
            else:
                # 預設與你輸出的解析度相同
                w, h = 450, 614
            self.frame_list_cycle = [np.zeros((h, w, 3), dtype=np.uint8)]
            logger.warning("Fallback to a blank frame because no avatar frames were found.")

    def init_customindex(self):
        self.curr_state=0
        for key in self.custom_audio_index:
            self.custom_audio_index[key]=0
        for key in self.custom_index:
            self.custom_index[key]=0

    def notify(self,eventpoint):
        logger.info("notify:%s",eventpoint)

    def start_recording(self):
        """开始录制视频"""
        if self.recording:
            return

        # 檢查是否支援 NVIDIA 硬體編碼
        if os.environ.get("FFMPEG_VIDEO_CODEC") == "h264_nvenc":
            command = ['ffmpeg',
                        '-y', '-an',
                        '-f', 'rawvideo',
                        '-vcodec','rawvideo',
                        '-pix_fmt', 'bgr24', #像素格式
                        '-s', "{}x{}".format(self.width, self.height),
                        '-r', str(25),
                        '-i', '-',
                        '-pix_fmt', 'yuv420p', 
                        '-vcodec', "h264_nvenc",  # 使用 NVIDIA 硬體編碼器
                        '-preset', 'hq',          # 高品質預設
                        '-rc', 'vbr_hq',          # 高品質可變位元率
                        '-cq', '23',              # 品質參數
                        '-b:v', '5M',             # 目標位元率
                        '-maxrate', '10M',        # 最大位元率
                        '-bufsize', '10M',        # 緩衝區大小
                        '-zerolatency', '1',      # 零延遲模式
                        '-spatial-aq', '1',       # 啟用空間自適應量化
                        '-temporal-aq', '1',      # 啟用時間自適應量化
                        f'temp{self.opt.sessionid}.mp4']
        else:
            # 回退到軟體編碼
            command = ['ffmpeg',
                        '-y', '-an',
                        '-f', 'rawvideo',
                        '-vcodec','rawvideo',
                        '-pix_fmt', 'bgr24', #像素格式
                        '-s', "{}x{}".format(self.width, self.height),
                        '-r', str(25),
                        '-i', '-',
                        '-pix_fmt', 'yuv420p', 
                        '-vcodec', "h264",
                        f'temp{self.opt.sessionid}.mp4']
        self._record_video_pipe = subprocess.Popen(command, shell=False, stdin=subprocess.PIPE)

        # 檢查是否支援硬體音訊編碼
        if os.environ.get("FFMPEG_AUDIO_CODEC") == "aac":
            acommand = ['ffmpeg',
                        '-y', '-vn',
                        '-f', 's16le',
                        #'-acodec','pcm_s16le',
                        '-ac', '1',
                        '-ar', '16000',
                        '-i', '-',
                        '-acodec', 'aac',
                        '-b:a', '128k',             # 音訊位元率
                        '-profile:a', 'aac_low',    # AAC 低複雜度配置
                        f'temp{self.opt.sessionid}.aac']
        else:
            # 回退到預設音訊編碼
            acommand = ['ffmpeg',
                        '-y', '-vn',
                        '-f', 's16le',
                        #'-acodec','pcm_s16le',
                        '-ac', '1',
                        '-ar', '16000',
                        '-i', '-',
                        '-acodec', 'aac',
                        f'temp{self.opt.sessionid}.aac']
        self._record_audio_pipe = subprocess.Popen(acommand, shell=False, stdin=subprocess.PIPE)

        self.recording = True
        # self.recordq_video.queue.clear()
        # self.recordq_audio.queue.clear()
        # self.container = av.open(path, mode="w")
    
        # process_thread = Thread(target=self.record_frame, args=())
        # process_thread.start()
    
    def record_video_data(self,image):
        if self.width == 0:
            print("image.shape:",image.shape)
            self.height,self.width,_ = image.shape
        if self.recording:
            self._record_video_pipe.stdin.write(image.tostring())

    def record_audio_data(self,frame):
        if self.recording:
            self._record_audio_pipe.stdin.write(frame.tostring())
    
    # def record_frame(self): 
    #     videostream = self.container.add_stream("libx264", rate=25)
    #     videostream.codec_context.time_base = Fraction(1, 25)
    #     audiostream = self.container.add_stream("aac")
    #     audiostream.codec_context.time_base = Fraction(1, 16000)
    #     init = True
    #     framenum = 0       
    #     while self.recording:
    #         try:
    #             videoframe = self.recordq_video.get(block=True, timeout=1)
    #             videoframe.pts = framenum #int(round(framenum*0.04 / videostream.codec_context.time_base))
    #             videoframe.dts = videoframe.pts
    #             if init:
    #                 videostream.width = videoframe.width
    #                 videostream.height = videoframe.height
    #                 init = False
    #             for packet in videostream.encode(videoframe):
    #                 self.container.mux(packet)
    #             for k in range(2):
    #                 audioframe = self.recordq_audio.get(block=True, timeout=1)
    #                 audioframe.pts = int(round((framenum*2+k)*0.02 / audiostream.codec_context.time_base))
    #                 audioframe.dts = audioframe.pts
    #                 for packet in audiostream.encode(audioframe):
    #                     self.container.mux(packet)
    #             framenum += 1
    #         except queue.Empty:
    #             print('record queue empty,')
    #             continue
    #         except Exception as e:
    #             print(e)
    #             #break
    #     for packet in videostream.encode(None):
    #         self.container.mux(packet)
    #     for packet in audiostream.encode(None):
    #         self.container.mux(packet)
    #     self.container.close()
    #     self.recordq_video.queue.clear()
    #     self.recordq_audio.queue.clear()
    #     print('record thread stop')
		
    def stop_recording(self):
        """停止录制视频"""
        if not self.recording:
            return
        self.recording = False 
        self._record_video_pipe.stdin.close()  #wait() 
        self._record_video_pipe.wait()
        self._record_audio_pipe.stdin.close()
        self._record_audio_pipe.wait()
        # 使用硬體加速合併影片和音訊
        if os.environ.get("FFMPEG_HWACCEL") == "nvdec":
            cmd_combine_audio = f"ffmpeg -y -hwaccel cuda -hwaccel_output_format cuda -i temp{self.opt.sessionid}.aac -i temp{self.opt.sessionid}.mp4 -c:v copy -c:a copy -f mp4 data/record.mp4"
        else:
            cmd_combine_audio = f"ffmpeg -y -i temp{self.opt.sessionid}.aac -i temp{self.opt.sessionid}.mp4 -c:v copy -c:a copy data/record.mp4"
        os.system(cmd_combine_audio) 
        #os.remove(output_path)

    def mirror_index(self,size, index):
        #size = len(self.coord_list_cycle)
        turn = index // size
        res = index % size
        if turn % 2 == 0:
            return res
        else:
            return size - res - 1 
    
    def get_audio_stream(self,audiotype):
        idx = self.custom_audio_index[audiotype]
        stream = self.custom_audio_cycle[audiotype][idx:idx+self.chunk]
        self.custom_audio_index[audiotype] += self.chunk
        if self.custom_audio_index[audiotype]>=self.custom_audio_cycle[audiotype].shape[0]:
            self.curr_state = 1  #当前视频不循环播放，切换到静音状态
        return stream
    
    def set_custom_state(self,audiotype, reinit=True):
        print('set_custom_state:',audiotype)
        if self.custom_audio_index.get(audiotype) is None:
            return
        self.curr_state = audiotype
        if reinit:
            self.custom_audio_index[audiotype] = 0
            self.custom_index[audiotype] = 0

    def process_frames(self,quit_event,loop=None,audio_track=None,video_track=None):
        enable_transition = False  # 设置为False禁用过渡效果，True启用
        
        if enable_transition:
            _last_speaking = False
            _transition_start = time.time()
            _transition_duration = 0.1  # 过渡时间
            _last_silent_frame = None  # 静音帧缓存
            _last_speaking_frame = None  # 说话帧缓存
        
        if self.opt.transport=='virtualcam':
            import pyvirtualcam
            vircam = None

            audio_tmp = queue.Queue(maxsize=3000)
            audio_thread = Thread(target=play_audio, args=(quit_event,audio_tmp,), daemon=True, name="pyaudio_stream")
            audio_thread.start()
        
        while not quit_event.is_set():
            try:
                res_frame,idx,audio_frames = self.res_frame_queue.get(block=True, timeout=1)
            except queue.Empty:
                continue

            # ===== NEW: 每輪都確保已載到影格（第一次或外部尚未準備時）=====
            self._ensure_frames_loaded(like_frame=res_frame)

            if enable_transition:
                # 检测状态变化
                current_speaking = not (audio_frames[0][1]!=0 and audio_frames[1][1]!=0)
                if current_speaking != _last_speaking:
                    logger.info("state switch")
                    _transition_start = time.time()
                _last_speaking = current_speaking

            if audio_frames[0][1]!=0 and audio_frames[1][1]!=0: #全为静音数据，只需要取fullimg
                self.speaking = False
                audiotype = audio_frames[0][1]
                if self.custom_index.get(audiotype) is not None: #有自定义视频
                    mirindex = self.mirror_index(len(self.custom_img_cycle[audiotype]),self.custom_index[audiotype])
                    target_frame = self.custom_img_cycle[audiotype][mirindex]
                    self.custom_index[audiotype] += 1
                else:
                    # ===== FIX: 安全取值（len 一定 > 0）=====
                    n = len(self.frame_list_cycle)
                    idx_mod = idx % n
                    target_frame = self.frame_list_cycle[idx_mod]

                if enable_transition:
                    # 过渡效果（可關）
                    if time.time() - _transition_start < _transition_duration and _last_speaking_frame is not None:
                        alpha = min(1.0, (time.time() - _transition_start) / _transition_duration)
                        combine_frame = cv2.addWeighted(_last_speaking_frame, 1-alpha, target_frame, alpha, 0)
                    else:
                        combine_frame = target_frame
                    _last_silent_frame = combine_frame.copy()
                else:
                    combine_frame = target_frame
            else:
                self.speaking = True
                try:
                    current_frame = self.paste_back_frame(res_frame,idx)
                except Exception as e:
                    logger.warning(f"paste_back_frame error: {e}")
                    continue
                if enable_transition:
                    if time.time() - _transition_start < _transition_duration and _last_silent_frame is not None:
                        alpha = min(1.0, (time.time() - _transition_start) / _transition_duration)
                        combine_frame = cv2.addWeighted(_last_silent_frame, 1-alpha, current_frame, alpha, 0)
                    else:
                        combine_frame = current_frame
                    _last_speaking_frame = combine_frame.copy()
                else:
                    combine_frame = current_frame

            cv2.putText(combine_frame, "LiveTalking", (10, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.3, (128,128,128), 1)
            if self.opt.transport=='virtualcam':
                if vircam==None:
                    height, width,_= combine_frame.shape
                    vircam = pyvirtualcam.Camera(width=width, height=height, fps=25, fmt=pyvirtualcam.PixelFormat.BGR,print_fps=True)
                vircam.send(combine_frame)
            else: #webrtc
                image = combine_frame

                # ★ 最小補丁：若寬/高為奇數，補 1px 黑邊 → 變偶數，避免 libx264 報錯
                h, w = image.shape[:2]
                if (h % 2) or (w % 2):
                    image = cv2.copyMakeBorder(image, 0, h % 2, 0, w % 2,
                                            cv2.BORDER_CONSTANT, value=(0, 0, 0))

                new_frame = VideoFrame.from_ndarray(image, format="bgr24")
                asyncio.run_coroutine_threadsafe(video_track._queue.put((new_frame, None)), loop)
                self.record_video_data(image)  # 用補過的影像


            for audio_frame in audio_frames:
                frame,type,eventpoint = audio_frame
                frame = (frame * 32767).astype(np.int16)

                if self.opt.transport=='virtualcam':
                    audio_tmp.put(frame.tobytes()) #TODO
                else: #webrtc
                    new_frame = AudioFrame(format='s16', layout='mono', samples=frame.shape[0])
                    new_frame.planes[0].update(frame.tobytes())
                    new_frame.sample_rate=16000
                    asyncio.run_coroutine_threadsafe(audio_track._queue.put((new_frame,eventpoint)), loop)
                self.record_audio_data(frame)
            if self.opt.transport=='virtualcam':
                vircam.sleep_until_next_frame()
        if self.opt.transport=='virtualcam':
            audio_thread.join()
            vircam.close()
        logger.info('basereal process_frames thread stop') 
    
    # def process_custom(self,audiotype:int,idx:int):
    #     if self.curr_state!=audiotype: #从推理切到口播
    #         if idx in self.switch_pos:  #在卡点位置可以切换
    #             self.curr_state=audiotype
    #             self.custom_index=0
    #     else:
    #         self.custom_index+=1
