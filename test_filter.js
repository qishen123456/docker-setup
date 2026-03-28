// 测试思考过程过滤功能
const formatAnalysis = (analysis) => {
    if (!analysis) return ''
    
    let formatted = analysis
    
    // 识别并处理思考过程、数据提取、分析过程类内容
    // 定义需要特殊处理的关键词模式（更精确的关键词）
    const processKeywords = [
        '我正在分析', '我需要', '我发现', '我观察到',
        '正在分析', '开始处理', '接下来', '思考过程',
        '第一步，', '第二步，', '第三步，', '最后，',
        '首先，', '其次，', '然后，',
        '通过分析，', '从数据中，', '根据分析，'
    ]
    
    // 创建正则表达式来匹配包含这些关键词的段落
    const keywordPattern = processKeywords.join('|')
    const processPattern = new RegExp(
        `(^.*(?:${keywordPattern}).*?(?:\\n|$))`,
        'gim'
    )
    
    console.log('关键词模式:', keywordPattern)
    console.log('正则表达式:', processPattern)
    
    // 将匹配到的思考过程内容用特殊样式包装
    formatted = formatted.replace(processPattern, (match) => {
        console.log('匹配到内容:', match)
        // 检查是否是完整的思考过程段落
        const lines = match.split('\n').filter(line => line.trim())
        if (lines.length > 0) {
            return `<div class="thinking-process">${match}</div>`
        }
        return match
    })
    
    return formatted
}

// 测试文本
const testText = `# 数据分析报告

我正在分析这些数据，首先需要提取关键信息。

通过分析，我发现了以下模式...

## 总体概述

根据查询结果，本次共获取到10条记录，主要特征如下：

1. 数据完整性较好
2. 时间分布均匀
3. 数值范围合理

## 详细分析

从结果中可以看出，数据呈现以下特点：

- 第一步：数据清洗完成
- 第二步：特征提取完成
- 第三步：模式识别完成

观察发现，这些数据具有明显的季节性特征。

正在处理统计信息...

## 结论

根据数据分析，我们得出以下结论。`

console.log('=== 测试开始 ===')
console.log('原始文本:')
console.log(testText)
console.log('\n=== 过滤结果 ===')
const result = formatAnalysis(testText)
console.log(result)
console.log('\n=== 分析结果 ===')
console.log('是否包含thinking-process:', result.includes('thinking-process'))
console.log('匹配的关键词数量:', (result.match(/thinking-process/g) || []).length)
console.log('=== 测试结束 ===')
