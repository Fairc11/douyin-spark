# AGENTS.md（服务器版）

本目录是 GitHub 仓库 `Fairc11/douyin-spark` 的本地副本，Fork 自 `sergeymeng/douyin-spark`（MIT）。用途：在首尔 VPS 上每天定时给指定抖音好友发消息续火花，并把结果推送到 Discord。

## 沟通

- 面向用户的叙述使用简体中文；代码、命令和标识保持英文。
- 上一级目录 `../手机版/` 是另一套独立程序（AutoJs6 + 多闪），本目录的改动不得影响它。

## 与上游的差异

- `notify.py`：在原有 ntfy 之外增加 Discord webhook 通道。`data/discord_url` 存在时，所有通知（每日汇总、登录失效、任务失败、测试）同时发到 Discord；不存在时行为与上游一致。
- `spark.py` + `map_friends.py`：按好友的永久用户编号 `sec_uid` 定位会话。依据（2026-11-25 实测）：
  - 私信页搜索框搜抖音号返回“未搜索到相关内容”；主站用户搜索 `/search/<抖音号>?type=user` 弹出滑块验证码，均不可用；
  - 私信列表每个会话行（`[data-e2e="conversation-item"]`）的 React 属性 `conversation.toParticipantSecUserId` 是对方的 sec_uid；会话对象里没有抖音号；
  - 对方主页 `https://www.douyin.com/user/<sec_uid>` 显示“抖音号：xxx”一行；
  - 会话行内标题的精确 class 是 `.conversationConversationItemtitle`（`[class*=...]` 会同时匹配 `titleWrapper`）。
- 用法：`config.json` 的 `friends` 填抖音号；`map_friends.py` 从标准输入读抖音号名单，逐个打开单聊对方主页核对抖音号，完全一致才写入 `data/friend_ids.json`（遇验证码即停）。运行时抖音号在该映射里就按 sec_uid 找会话，读出当前显示名只在内存中使用，打开聊天后核对标题一致才继续；不在映射里则按上游的名字逻辑处理。
- 不要在管理网页里修改好友：网页按名字保存，会覆盖 `friends` 里的抖音号。
- 同步上游：`git fetch upstream && git merge upstream/main`，冲突可能出现在 `notify.py`、`spark.py`。合并后在本机跑 `.venv/bin/python -m pytest -q`（运行前先把 `data/discord_url` 移开，避免测试误发）。

## 隐私

- `auth.json`（抖音登录状态）、`config.json`（好友备注名、发送时间、内容）、`data/`（发送记录、Discord webhook 地址 `data/discord_url`）都已被 `.gitignore` 排除，只能留在本机和服务器，不得提交、不得写进其他文件或对话以外的服务。
- 仓库是公开的，提交前用 `git status` 确认没有上述文件。

## 运行环境

- 本机：Python 3.12（`~/.local/bin/python3.12`），虚拟环境 `.venv/`。系统自带的 Python 3.9 版本过低，不能用。
- 服务器：部署步骤、内存上限和服务名见 VPS 项目 `docs/3x-ui 建节点与客户端导入流程.md` 第二十章。

## 验证命令

```bash
.venv/bin/python -m pytest -q          # 2026-11-25：29 passed
.venv/bin/python spark.py --dry-run    # 只检查登录和好友定位，不发送
.venv/bin/python -c "import notify; notify.publish('test')"   # 向 Discord 发测试消息
```
