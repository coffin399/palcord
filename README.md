# Palcord

![Palcord](https://i.imgur.com/jvc1OHe.png)

Palworld 1.0 サーバー向け Discord 連携ボットです。  
**REST API のみ**を使用します（**RCON 非対応**）。

Discord integration bot for Palworld 1.0 dedicated servers.  
Uses the **REST API only** (**RCON is not supported**).

公式 REST API ドキュメント / Official REST API docs:  
https://docs.palworldgame.com/ja/category/rest-api

---

## 日本語

### 概要

- プレイヤーの入室・退室を指定チャンネルへ通知
- REST API 未到達 / 復旧を通知
- ボット起動時にステータスを通知
- チャンネルトピックにオンライン人数を表示
- スラッシュコマンドで一覧取得・管理操作

### 必要条件

- Python **3.11+**
- Palworld 専用サーバー（REST API 有効）
- Discord Bot（Developer Portal で作成）

### Palworld 側の設定

`PalWorldSettings.ini` などで次を設定します。

```ini
RESTAPIEnabled=True
RESTAPIPort=8212
AdminPassword="YourPassword123"
```

- REST API はインターネットへ直接公開しないでください（LAN / VPN / リバースプロキシ推奨）。
- palcord の `palworld.base_url` 例: `http://localhost:8212/v1/api`
- Basic Auth ユーザー名は通常 `admin`、パスワードは `AdminPassword`

### Discord Bot の設定

1. [Discord Developer Portal](https://discord.com/developers/applications) でアプリケーションを作成
2. Bot を追加し、**Token** を控える
3. Privileged Gateway Intent は不要です（Guilds のみ使用）
4. Bot をサーバーへ招待（少なくとも次の権限）
   - View Channels / Send Messages / Embed Links
   - **Manage Channels**（チャンネルトピック更新に必要）
5. Discord の「開発者モード」を有効にし、次の ID を控える
   - サーバー（ギルド）ID → `guild_id`
   - 通知用テキストチャンネル ID → `channel_id`
   - 管理者にするユーザー ID → `admin_ids`

### セットアップ

1. このリポジトリを配置します
2. `start.bat` を実行します（初回は `config.yaml` が自動生成されます）
3. `config.yaml` を編集します
4. もう一度 `start.bat` を実行します

初回起動時、`config.default.yaml` が `config.yaml` にコピーされます。  
`config.yaml` は Git 管理対象外です（秘密情報を含むため）。

#### 主な設定項目

| キー | 説明 |
|------|------|
| `discord.token` | Bot トークン |
| `discord.guild_id` | Discord サーバー ID |
| `discord.channel_id` | 通知チャンネル ID |
| `discord.admin_ids` | 管理コマンドを使えるユーザー ID のリスト |
| `palworld.base_url` | REST API ベース URL（`/v1/api` まで） |
| `palworld.username` | Basic Auth ユーザー（通常 `admin`） |
| `palworld.password` | `AdminPassword` |
| `poll.interval_seconds` | ポーリング間隔（秒） |
| `topic.template` | トピック文言（`{current}` / `{max}`） |

### 起動

Windows:

```bat
start.bat
```

手動:

```bat
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe -m palcord
```

### 機能

- 入室 / 退室 Embed 通知（IP は表示しません）
- REST API 到達不能・復旧通知
- 起動時ステータス通知
- チャンネルトピックの人数表示（人数変化時のみ更新。Discord のレート制限に配慮）

### コマンド一覧

#### 誰でも使えるコマンド

| コマンド | 説明 |
|----------|------|
| `/help` | 使い方とコマンド一覧 |
| `/players` | オンラインプレイヤー一覧 |
| `/info` | サーバー情報 |
| `/metrics` | FPS・人数・uptime など |
| `/settings` | サーバー設定の要約 |

#### 管理者のみ（`admin_ids`）

| コマンド | 説明 |
|----------|------|
| `/kick` | キック（userid + 理由） |
| `/ban` | BAN（userid + 理由） |
| `/unban` | BAN 解除 |
| `/announce` | 全体アナウンス |
| `/save` | ワールド保存 |
| `/shutdown` | 猶予付きシャットダウン（Confirm 必須） |
| `/stop` | 即時強制停止（Confirm 必須） |

`/shutdown` と `/stop` は誤操作防止のため Confirm / Cancel ボタンが必要です。

### トラブルシュート

| 症状 | 確認すること |
|------|----------------|
| 認証失敗 | `palworld.password` とサーバーの `AdminPassword` |
| コマンドが出ない | Bot 招待・`guild_id`・再起動後の同期 |
| トピックが変わらない | Manage Channels 権限。Discord は 10 分あたり約 2 回の制限あり |
| 通知が来ない | `channel_id` がテキストチャンネルか、送信権限があるか |
| REST 未到達 | `base_url`・ファイアウォール・サーバー起動状態 |

---

## English

### Overview

- Notify player join / leave to a configured channel
- Notify REST API unreachable / recovered
- Notify status on bot startup
- Show online player count in the channel topic
- Slash commands for status and admin operations

### Requirements

- Python **3.11+**
- Palworld dedicated server with REST API enabled
- A Discord Bot (created in the Developer Portal)

### Palworld server settings

Configure something like this in `PalWorldSettings.ini`:

```ini
RESTAPIEnabled=True
RESTAPIPort=8212
AdminPassword="YourPassword123"
```

- Do **not** expose the REST API directly to the public Internet (prefer LAN / VPN / reverse proxy).
- Example `palworld.base_url`: `http://localhost:8212/v1/api`
- Basic Auth username is usually `admin`; password is `AdminPassword`

### Discord Bot setup

1. Create an application in the [Discord Developer Portal](https://discord.com/developers/applications)
2. Add a Bot and copy the **Token**
3. No privileged intents are required (Guilds only)
4. Invite the bot with at least:
   - View Channels / Send Messages / Embed Links
   - **Manage Channels** (required to edit channel topic)
5. Enable Developer Mode in Discord and copy:
   - Server (guild) ID → `guild_id`
   - Notification text channel ID → `channel_id`
   - Admin user IDs → `admin_ids`

### Setup

1. Place this repository on the machine that can reach the Palworld REST API
2. Run `start.bat` once (it creates `config.yaml` on first run)
3. Edit `config.yaml`
4. Run `start.bat` again

On first launch, `config.default.yaml` is copied to `config.yaml`.  
`config.yaml` is gitignored because it contains secrets.

#### Main config keys

| Key | Description |
|-----|-------------|
| `discord.token` | Bot token |
| `discord.guild_id` | Discord server ID |
| `discord.channel_id` | Notification channel ID |
| `discord.admin_ids` | User IDs allowed to run admin commands |
| `palworld.base_url` | REST API base URL (include `/v1/api`) |
| `palworld.username` | Basic Auth user (usually `admin`) |
| `palworld.password` | `AdminPassword` |
| `poll.interval_seconds` | Polling interval in seconds |
| `topic.template` | Topic text (`{current}` / `{max}`) |

### Start

Windows:

```bat
start.bat
```

Manual:

```bat
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe -m palcord
```

### Features

- Join / leave embeds (IP addresses are never shown)
- REST unreachable / recovered notifications
- Startup status notification
- Channel topic player count (updated on change only; respects Discord rate limits)

### Commands

#### Available to everyone in the guild

| Command | Description |
|---------|-------------|
| `/help` | Usage and command list |
| `/players` | Online player list |
| `/info` | Server info |
| `/metrics` | FPS, players, uptime, etc. |
| `/settings` | Summarized server settings |

#### Admins only (`admin_ids`)

| Command | Description |
|---------|-------------|
| `/kick` | Kick (userid + reason) |
| `/ban` | Ban (userid + reason) |
| `/unban` | Unban |
| `/announce` | Broadcast announce |
| `/save` | Save the world |
| `/shutdown` | Graceful shutdown (Confirm required) |
| `/stop` | Force stop (Confirm required) |

`/shutdown` and `/stop` require Confirm / Cancel buttons to prevent accidents.

### Troubleshooting

| Issue | What to check |
|------|----------------|
| Auth failed | `palworld.password` vs server `AdminPassword` |
| Commands missing | Bot invite, `guild_id`, wait for guild command sync after restart |
| Topic not updating | Manage Channels permission; Discord allows ~2 topic edits / 10 minutes |
| No notifications | Correct text `channel_id` and send permissions |
| REST unreachable | `base_url`, firewall, server process status |

---

## License

MIT
