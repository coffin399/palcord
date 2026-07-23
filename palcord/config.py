"""設定ファイルの読み込みと初回コピー処理。"""

from __future__ import annotations

import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

# リポジトリルート（このファイルの親の親）
ROOT_DIR = Path(__file__).resolve().parent.parent
# 配布用テンプレート
DEFAULT_CONFIG_PATH = ROOT_DIR / "config.default.yaml"
# 実行時に使う設定
CONFIG_PATH = ROOT_DIR / "config.yaml"


@dataclass
class DiscordConfig:
    """Discord 関連設定。"""

    token: str
    guild_id: int
    channel_id: int
    admin_ids: list[int] = field(default_factory=list)


@dataclass
class PalworldConfig:
    """Palworld REST API 関連設定。"""

    base_url: str
    username: str
    password: str


@dataclass
class PollConfig:
    """ポーリング間隔設定。"""

    interval_seconds: float


@dataclass
class TopicConfig:
    """チャンネルトピック表示設定。"""

    template: str


@dataclass
class AppConfig:
    """アプリケーション全体の設定。"""

    discord: DiscordConfig
    palworld: PalworldConfig
    poll: PollConfig
    topic: TopicConfig


class ConfigError(Exception):
    """設定の不備や読込失敗を表す例外。"""


def ensure_config_file() -> Path:
    """config.yaml が無ければ default をコピーしてパスを返す。"""
    # 既に設定がある場合はそのまま使う
    if CONFIG_PATH.exists():
        return CONFIG_PATH
    # テンプレートが無いと初回セットアップできない
    if not DEFAULT_CONFIG_PATH.exists():
        raise ConfigError(
            f"テンプレートが見つかりません: {DEFAULT_CONFIG_PATH}"
        )
    # 初回用に default をコピーする
    shutil.copyfile(DEFAULT_CONFIG_PATH, CONFIG_PATH)
    return CONFIG_PATH


def _require_str(data: dict[str, Any], key: str, section: str) -> str:
    """必須文字列キーを取り出す。"""
    # セクション内にキーが無い場合はエラー
    if key not in data:
        raise ConfigError(f"{section}.{key} が設定されていません。")
    # 値を文字列に正規化する
    value = str(data[key]).strip()
    return value


def _require_int(data: dict[str, Any], key: str, section: str) -> int:
    """必須整数キーを取り出す。"""
    # セクション内にキーが無い場合はエラー
    if key not in data:
        raise ConfigError(f"{section}.{key} が設定されていません。")
    try:
        # 数値として解釈する
        return int(data[key])
    except (TypeError, ValueError) as exc:
        # 整数に変換できない場合は設定ミスとして報告する
        raise ConfigError(f"{section}.{key} は整数である必要があります。") from exc


def _parse_admin_ids(raw: Any) -> list[int]:
    """admin_ids を整数リストに正規化する。"""
    # 未指定は空リスト扱い
    if raw is None:
        return []
    # リスト以外は型エラー
    if not isinstance(raw, list):
        raise ConfigError("discord.admin_ids はリストである必要があります。")
    result: list[int] = []
    # 各要素を Discord ユーザー ID として解釈する
    for item in raw:
        try:
            result.append(int(item))
        except (TypeError, ValueError) as exc:
            raise ConfigError(
                "discord.admin_ids の各要素は整数である必要があります。"
            ) from exc
    return result


def load_config(path: Path | None = None) -> AppConfig:
    """YAML を読み込み AppConfig を返す。"""
    # 明示パスが無ければ標準の config.yaml を使う
    config_path = path or CONFIG_PATH
    # ファイルが無ければ読込不可
    if not config_path.exists():
        raise ConfigError(f"設定ファイルがありません: {config_path}")
    # YAML をパースする
    with config_path.open(encoding="utf-8") as file:
        raw = yaml.safe_load(file) or {}
    # ルートが辞書でない場合は不正
    if not isinstance(raw, dict):
        raise ConfigError("設定ファイルのルートはマップである必要があります。")

    # 各セクションを取り出す
    discord_raw = raw.get("discord") or {}
    palworld_raw = raw.get("palworld") or {}
    poll_raw = raw.get("poll") or {}
    topic_raw = raw.get("topic") or {}

    # セクション型を検証する
    for name, section in (
        ("discord", discord_raw),
        ("palworld", palworld_raw),
        ("poll", poll_raw),
        ("topic", topic_raw),
    ):
        if not isinstance(section, dict):
            raise ConfigError(f"{name} セクションはマップである必要があります。")

    # Discord 設定を構築する
    discord = DiscordConfig(
        token=_require_str(discord_raw, "token", "discord"),
        guild_id=_require_int(discord_raw, "guild_id", "discord"),
        channel_id=_require_int(discord_raw, "channel_id", "discord"),
        admin_ids=_parse_admin_ids(discord_raw.get("admin_ids")),
    )
    # Palworld REST 設定を構築する
    palworld = PalworldConfig(
        base_url=_require_str(palworld_raw, "base_url", "palworld").rstrip("/"),
        username=_require_str(palworld_raw, "username", "palworld"),
        password=_require_str(palworld_raw, "password", "palworld"),
    )
    # ポーリング間隔（未指定時は 10 秒）
    interval = poll_raw.get("interval_seconds", 10)
    try:
        interval_seconds = float(interval)
    except (TypeError, ValueError) as exc:
        raise ConfigError("poll.interval_seconds は数値である必要があります。") from exc
    # 間隔が短すぎると API / Discord を圧迫するため下限を設ける
    if interval_seconds < 1:
        raise ConfigError("poll.interval_seconds は 1 以上である必要があります。")
    poll = PollConfig(interval_seconds=interval_seconds)

    # トピックテンプレート（未指定時は既定文言）
    template = str(
        topic_raw.get("template") or "プレイヤー: {current}/{max}"
    ).strip()
    topic = TopicConfig(template=template)

    return AppConfig(
        discord=discord,
        palworld=palworld,
        poll=poll,
        topic=topic,
    )


def validate_runtime_config(config: AppConfig) -> None:
    """起動に必要な値が埋まっているか検証する。"""
    # Bot トークン未設定は起動不可
    if not config.discord.token:
        raise ConfigError("discord.token を config.yaml に設定してください。")
    # ギルド ID が 0 のままは未設定扱い
    if config.discord.guild_id <= 0:
        raise ConfigError("discord.guild_id を正しいサーバー ID に設定してください。")
    # 通知チャンネル未設定は不可
    if config.discord.channel_id <= 0:
        raise ConfigError(
            "discord.channel_id を正しいチャンネル ID に設定してください。"
        )
    # REST パスワード未設定は認証できない
    if not config.palworld.password:
        raise ConfigError("palworld.password を config.yaml に設定してください。")
    # ベース URL が空は接続先不明
    if not config.palworld.base_url:
        raise ConfigError("palworld.base_url を設定してください。")
