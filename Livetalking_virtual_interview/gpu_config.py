###############################################################################
# GPU 優化配置文件
# 用於 LiveTalking 虛擬面試系統的 GPU 加速優化
###############################################################################

import os
import torch
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

class GPUOptimizer:
    """GPU 優化器類"""
    
    def __init__(self):
        self.device = self._detect_device()
        self.optimization_config = self._get_optimization_config()
        self._apply_optimizations()
    
    def _detect_device(self) -> str:
        """檢測可用的計算設備"""
        if torch.cuda.is_available():
            return "cuda"
        elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            return "mps"
        else:
            return "cpu"
    
    def _get_optimization_config(self) -> Dict[str, Any]:
        """獲取 GPU 優化配置"""
        config = {
            "cuda": {
                "memory_fraction": 0.9,
                "cudnn_benchmark": True,
                "cudnn_deterministic": False,
                "cudnn_allow_tf32": True,
                "amp_enabled": True,
                "jit_enabled": True,
                "graph_optimization": True
            },
            "mps": {
                "memory_fraction": 0.8,
                "amp_enabled": False,
                "jit_enabled": False,
                "graph_optimization": False
            },
            "cpu": {
                "memory_fraction": 1.0,
                "amp_enabled": False,
                "jit_enabled": False,
                "graph_optimization": False
            }
        }
        return config
    
    def _apply_optimizations(self):
        """應用 GPU 優化設置"""
        if self.device == "cuda":
            self._apply_cuda_optimizations()
        elif self.device == "mps":
            self._apply_mps_optimizations()
        else:
            self._apply_cpu_optimizations()
    
    def _apply_cuda_optimizations(self):
        """應用 CUDA 特定優化"""
        try:
            # CUDA 記憶體管理
            torch.cuda.set_per_process_memory_fraction(
                self.optimization_config["cuda"]["memory_fraction"]
            )
            
            # cuDNN 優化
            torch.backends.cudnn.benchmark = self.optimization_config["cuda"]["cudnn_benchmark"]
            torch.backends.cudnn.deterministic = self.optimization_config["cuda"]["cudnn_deterministic"]
            torch.backends.cudnn.allow_tf32 = self.optimization_config["cuda"]["cudnn_allow_tf32"]
            
            # 清空 CUDA 快取
            torch.cuda.empty_cache()
            
            # 顯示 GPU 信息
            gpu_name = torch.cuda.get_device_name(0)
            gpu_memory = torch.cuda.get_device_properties(0).total_memory / 1024**3
            cuda_version = torch.version.cuda
            cudnn_version = torch.backends.cudnn.version()
            
            logger.info(f"CUDA GPU 優化已啟用:")
            logger.info(f"  設備: {gpu_name}")
            logger.info(f"  記憶體: {gpu_memory:.1f} GB")
            logger.info(f"  CUDA 版本: {cuda_version}")
            logger.info(f"  cuDNN 版本: {cudnn_version}")
            
        except Exception as e:
            logger.error(f"CUDA 優化設置失敗: {e}")
    
    def _apply_mps_optimizations(self):
        """應用 MPS 特定優化"""
        try:
            logger.info("Apple Silicon MPS 優化已啟用")
        except Exception as e:
            logger.error(f"MPS 優化設置失敗: {e}")
    
    def _apply_cpu_optimizations(self):
        """應用 CPU 特定優化"""
        logger.warning("未檢測到 GPU，將使用 CPU 運行（性能較低）")
    
    def get_device(self) -> str:
        """獲取當前設備"""
        return self.device
    
    def is_cuda_available(self) -> bool:
        """檢查 CUDA 是否可用"""
        return self.device == "cuda"
    
    def is_mps_available(self) -> bool:
        """檢查 MPS 是否可用"""
        return self.device == "mps"
    
    def optimize_model(self, model: torch.nn.Module) -> torch.nn.Module:
        """優化模型以提升 GPU 性能"""
        if self.device == "cuda":
            return self._optimize_cuda_model(model)
        elif self.device == "mps":
            return self._optimize_mps_model(model)
        else:
            return model
    
    def _optimize_cuda_model(self, model: torch.nn.Module) -> torch.nn.Module:
        """CUDA 模型優化"""
        try:
            # 啟用混合精度
            if self.optimization_config["cuda"]["amp_enabled"]:
                model = model.half()
                logger.info("模型已轉換為 FP16 以節省記憶體")
            
            # JIT 編譯優化
            if self.optimization_config["cuda"]["jit_enabled"]:
                try:
                    model = torch.jit.script(model)
                    logger.info("模型 JIT 編譯完成")
                except Exception as e:
                    logger.warning(f"JIT 編譯失敗: {e}")
            
            # 設置為評估模式
            model.eval()
            
            return model
            
        except Exception as e:
            logger.error(f"CUDA 模型優化失敗: {e}")
            return model
    
    def _optimize_mps_model(self, model: torch.nn.Module) -> torch.nn.Module:
        """MPS 模型優化"""
        try:
            model.eval()
            return model
        except Exception as e:
            logger.error(f"MPS 模型優化失敗: {e}")
            return model
    
    def setup_ffmpeg_gpu(self):
        """設置 FFmpeg GPU 硬體編碼器"""
        if self.device == "cuda":
            # NVIDIA 硬體編碼器設置
            os.environ["FFMPEG_HWACCEL"] = "nvdec"
            os.environ["FFMPEG_VIDEO_CODEC"] = "h264_nvenc"
            os.environ["FFMPEG_AUDIO_CODEC"] = "aac"
            
            # NVIDIA 編碼器參數
            os.environ["NVENC_PRESET"] = "p7"  # 最高品質預設
            os.environ["NVENC_TUNE"] = "hq"    # 高品質調優
            os.environ["NVENC_RC"] = "vbr"     # 可變位元率
            
            logger.info("FFmpeg NVIDIA 硬體編碼器已設置")
        else:
            logger.info("使用軟體編碼器")
    
    def get_memory_info(self) -> Dict[str, Any]:
        """獲取記憶體使用信息"""
        if self.device == "cuda":
            return {
                "total": torch.cuda.get_device_properties(0).total_memory / 1024**3,
                "allocated": torch.cuda.memory_allocated(0) / 1024**3,
                "cached": torch.cuda.memory_reserved(0) / 1024**3,
                "free": (torch.cuda.get_device_properties(0).total_memory - torch.cuda.memory_allocated(0)) / 1024**3
            }
        else:
            return {"message": "非 CUDA 設備，無法獲取記憶體信息"}

# 全局 GPU 優化器實例
gpu_optimizer = GPUOptimizer()

def get_gpu_optimizer() -> GPUOptimizer:
    """獲取全局 GPU 優化器實例"""
    return gpu_optimizer

def setup_gpu_environment():
    """設置 GPU 環境（向後相容性函數）"""
    return gpu_optimizer

if __name__ == "__main__":
    # 測試 GPU 優化器
    optimizer = GPUOptimizer()
    print(f"檢測到設備: {optimizer.get_device()}")
    print(f"CUDA 可用: {optimizer.is_cuda_available()}")
    
    if optimizer.is_cuda_available():
        memory_info = optimizer.get_memory_info()
        print(f"GPU 記憶體信息: {memory_info}")
