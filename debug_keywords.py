#!/usr/bin/env python3

# 模拟关键词匹配逻辑
question = "商用 分公司的业绩"
train_q = "今年商用事业部业绩分析"

# 简单的关键词提取
user_keywords = set()
train_keywords = set()

# 提取用户问题关键词
for word in ['商用', '分公司', '事业部', '业绩', '分析', '今年']:
    if word in question:
        user_keywords.add(word)

# 提取训练问题关键词  
for word in ['商用', '分公司', '事业部', '业绩', '分析', '今年']:
    if word in train_q:
        train_keywords.add(word)

print(f"用户问题: {question}")
print(f"训练问题: {train_q}")
print(f"用户关键词: {user_keywords}")
print(f"训练关键词: {train_keywords}")

# 计算关键词重叠度
if user_keywords and train_keywords:
    overlap = len(user_keywords.intersection(train_keywords))
    overlap_ratio = overlap / len(user_keywords)
    
    print(f"重叠关键词: {user_keywords.intersection(train_keywords)}")
    print(f"重叠数量: {overlap}")
    print(f"重叠度: {overlap_ratio:.2f}")
    
    # 如果重叠度超过50%，认为是匹配
    if overlap_ratio >= 0.5:
        print("✅ 匹配成功!")
    else:
        print("❌ 匹配失败，重叠度不足50%")
