from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from fastmcp import FastMCP
import os

mcp = FastMCP("DeepSeek Price Assistant")
TZ = ZoneInfo("Asia/Shanghai")
def now_bj():
    return datetime.now(TZ)

@mcp.tool()
def deepseek_clock_now() -> str:
    """获取服务器当前北京时间，精确到秒。"""
    now = now_bj()
    return (
        f"当前北京时间：{now:%Y-%m-%d %H:%M:%S}\n"
        f"星期：{['周一','周二','周三','周四','周五','周六','周日'][now.weekday()]}\n"
        f"UTC偏移：{now.strftime('%z')}\n"
        f"Unix时间戳：{int(now.timestamp())}"
    )

PRICES = {
    "cache_hit_input": {"peak": 0.04, "off_peak": 0.02},
    "cache_miss_input": {"peak": 2.00, "off_peak": 1.00},
    "output": {"peak": 8.00, "off_peak": 4.00},
}

def is_peak(dt):
    if dt.weekday() >= 5:
        return False
    t = dt.hour * 60 + dt.minute
    return (9 * 60 <= t < 12 * 60 or 14 * 60 <= t < 18 * 60)

def next_transition(dt):
    candidates = []
    for day_offset in range(8):
        d = (dt + timedelta(days=day_offset)).date()
        for h, m in [(9, 0), (12, 0), (14, 0), (18, 0)]:
            x = datetime(d.year, d.month, d.day, h, m, tzinfo=TZ)
            if x > dt:
                candidates.append(x)
    return min(candidates)

def fmt_minutes(seconds):
    mins = max(0, int(seconds // 60))
    if mins < 60:
        return f"{mins} 分钟"
    return f"{mins // 60} 小时 {mins % 60} 分钟"

@mcp.tool()
def deepseek_price_now() -> str:
    """查询当前北京时间下 DeepSeek API 是高峰还是低谷，并返回当前价格。"""
    now = datetime.now(TZ)
    peak = is_peak(now)
    state = "高峰 🔴" if peak else "低谷 🟢"
    p = "peak" if peak else "off_peak"
    nxt = next_transition(now)
    return (
        f"当前北京时间：{now:%Y-%m-%d %H:%M:%S}\n"
        f"当前时段：{state}\n"
        f"下一次时段切换：{nxt:%Y-%m-%d %H:%M}"
        f"（约 {fmt_minutes((nxt-now).total_seconds())} 后）\n\n"
        "DeepSeek V4.1-Flash 价格（请以官方最新价格为准）：\n"
        f"- 缓存命中输入：¥{PRICES['cache_hit_input'][p]:.2f}\n"
        f"- 缓存未命中输入：¥{PRICES['cache_miss_input'][p]:.2f}\n"
        f"- 输出：¥{PRICES['output'][p]:.2f}\n\n"
        "高峰：周一至周五 09:00–12:00、14:00–18:00（北京时间）。"
        "其余时间为低谷。"
    )

@mcp.tool()
def deepseek_price_schedule(days: int = 7) -> str:
    """查询未来 1 到 14 天的 DeepSeek API 峰谷时间。"""
    days = max(1, min(int(days), 14))
    now = datetime.now(TZ)
    weekdays = ["周一","周二","周三","周四","周五","周六","周日"]
    result = [f"北京时间未来 {days} 天 DeepSeek API 峰谷时间："]
    for i in range(days):
        date = (now + timedelta(days=i)).date()
        weekday = weekdays[date.weekday()]
        if date.weekday() >= 5:
            result.append(f"{date} {weekday}：🟢 全天低谷")
        else:
            result.append(
                f"{date} {weekday}：🔴 09:00-12:00、14:00-18:00 高峰；"
                "其余时间 🟢 低谷"
            )
    return "\n".join(result)

@mcp.tool()
def deepseek_best_time() -> str:
    """判断现在是否适合运行大量 DeepSeek API 任务。"""
    now = datetime.now(TZ)
    if not is_peak(now):
        return (
            f"现在北京时间 {now:%H:%M}。\n"
            "当前是：🟢 低谷\n\n"
            "如果任务不着急，可以直接运行。\n"
            "当前价格约为高峰价格的 50%。"
        )
    next_time = next_transition(now)
    duration = fmt_minutes((next_time - now).total_seconds())
    return (
        f"现在北京时间 {now:%H:%M}。\n"
        "当前是：🔴 高峰\n\n"
        f"下一段低谷开始：{next_time:%Y-%m-%d %H:%M}\n"
        f"距离低谷：约 {duration}\n\n"
        "如果任务不着急，可以等待低谷后再运行大量 API 任务。"
    )

@mcp.tool()
def deepseek_estimate_cost(
    cache_hit_input_tokens: int = 0,
    cache_miss_input_tokens: int = 0,
    output_tokens: int = 0,
    peak: bool | None = None,
) -> str:
    """估算 DeepSeek V4.1-Flash API 成本。"""
    now = datetime.now(TZ)
    actual_peak = is_peak(now) if peak is None else bool(peak)
    p = "peak" if actual_peak else "off_peak"
    hit_cost = cache_hit_input_tokens / 1_000_000 * PRICES["cache_hit_input"][p]
    miss_cost = cache_miss_input_tokens / 1_000_000 * PRICES["cache_miss_input"][p]
    output_cost = output_tokens / 1_000_000 * PRICES["output"][p]
    total = hit_cost + miss_cost + output_cost
    state = "高峰" if actual_peak else "低谷"
    return (
        "DeepSeek V4.1-Flash API 成本估算\n\n"
        f"计算时段：{state}\n"
        f"缓存命中输入：{cache_hit_input_tokens:,} tokens\n"
        f"缓存未命中输入：{cache_miss_input_tokens:,} tokens\n"
        f"输出：{output_tokens:,} tokens\n\n"
        f"预计成本：¥{total:.4f}\n\n"
        "以上价格参数请以 DeepSeek 官方最新价格为准。"
    )

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8000"))
    mcp.run(transport="streamable-http", host="0.0.0.0", port=port)
