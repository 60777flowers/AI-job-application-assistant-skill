#!/usr/bin/env python3
"""
统一 LLM 客户端 — 支持 DeepSeek / Kimi(Moonshot) / Qwen(DashScope)
三家均兼容 OpenAI API 格式，用 urllib 实现，无需额外依赖。

用法:
  from llm_client import LLMClient
  client = LLMClient(provider="deepseek", api_key="sk-...", model="deepseek-chat")
  reply = client.chat("你好")
"""

import json
import urllib.request
import urllib.error


# ── 各供应商配置 ─────────────────────────────────────────
PROVIDERS = {
    "deepseek": {
        "name": "DeepSeek",
        "url": "https://api.deepseek.com/v1/chat/completions",
        "models": ["deepseek-chat", "deepseek-reasoner"],
        "default_model": "deepseek-chat",
    },
    "kimi": {
        "name": "Kimi (Moonshot)",
        "url": "https://api.moonshot.cn/v1/chat/completions",
        "models": ["moonshot-v1-8k", "moonshot-v1-32k", "moonshot-v1-128k"],
        "default_model": "moonshot-v1-8k",
    },
    "qwen": {
        "name": "Qwen (通义千问)",
        "url": "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions",
        "models": ["qwen-plus", "qwen-turbo", "qwen-max"],
        "default_model": "qwen-plus",
    },
}


class LLMClient:
    """统一的 LLM 客户端"""

    def __init__(self, provider="deepseek", api_key="", model=None):
        if provider not in PROVIDERS:
            raise ValueError(f"不支持的供应商: {provider}，可选: {list(PROVIDERS.keys())}")
        self.provider = provider
        self.api_key = api_key
        self.model = model or PROVIDERS[provider]["default_model"]
        self.url = PROVIDERS[provider]["url"]

    def chat(self, messages, temperature=0.7, max_tokens=4096, timeout=60):
        """
        调用 LLM 对话接口

        Args:
            messages: [{"role": "system"/"user"/"assistant", "content": "..."}]
            temperature: 温度
            max_tokens: 最大输出token数
            timeout: 超时秒数

        Returns:
            LLM 回复文本
        """
        if not self.api_key:
            raise ValueError("API Key 未配置，请在设置页面填写")

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(
            self.url,
            data=body,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                result = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8", errors="replace")
            try:
                err_msg = json.loads(err_body).get("error", {}).get("message", err_body)
            except (json.JSONDecodeError, ValueError):
                err_msg = err_body
            raise Exception(f"LLM API 错误 (HTTP {e.code}): {err_msg}")
        except urllib.error.URLError as e:
            raise Exception(f"无法连接 LLM API: {e.reason}")

        # 提取回复文本
        try:
            content = result["choices"][0]["message"]["content"]
            return content
        except (KeyError, IndexError):
            raise Exception(f"LLM 返回格式异常: {result}")

    def chat_json(self, messages, temperature=0.3, max_tokens=4096, timeout=60):
        """
        调用 LLM 并解析 JSON 回复
        在 system prompt 中要求返回 JSON，此处自动提取。
        """
        raw = self.chat(messages, temperature=temperature, max_tokens=max_tokens, timeout=timeout)
        # 尝试提取 JSON（可能被 ```json ... ``` 包裹）
        text = raw.strip()
        if text.startswith("```"):
            # 去掉 markdown 代码块
            lines = text.split("\n")
            lines = [l for l in lines if not l.strip().startswith("```")]
            text = "\n".join(lines)
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            # 尝试找到第一个 { 和最后一个 }
            start = text.find("{")
            end = text.rfind("}")
            if start != -1 and end != -1:
                try:
                    return json.loads(text[start:end + 1])
                except json.JSONDecodeError:
                    pass
            raise Exception(f"LLM 返回不是有效 JSON: {raw[:500]}")


def get_provider_info():
    """返回所有供应商信息（供前端展示）"""
    return PROVIDERS
