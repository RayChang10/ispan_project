#!/usr/bin/env python3
###############################################################################
# GPU 性能監控腳本
# 用於監控 LiveTalking 系統的 GPU 使用情況
###############################################################################

import time
import psutil
import threading
from typing import Dict, List
import logging

try:
    import torch
    import pynvml
    GPU_AVAILABLE = True
except ImportError:
    GPU_AVAILABLE = False
    print("警告: 無法導入 GPU 監控模組")

logger = logging.getLogger(__name__)

class GPUMonitor:
    """GPU 性能監控器"""
    
    def __init__(self, interval: float = 1.0):
        self.interval = interval
        self.monitoring = False
        self.monitor_thread = None
        self.gpu_stats_history: List[Dict] = []
        self.max_history = 1000
        
        if GPU_AVAILABLE:
            self._init_nvml()
    
    def _init_nvml(self):
        """初始化 NVIDIA Management Library"""
        try:
            pynvml.nvmlInit()
            self.gpu_count = pynvml.nvmlDeviceGetCount()
            logger.info(f"檢測到 {self.gpu_count} 個 GPU 設備")
        except Exception as e:
            logger.error(f"NVML 初始化失敗: {e}")
            self.gpu_count = 0
    
    def get_gpu_stats(self) -> Dict:
        """獲取 GPU 統計信息"""
        if not GPU_AVAILABLE or self.gpu_count == 0:
            return {"error": "GPU 不可用"}
        
        try:
            stats = {
                "timestamp": time.time(),
                "gpus": []
            }
            
            for i in range(self.gpu_count):
                handle = pynvml.nvmlDeviceGetHandleByIndex(i)
                
                # 獲取 GPU 名稱
                name = pynvml.nvmlDeviceGetName(handle).decode('utf-8')
                
                # 獲取記憶體信息
                mem_info = pynvml.nvmlDeviceGetMemoryInfo(handle)
                total_memory = mem_info.total / 1024**3  # GB
                used_memory = mem_info.used / 1024**3   # GB
                free_memory = mem_info.free / 1024**3   # GB
                
                # 獲取 GPU 利用率
                utilization = pynvml.nvmlDeviceGetUtilizationRates(handle)
                gpu_util = utilization.gpu
                memory_util = utilization.memory
                
                # 獲取溫度
                try:
                    temperature = pynvml.nvmlDeviceGetTemperature(handle, pynvml.NVML_TEMPERATURE_GPU)
                except:
                    temperature = 0
                
                # 獲取風扇速度
                try:
                    fan_speed = pynvml.nvmlDeviceGetFanSpeed(handle)
                except:
                    fan_speed = 0
                
                gpu_stats = {
                    "index": i,
                    "name": name,
                    "memory": {
                        "total": round(total_memory, 2),
                        "used": round(used_memory, 2),
                        "free": round(free_memory, 2),
                        "utilization": memory_util
                    },
                    "utilization": gpu_util,
                    "temperature": temperature,
                    "fan_speed": fan_speed
                }
                
                stats["gpus"].append(gpu_stats)
            
            return stats
            
        except Exception as e:
            logger.error(f"獲取 GPU 統計信息失敗: {e}")
            return {"error": str(e)}
    
    def get_system_stats(self) -> Dict:
        """獲取系統統計信息"""
        try:
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            
            return {
                "timestamp": time.time(),
                "cpu": {
                    "percent": cpu_percent,
                    "count": psutil.cpu_count()
                },
                "memory": {
                    "total": round(memory.total / 1024**3, 2),
                    "used": round(memory.used / 1024**3, 2),
                    "free": round(memory.free / 1024**3, 2),
                    "percent": memory.percent
                }
            }
        except Exception as e:
            logger.error(f"獲取系統統計信息失敗: {e}")
            return {"error": str(e)}
    
    def start_monitoring(self):
        """開始監控"""
        if self.monitoring:
            logger.warning("監控已在運行中")
            return
        
        self.monitoring = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        logger.info("GPU 監控已啟動")
    
    def stop_monitoring(self):
        """停止監控"""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join()
        logger.info("GPU 監控已停止")
    
    def _monitor_loop(self):
        """監控循環"""
        while self.monitoring:
            try:
                # 獲取 GPU 統計信息
                gpu_stats = self.get_gpu_stats()
                if "error" not in gpu_stats:
                    self.gpu_stats_history.append(gpu_stats)
                    
                    # 限制歷史記錄數量
                    if len(self.gpu_stats_history) > self.max_history:
                        self.gpu_stats_history.pop(0)
                
                # 獲取系統統計信息
                system_stats = self.get_system_stats()
                
                # 顯示統計信息
                self._display_stats(gpu_stats, system_stats)
                
                time.sleep(self.interval)
                
            except Exception as e:
                logger.error(f"監控循環錯誤: {e}")
                time.sleep(self.interval)
    
    def _display_stats(self, gpu_stats: Dict, system_stats: Dict):
        """顯示統計信息"""
        if "error" in gpu_stats:
            return
        
        print("\n" + "="*60)
        print(f"時間: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        print("-"*60)
        
        # 系統信息
        if "error" not in system_stats:
            print(f"CPU 使用率: {system_stats['cpu']['percent']}%")
            print(f"記憶體使用率: {system_stats['memory']['percent']}%")
            print(f"記憶體: {system_stats['memory']['used']}/{system_stats['memory']['total']} GB")
        
        print("-"*60)
        
        # GPU 信息
        for gpu in gpu_stats["gpus"]:
            print(f"GPU {gpu['index']}: {gpu['name']}")
            print(f"  GPU 使用率: {gpu['utilization']}%")
            print(f"  記憶體使用率: {gpu['memory']['utilization']}%")
            print(f"  記憶體: {gpu['memory']['used']}/{gpu['memory']['total']} GB")
            print(f"  溫度: {gpu['temperature']}°C")
            print(f"  風扇: {gpu['fan_speed']}%")
            print()
    
    def get_performance_summary(self) -> Dict:
        """獲取性能摘要"""
        if not self.gpu_stats_history:
            return {"message": "無監控數據"}
        
        summary = {
            "monitoring_duration": len(self.gpu_stats_history) * self.interval,
            "gpu_count": len(self.gpu_stats_history[0]["gpus"]) if self.gpu_stats_history else 0,
            "peak_gpu_utilization": 0,
            "peak_memory_utilization": 0,
            "average_gpu_utilization": 0,
            "average_memory_utilization": 0
        }
        
        total_gpu_util = 0
        total_memory_util = 0
        count = 0
        
        for stats in self.gpu_stats_history:
            for gpu in stats["gpus"]:
                total_gpu_util += gpu["utilization"]
                total_memory_util += gpu["memory"]["utilization"]
                count += 1
                
                summary["peak_gpu_utilization"] = max(summary["peak_gpu_utilization"], gpu["utilization"])
                summary["peak_memory_utilization"] = max(summary["peak_memory_utilization"], gpu["memory"]["utilization"])
        
        if count > 0:
            summary["average_gpu_utilization"] = round(total_gpu_util / count, 2)
            summary["average_memory_utilization"] = round(total_memory_util / count, 2)
        
        return summary
    
    def save_report(self, filename: str = "gpu_performance_report.txt"):
        """保存性能報告"""
        try:
            summary = self.get_performance_summary()
            
            with open(filename, 'w', encoding='utf-8') as f:
                f.write("LiveTalking GPU 性能報告\n")
                f.write("="*50 + "\n\n")
                f.write(f"監控時長: {summary['monitoring_duration']:.1f} 秒\n")
                f.write(f"GPU 數量: {summary['gpu_count']}\n")
                f.write(f"峰值 GPU 使用率: {summary['peak_gpu_utilization']}%\n")
                f.write(f"峰值記憶體使用率: {summary['peak_memory_utilization']}%\n")
                f.write(f"平均 GPU 使用率: {summary['average_gpu_utilization']}%\n")
                f.write(f"平均記憶體使用率: {summary['average_memory_utilization']}%\n")
                
                f.write("\n詳細統計數據:\n")
                f.write("-"*30 + "\n")
                
                for i, stats in enumerate(self.gpu_stats_history):
                    f.write(f"\n時間點 {i+1}:\n")
                    for gpu in stats["gpus"]:
                        f.write(f"  GPU {gpu['index']}: {gpu['utilization']}% GPU, {gpu['memory']['utilization']}% 記憶體\n")
            
            logger.info(f"性能報告已保存到 {filename}")
            
        except Exception as e:
            logger.error(f"保存性能報告失敗: {e}")

def main():
    """主函數"""
    print("LiveTalking GPU 性能監控器")
    print("按 Ctrl+C 停止監控")
    
    monitor = GPUMonitor(interval=2.0)
    
    try:
        monitor.start_monitoring()
        
        # 保持主線程運行
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\n正在停止監控...")
        monitor.stop_monitoring()
        
        # 顯示性能摘要
        summary = monitor.get_performance_summary()
        print("\n性能摘要:")
        print(f"監控時長: {summary['monitoring_duration']:.1f} 秒")
        print(f"峰值 GPU 使用率: {summary['peak_gpu_utilization']}%")
        print(f"平均 GPU 使用率: {summary['average_gpu_utilization']}%")
        
        # 保存報告
        monitor.save_report()

if __name__ == "__main__":
    main()
