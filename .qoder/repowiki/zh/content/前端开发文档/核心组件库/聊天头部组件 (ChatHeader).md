我需要分析 ChatHeader 组件的代码。让我先尝试读取相关文件。

<tool_call>
<function=read_file>
<parameter=file_path>
frontend/src/components/smartask/ChatHeader.vue
</parameter>
</function>
</tool_call>
<tool_call>
<function=search_codebase>
<parameter=query>
ChatHeader component usage and props
</parameter>
<parameter=key_words>
ChatHeader,props,component
</parameter>
<parameter=search_scope>
frontend/src
</parameter>
</function>
</tool_call>
<tool_call>
<function=grep_code>
<parameter=regex>
ChatHeader
</parameter>
<parameter=path>
frontend/src
</parameter>
</function>
</tool_call>