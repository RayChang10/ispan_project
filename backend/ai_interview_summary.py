def generate_ai_interview_summary(conversation_history, user_id):
    """使用AI生成動態的面試總結和評論"""
    try:
        # 分析對話歷史
        total_messages = len(conversation_history)
        user_messages = [msg for msg in conversation_history if msg.get('role') == 'user']
        assistant_messages = [msg for msg in conversation_history if msg.get('role') == 'assistant']
        
        # 統計問題數量
        question_count = sum(1 for msg in assistant_messages 
                           if '問題' in msg.get('content', '') or 'Question' in msg.get('content', ''))
        
        # 檢查是否有自我介紹
        has_intro = any('自我介紹' in msg.get('content', '') or '介紹' in msg.get('content', '') 
                       for msg in user_messages[:3])  # 檢查前3條用戶消息
        
        # 檢查是否有評分結果
        has_scoring = any('評分' in msg.get('content', '') or '分析結果' in msg.get('content', '') 
                         for msg in assistant_messages)
        
        # 構建AI提示
        conversation_text = "\n".join([
            f"{'用戶' if msg.get('role') == 'user' else '面試官'}: {msg.get('content', '')[:200]}"
            for msg in conversation_history[-10:]  # 只取最後10條消息避免過長
        ])
        
        prompt = f"""請基於以下面試對話記錄，生成一個個人化的面試總結和評論：

對話記錄：
{conversation_text}

統計信息：
- 總消息數：{total_messages}
- 用戶回應數：{len(user_messages)}
- 面試問題數：{question_count}
- 包含自我介紹：{'是' if has_intro else '否'}
- 有評分結果：{'是' if has_scoring else '否'}

請生成一個專業、個人化的面試總結，包括：
1. 面試表現亮點
2. 回答品質評估
3. 改進建議
4. 鼓勵性的結語

請用繁體中文回應，語氣專業但友善，字數控制在200-300字。"""

        # 調用AI生成評論
        try:
            # 這裡需要導入 call_ai_service 函數
            from fastapi_app import call_ai_service
            ai_response = call_ai_service(prompt, user_id, max_tokens=400)
            if ai_response and ai_response.strip():
                return f"🎯 **AI面試評論**\n\n{ai_response}\n\n✨ 感謝您使用JobMate360面試系統！"
            else:
                raise Exception("AI回應為空")
        except Exception as ai_error:
            print(f"AI調用失敗: {ai_error}")
            
            # AI調用失敗時的備用總結
            fallback_summary = f"""🎯 **面試總結**

📊 **本次面試表現：**
• 參與了 {len(user_messages)} 次互動
• 回答了 {question_count} 個面試問題
{"• 完成了自我介紹環節" if has_intro else "• 建議加強自我介紹準備"}
{"• 獲得了詳細的回答分析" if has_scoring else "• 建議多練習問答技巧"}

💡 **改進建議：**
• 繼續練習結構化的自我介紹
• 多準備技術問題的回答範例
• 保持積極主動的面試態度

🎉 **總評：** 您展現了良好的學習意願，建議持續練習以提升面試技巧！

✨ 感謝您使用JobMate360面試系統！"""
            
            return fallback_summary
            
    except Exception as e:
        print(f"生成面試總結時發生錯誤: {e}")
        return "🎯 **面試已完成！**\n\n感謝您的參與，系統正在為您準備個人化的建議和總結。"
