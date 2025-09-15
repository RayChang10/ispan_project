#!/bin/bash
###############################################################################
# LiveTalking 快速啟動腳本
# 使用根目錄的 docker-compose 配置
###############################################################################

set -e

# 顏色定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}==========================================${NC}"
echo -e "${BLUE}LiveTalking 快速啟動腳本${NC}"
echo -e "${BLUE}==========================================${NC}"

# 檢查是否在正確的目錄
if [[ ! -f "../docker-compose.yml" ]]; then
    echo -e "${RED}錯誤: 請在專案根目錄執行此腳本${NC}"
    echo "當前目錄: $(pwd)"
    echo "請執行: cd .. && ./Livetalking_virtual_interview/quick-start.sh"
    exit 1
fi

# 檢查 Docker 是否運行
if ! docker info > /dev/null 2>&1; then
    echo -e "${RED}錯誤: Docker 未運行或無法連接${NC}"
    echo "請確保 Docker 服務正在運行"
    exit 1
fi

# 檢查 NVIDIA Container Toolkit
echo -e "${BLUE}檢查 NVIDIA Container Toolkit...${NC}"
if ! docker run --rm --gpus all nvidia/cuda:11.8-base-ubuntu20.04 nvidia-smi > /dev/null 2>&1; then
    echo -e "${YELLOW}警告: NVIDIA Container Toolkit 未正確配置${NC}"
    echo "GPU 功能可能無法正常工作"
    echo "請參考: https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html"
    echo ""
    echo -e "${YELLOW}是否繼續啟動 CPU 版本? (y/N)${NC}"
    read -p "請選擇: " choice
    if [[ ! $choice =~ ^[Yy]$ ]]; then
        echo "取消啟動"
        exit 1
    fi
    PROFILE="cpu"
else
    echo -e "${GREEN}NVIDIA Container Toolkit 檢查通過${NC}"
    echo ""
    echo -e "${BLUE}選擇啟動模式:${NC}"
    echo "1) GPU 版本 (推薦，需要 NVIDIA GPU)"
    echo "2) CPU 版本 (簡化版，無需 GPU)"
    echo "3) 完整版 (包含所有服務)"
    echo ""
    read -p "請選擇 (1-3): " choice
    
    case $choice in
        1) PROFILE="gpu" ;;
        2) PROFILE="cpu" ;;
        3) PROFILE="full" ;;
        *) echo "無效選擇，使用 GPU 版本"; PROFILE="gpu" ;;
    esac
fi

# 切換到根目錄
cd ..

echo -e "${GREEN}啟動 LiveTalking 服務...${NC}"
echo -e "${BLUE}使用 profile: ${PROFILE}${NC}"

# 啟動服務
docker-compose --profile $PROFILE up -d

echo -e "${GREEN}服務啟動完成！${NC}"
echo ""

# 顯示服務狀態
echo -e "${BLUE}服務狀態:${NC}"
docker-compose ps

echo ""

# 顯示訪問信息
if [[ "$PROFILE" == "gpu" || "$PROFILE" == "full" ]]; then
    echo -e "${GREEN}GPU 版本已啟動${NC}"
    echo -e "${BLUE}訪問地址: http://localhost:8010${NC}"
    echo -e "${BLUE}網路模式: host (解決 WebRTC 連接問題)${NC}"
    echo ""
    echo -e "${BLUE}查看 GPU 使用情況:${NC}"
    echo "docker exec fastmcp-livetalking nvidia-smi"
elif [[ "$PROFILE" == "cpu" ]]; then
    echo -e "${GREEN}CPU 版本已啟動${NC}"
    echo -e "${BLUE}訪問地址: http://localhost:8010${NC}"
    echo -e "${BLUE}網路模式: bridge${NC}"
fi

echo ""
echo -e "${BLUE}常用命令:${NC}"
echo "查看日誌: docker-compose logs -f livetalking"
echo "停止服務: docker-compose down"
echo "重啟服務: docker-compose restart"
echo "查看狀態: docker-compose ps"
echo "進入容器: docker exec -it fastmcp-livetalking bash"

echo ""
echo -e "${GREEN}LiveTalking 啟動成功！${NC}"
echo -e "${BLUE}請訪問上述地址開始使用${NC}"
