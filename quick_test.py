import json

import requests

# 測試回答問題
data = {
    "message": "區塊鏈中的區塊是一個包含交易數據的數據結構，每個區塊都有唯一的哈希值來識別",
    "user_id": "test_user_123",
}

response = requests.post("http://localhost:5000/api/interview", json=data)
result = response.json()

print("📝 測試回答問題:")
print(f'✅ 請求成功: {result.get("success")}')
print(f'回應: {result.get("response", "")[:200]}...')
print(f'當前狀態: {result.get("current_state")}')
print(f'使用的代理: {result.get("agent_used")}')
