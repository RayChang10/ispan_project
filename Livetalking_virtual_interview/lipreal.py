
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

import math
import torch
import numpy as np

#from .utils import *
import os
import time
import cv2
import glob
import pickle
import copy
import sys

import queue
from queue import Queue
from threading import Thread, Event
import torch.multiprocessing as mp


from lipasr import LipASR
import asyncio
from av import AudioFrame, VideoFrame
from wav2lip.models import Wav2Lip
from basereal import BaseReal

#from imgcache import ImgCache

from tqdm import tqdm
from logger import logger

# 在模組導入時就創建假的 numpy._core 模組
try:
    import numpy.core as numpy_core
    import sys
    
    # 創建一個假的 numpy._core 模組，將所有引用重定向到 numpy.core
    class FakeNumpyCore:
        def __getattr__(self, name):
            return getattr(numpy_core, name)
    
    # 將假的模組注入到 sys.modules
    sys.modules['numpy._core'] = FakeNumpyCore()
    logger.info("成功創建假的 numpy._core 模組")
except Exception as e:
    logger.warning(f"創建假的 numpy._core 模組失敗: {e}")

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


# GPU 設備檢測和優化
def get_optimal_device():
    """獲取最佳的計算設備"""
    if torch.cuda.is_available():
        # CUDA 設備優化
        device = "cuda"
        
        # 設置 CUDA 優化選項
        torch.backends.cudnn.benchmark = True
        torch.backends.cudnn.deterministic = False
        torch.backends.cudnn.allow_tf32 = True
        
        # 設置記憶體分配策略
        torch.cuda.set_per_process_memory_fraction(0.9)  # 使用 90% 的 GPU 記憶體
        
        # 顯示 GPU 信息
        gpu_name = torch.cuda.get_device_name(0)
        gpu_memory = torch.cuda.get_device_properties(0).total_memory / 1024**3
        logger.info(f'使用 CUDA GPU: {gpu_name} ({gpu_memory:.1f} GB)')
        logger.info(f'CUDA 版本: {torch.version.cuda}')
        logger.info(f'cuDNN 版本: {torch.backends.cudnn.version()}')
        
    elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        # Apple Silicon MPS
        device = "mps"
        logger.info('使用 Apple Silicon MPS')
    else:
        # CPU 回退
        device = "cpu"
        logger.warning('未檢測到 GPU，使用 CPU 運行（性能較低）')
    
    return device

device = get_optimal_device()
print('Using {} for inference.'.format(device))
logger.info('Using {} for inference.'.format(device))

def _load(checkpoint_path):
	if device == 'cuda':
		checkpoint = torch.load(checkpoint_path) #,weights_only=True
	else:
		checkpoint = torch.load(checkpoint_path,
								map_location=lambda storage, loc: storage)
	return checkpoint

def load_model(path):
	model = Wav2Lip()
	logger.info("Load checkpoint from: {}".format(path))
	checkpoint = _load(path)
	s = checkpoint["state_dict"]
	new_s = {}
	for k, v in s.items():
		new_s[k.replace('module.', '')] = v
	model.load_state_dict(new_s)

	# GPU 優化的模型加載
	model = model.to(device)
	
	# GPU 特定優化
	if device == "cuda":
		# 啟用混合精度訓練
		model = model.half()  # 使用 FP16 以節省記憶體
		
		# 啟用 JIT 編譯以提升性能
		try:
			model = torch.jit.script(model)
			logger.info("模型 JIT 編譯完成")
		except Exception as e:
			logger.warning(f"JIT 編譯失敗: {e}")
		
		# 設置模型為評估模式
		model.eval()
		
		# 啟用 CUDA 圖形優化
		if hasattr(torch, 'cuda') and torch.cuda.is_available():
			model = torch.cuda.amp.autocast()(model)
			logger.info("啟用 CUDA 自動混合精度")
	
	return model

def load_avatar(avatar_id):
    avatar_path = f"/app/data/avatars/{avatar_id}"
    full_imgs_path = f"{avatar_path}/my_avatar/full_imgs" 
    face_imgs_path = f"{avatar_path}/my_avatar/face_imgs" 
    coords_path = f"{avatar_path}/my_avatar/coords.pkl"
    
    # 使用修復的 Unpickler 載入 coords.pkl
    class FixUnpickler(pickle.Unpickler):
        def find_class(self, module, name):
            # 將 numpy._core 重定向到 numpy.core
            if module.startswith("numpy._core"):
                module = module.replace("numpy._core", "numpy.core")
            return super().find_class(module, name)
    
    try:
        logger.info("嘗試載入 coords.pkl...")
        with open(coords_path, 'rb') as f:
            coord_list_cycle = FixUnpickler(f).load()
        logger.info("成功載入 coords.pkl")
    except Exception as e:
        logger.error(f"載入 coords.pkl 失敗: {e}")
        raise RuntimeError(f"無法載入 avatar 資料: {e}")
    input_img_list = glob.glob(os.path.join(full_imgs_path, '*.[jpJP][pnPN]*[gG]'))
    input_img_list = sorted(input_img_list, key=lambda x: int(os.path.splitext(os.path.basename(x))[0]))
    frame_list_cycle = read_imgs(input_img_list)
    #self.imagecache = ImgCache(len(self.coord_list_cycle),self.full_imgs_path,1000)
    input_face_list = glob.glob(os.path.join(face_imgs_path, '*.[jpJP][pnPN]*[gG]'))
    input_face_list = sorted(input_face_list, key=lambda x: int(os.path.splitext(os.path.basename(x))[0]))
    face_list_cycle = read_imgs(input_face_list)

    return frame_list_cycle,face_list_cycle,coord_list_cycle

@torch.no_grad()
def warm_up(batch_size,model,modelres):
    # 预热函数
    logger.info('warmup model...')
    img_batch = torch.ones(batch_size, 6, modelres, modelres).to(device)
    mel_batch = torch.ones(batch_size, 1, 80, 16).to(device)
    model(mel_batch, img_batch)

def read_imgs(img_list):
    frames = []
    logger.info('reading images...')
    for img_path in tqdm(img_list):
        frame = cv2.imread(img_path)
        frames.append(frame)
    return frames

def __mirror_index(size, index):
    #size = len(self.coord_list_cycle)
    turn = index // size
    res = index % size
    if turn % 2 == 0:
        return res
    else:
        return size - res - 1 

def inference(quit_event,batch_size,face_list_cycle,audio_feat_queue,audio_out_queue,res_frame_queue,model):
    
    #model = load_model("./models/wav2lip.pth")
    # input_face_list = glob.glob(os.path.join(face_imgs_path, '*.[jpJP][pnPN]*[gG]'))
    # input_face_list = sorted(input_face_list, key=lambda x: int(os.path.splitext(os.path.basename(x))[0]))
    # face_list_cycle = read_imgs(input_face_list)
    
    #input_latent_list_cycle = torch.load(latents_out_path)
    length = len(face_list_cycle)
    index = 0
    count=0
    counttime=0
    logger.info('start inference')
    while not quit_event.is_set():
        starttime=time.perf_counter()
        mel_batch = []
        try:
            mel_batch = audio_feat_queue.get(block=True, timeout=1)
        except queue.Empty:
            continue
            
        is_all_silence=True
        audio_frames = []
        for _ in range(batch_size*2):
            frame,type,eventpoint = audio_out_queue.get()
            audio_frames.append((frame,type,eventpoint))
            if type==0:
                is_all_silence=False

        if is_all_silence:
            for i in range(batch_size):
                res_frame_queue.put((None,__mirror_index(length,index),audio_frames[i*2:i*2+2]))
                index = index + 1
        else:
            # print('infer=======')
            t=time.perf_counter()
            img_batch = []
            for i in range(batch_size):
                idx = __mirror_index(length,index+i)
                face = face_list_cycle[idx]
                img_batch.append(face)
            img_batch, mel_batch = np.asarray(img_batch), np.asarray(mel_batch)

            img_masked = img_batch.copy()
            img_masked[:, face.shape[0]//2:] = 0

            img_batch = np.concatenate((img_masked, img_batch), axis=3) / 255.
            mel_batch = np.reshape(mel_batch, [len(mel_batch), mel_batch.shape[1], mel_batch.shape[2], 1])
            
            # GPU 優化的張量處理
            if device == "cuda":
                # 使用 FP16 以節省記憶體
                img_batch = torch.FloatTensor(np.transpose(img_batch, (0, 3, 1, 2))).half().to(device)
                mel_batch = torch.FloatTensor(np.transpose(mel_batch, (0, 3, 1, 2))).half().to(device)
            else:
                img_batch = torch.FloatTensor(np.transpose(img_batch, (0, 3, 1, 2))).to(device)
                mel_batch = torch.FloatTensor(np.transpose(mel_batch, (0, 3, 1, 2))).to(device)

            # GPU 優化的推理
            with torch.no_grad():
                if device == "cuda":
                    # 使用自動混合精度
                    with torch.cuda.amp.autocast():
                        pred = model(mel_batch, img_batch)
                else:
                    pred = model(mel_batch, img_batch)
            
            # 記憶體優化的結果處理
            pred = pred.cpu().numpy().transpose(0, 2, 3, 1) * 255.
            
            # GPU 記憶體清理
            if device == "cuda":
                del img_batch, mel_batch
                torch.cuda.empty_cache()

            counttime += (time.perf_counter() - t)
            count += batch_size
            #_totalframe += 1
            if count>=100:
                logger.info(f"------actual avg infer fps:{count/counttime:.4f}")
                count=0
                counttime=0
            for i,res_frame in enumerate(pred):
                #self.__pushmedia(res_frame,loop,audio_track,video_track)
                res_frame_queue.put((res_frame,__mirror_index(length,index),audio_frames[i*2:i*2+2]))
                index = index + 1
            #print('total batch time:',time.perf_counter()-starttime)            
    logger.info('lipreal inference processor stop')

class LipReal(BaseReal):
    @torch.no_grad()
    def __init__(self, opt, model, avatar):
        super().__init__(opt)
        #self.opt = opt # shared with the trainer's opt to support in-place modification of rendering parameters.
        # self.W = opt.W
        # self.H = opt.H

        self.fps = opt.fps # 20 ms per frame
        
        self.batch_size = opt.batch_size
        self.idx = 0
        self.res_frame_queue = Queue(self.batch_size*2)  #mp.Queue
        #self.__loadavatar()
        self.model = model
        self.frame_list_cycle,self.face_list_cycle,self.coord_list_cycle = avatar

        self.asr = LipASR(opt,self)
        self.asr.warm_up()
        
        self.render_event = mp.Event()
    
    def __del__(self):
        logger.info(f'lipreal({self.sessionid}) delete')


    def paste_back_frame(self, pred_frame, idx: int):
        raw = self.coord_list_cycle[idx]
        combine_frame = copy.deepcopy(self.frame_list_cycle[idx])
        H, W = combine_frame.shape[:2]

        # 兩種可能的次序：
        # A: (x1, y1, x2, y2)
        xa1, ya1, xa2, ya2 = raw
        xa1, ya1, xa2, ya2 = _safe_box(xa1, ya1, xa2, ya2, W, H)
        areaA = max(0, xa2 - xa1) * max(0, ya2 - ya1)

        # B: (y1, y2, x1, x2)  ← 這是原本 lipreal.py 的寫法
        yb1, yb2, xb1, xb2 = raw
        xb1, yb1, xb2, yb2 = _safe_box(xb1, yb1, xb2, yb2, W, H)
        areaB = max(0, xb2 - xb1) * max(0, yb2 - yb1)

        # 選較合理（面積較大）的詮釋
        if areaB > areaA:
            x1, y1, x2, y2 = xb1, yb1, xb2, yb2
        else:
            x1, y1, x2, y2 = xa1, ya1, xa2, ya2

        # 產生要貼回的區塊
        res_frame = pred_frame.astype(np.uint8)
        res_frame = _safe_resize(res_frame, x2 - x1, y2 - y1)
        combine_frame[y1:y2, x1:x2] = res_frame
        return combine_frame

            
    def render(self,quit_event,loop=None,audio_track=None,video_track=None):
        #if self.opt.asr:
        #     self.asr.warm_up()

        self.tts.render(quit_event)
        self.init_customindex()
        process_thread = Thread(target=self.process_frames, args=(quit_event,loop,audio_track,video_track))
        process_thread.start()

        Thread(target=inference, args=(quit_event,self.batch_size,self.face_list_cycle,
                                           self.asr.feat_queue,self.asr.output_queue,self.res_frame_queue,
                                           self.model,)).start()  #mp.Process

        #self.render_event.set() #start infer process render
        count=0
        totaltime=0
        _starttime=time.perf_counter()
        #_totalframe=0
        while not quit_event.is_set(): 
            # update texture every frame
            # audio stream thread...
            t = time.perf_counter()
            self.asr.run_step()

            # if video_track._queue.qsize()>=2*self.opt.batch_size:
            #     print('sleep qsize=',video_track._queue.qsize())
            #     time.sleep(0.04*video_track._queue.qsize()*0.8)
            if video_track and video_track._queue.qsize()>=5:
                logger.debug('sleep qsize=%d',video_track._queue.qsize())
                time.sleep(0.04*video_track._queue.qsize()*0.8)
                
            # delay = _starttime+_totalframe*0.04-time.perf_counter() #40ms
            # if delay > 0:
            #     time.sleep(delay)
        #self.render_event.clear() #end infer process render
        logger.info('lipreal thread stop')
            
