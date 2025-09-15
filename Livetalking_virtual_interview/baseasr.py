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

import queue
import time
from queue import Queue
from threading import Event, Thread

import numpy as np
import torch

from logger import logger


class BaseASR:
    def __init__(self, opt, parent):
        self.opt = opt
        self.parent = parent
        self.fps = opt.fps
        self.batch_size = opt.batch_size

        # 音訊處理參數
        self.stride_left_size = opt.l
        self.stride_middle_size = opt.m
        self.stride_right_size = opt.r

        # 音訊佇列
        self.feat_queue = Queue()
        self.output_queue = Queue()

        # 音訊幀緩存
        self.frames = []

        # 音訊輸入佇列
        self.input_queue = Queue()

        # 狀態控制
        self.quit_event = Event()

    def warm_up(self):
        """預熱函數"""
        logger.info("LipASR warm up...")

    def get_audio_frame(self):
        """獲取音訊幀 - 預設返回靜音幀"""
        # 預設返回靜音幀 (type=1 表示靜音)
        return np.zeros(320, dtype=np.float32), 1, None

    def run_step(self):
        """運行一步音訊處理"""
        pass

    def put_audio_file(self, audio_bytes):
        """放入音訊檔案"""
        pass

    def put_msg_txt(self, text, eventpoint=None):
        """放入文字訊息"""
        pass

    def flush_talk(self):
        """清空對話"""
        pass
