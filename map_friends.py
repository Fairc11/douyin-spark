"""一次性：把好友抖音号对应到永久用户编号 sec_uid，写入 data/friend_ids.json。

用法：.venv/bin/python map_friends.py < 抖音号名单（每行一个，# 开头为注释）

做法：滚动私信列表收集所有单聊会话的 sec_uid，逐个打开对方主页，读取“抖音号：xxx”，
与名单逐字比较，完全一致才记录。遇到验证码立即停止。不点击聊天、不发送消息。
"""

from __future__ import annotations

import json
import random
import re
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

from spark import SEC_UIDS_JS, load_chat, write_friend_ids

ROOT = Path(__file__).resolve().parent
PROFILE_URL = "https://www.douyin.com/user/{}"
ID_LINE = re.compile(r"抖音号[:：]\s*(\S+)")
CAPTCHA_TEXT = "请完成下列验证"



def read_ids(text: str) -> list[str]:
    ids = [line.strip() for line in text.splitlines()]
    ids = [x for x in ids if x and not x.startswith("#")]
    if not ids or len(ids) != len(set(ids)):
        raise SystemExit("名单为空或有重复")
    return ids


def collect_sec_uids(page) -> list[str]:
    scroll = page.locator(".conversationConversationListwrapper").first
    found: list[str] = []
    if scroll.count():
        scroll.evaluate("el => { el.scrollTop = 0 }")
    bottom = 0
    for _ in range(300):
        for sec in page.evaluate(SEC_UIDS_JS):
            if sec and sec not in found:
                found.append(sec)
        if not scroll.count():
            break
        top, height, view = scroll.evaluate("el => [el.scrollTop, el.scrollHeight, el.clientHeight]")
        bottom = bottom + 1 if top + view >= height - 2 else 0
        if bottom >= 3:
            break
        scroll.evaluate("(el, s) => { el.scrollTop += s }", max(250, view * 0.7))
        page.wait_for_timeout(600)
    return found


def main() -> int:
    wanted = read_ids(sys.stdin.read())
    mapping: dict[str, str] = {}
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(storage_state=str(ROOT / "auth.json"), locale="zh-CN",
                                      viewport={"width": 1400, "height": 900})
        page = context.new_page()
        load_chat(page)
        page.wait_for_timeout(2500)
        secs = collect_sec_uids(page)
        print(f"私信列表中的单聊会话：{len(secs)} 个")
        for index, sec in enumerate(secs, 1):
            if len(mapping) == len(wanted):
                break
            page.goto(PROFILE_URL.format(sec), wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(4000)
            text = page.evaluate("() => document.body.innerText")
            if CAPTCHA_TEXT in text:
                print(f"第 {index} 个主页出现验证码，已停止")
                break
            ids = {m.group(1) for m in ID_LINE.finditer(text)}
            if len(ids) != 1:
                print(f"第 {index} 个主页未能唯一读取抖音号，跳过")
            else:
                douyin_id = ids.pop()
                if douyin_id in wanted and douyin_id not in mapping:
                    mapping[douyin_id] = sec
                    print(f"名单第 {wanted.index(douyin_id) + 1} 位：已对应")
            page.wait_for_timeout(random.randint(3000, 6000))
        context.storage_state(path=str(ROOT / "auth.json"))
        browser.close()
    write_friend_ids(ROOT / "data" / "friend_ids.json",
                     [{"douyin_id": d, "sec_uid": mapping[d]} for d in wanted if d in mapping])
    missing = [i + 1 for i, d in enumerate(wanted) if d not in mapping]
    print(f"已对应 {len(mapping)}/{len(wanted)}" + (f"；未找到：名单第 {missing} 位" if missing else ""))
    return 0 if not missing else 1


if __name__ == "__main__":
    sys.exit(main())
