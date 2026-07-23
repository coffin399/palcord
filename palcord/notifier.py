"""Discord への通知とチャンネルトピック更新。"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

import discord

from palcord.config import TopicConfig

logger = logging.getLogger(__name__)


def player_key(player: dict[str, Any]) -> str:
    """プレイヤー識別キーを返す（userId 優先）。"""
    # userId があればそれを使う
    user_id = player.get("userId") or player.get("userid")
    if user_id:
        return str(user_id)
    # なければ playerId を使う
    player_id = player.get("playerId")
    if player_id:
        return str(player_id)
    # 最後の手段として名前を使う
    return str(player.get("name") or "unknown")


def player_display_name(player: dict[str, Any]) -> str:
    """表示用のプレイヤー名を返す。"""
    # ゲーム内名を優先する
    name = player.get("name")
    if name:
        return str(name)
    # アカウント名があれば代用する
    account = player.get("accountName")
    if account:
        return str(account)
    return "Unknown"


class Notifier:
    """通知チャンネルへの Embed 送信とトピック更新を担当する。"""

    def __init__(
        self,
        channel: discord.TextChannel,
        topic_config: TopicConfig,
    ) -> None:
        # 通知先チャンネル
        self._channel = channel
        # トピックテンプレート設定
        self._topic_config = topic_config
        # 最後に設定したトピック文字列（差分検出用）
        self._last_topic: str | None = None
        # トピック更新がレート制限で失敗した場合のリトライフラグ
        self._topic_dirty = False

    @property
    def channel(self) -> discord.TextChannel:
        """通知チャンネルを返す。"""
        return self._channel

    async def send_embed(self, embed: discord.Embed) -> None:
        """Embed を通知チャンネルへ送信する。"""
        # チャンネルへ投稿する
        await self._channel.send(embed=embed)

    async def notify_startup(
        self,
        info: dict[str, Any] | None,
        players: list[dict[str, Any]],
        reachable: bool,
    ) -> None:
        """ボット起動時のステータスを通知する。"""
        # Embed を組み立てる
        embed = discord.Embed(
            title="Palcord 起動",
            color=discord.Color.green() if reachable else discord.Color.orange(),
            timestamp=datetime.now(timezone.utc),
        )
        # 到達可否を表示する
        embed.add_field(
            name="REST API",
            value="接続成功" if reachable else "未到達",
            inline=True,
        )
        # サーバー情報があれば載せる
        if info:
            embed.add_field(
                name="サーバー名",
                value=str(info.get("servername") or "不明"),
                inline=True,
            )
            embed.add_field(
                name="バージョン",
                value=str(info.get("version") or "不明"),
                inline=True,
            )
        # オンライン人数を表示する
        embed.add_field(
            name="オンライン",
            value=str(len(players)),
            inline=True,
        )
        # プレイヤー名を列挙する（長すぎる場合は省略）
        if players:
            names = ", ".join(player_display_name(p) for p in players[:20])
            # 20 人超は省略表記を付ける
            if len(players) > 20:
                names += f" 他 {len(players) - 20} 人"
            embed.add_field(name="プレイヤー", value=names, inline=False)
        # 通知を送る
        await self.send_embed(embed)

    async def notify_join(self, player: dict[str, Any], current: int, maximum: int) -> None:
        """入室通知を送る。"""
        # 入室用 Embed を作る
        embed = discord.Embed(
            title="プレイヤー入室",
            description=player_display_name(player),
            color=discord.Color.blue(),
            timestamp=datetime.now(timezone.utc),
        )
        # レベルがあれば表示する
        level = player.get("level")
        if level is not None:
            embed.add_field(name="レベル", value=str(level), inline=True)
        # 現在人数を表示する
        embed.add_field(name="人数", value=f"{current}/{maximum}", inline=True)
        # IP はプライバシーのため出さない
        await self.send_embed(embed)

    async def notify_leave(self, player: dict[str, Any], current: int, maximum: int) -> None:
        """退室通知を送る。"""
        # 退室用 Embed を作る
        embed = discord.Embed(
            title="プレイヤー退室",
            description=player_display_name(player),
            color=discord.Color.dark_grey(),
            timestamp=datetime.now(timezone.utc),
        )
        # レベルがあれば表示する
        level = player.get("level")
        if level is not None:
            embed.add_field(name="レベル", value=str(level), inline=True)
        # 現在人数を表示する
        embed.add_field(name="人数", value=f"{current}/{maximum}", inline=True)
        await self.send_embed(embed)

    async def notify_unreachable(self, detail: str) -> None:
        """サーバー到達不能を通知する。"""
        # 警告色の Embed を送る
        embed = discord.Embed(
            title="サーバー未到達",
            description=detail,
            color=discord.Color.red(),
            timestamp=datetime.now(timezone.utc),
        )
        await self.send_embed(embed)

    async def notify_recovered(self, player_count: int) -> None:
        """サーバー復旧を通知する。"""
        # 復旧 Embed を送る
        embed = discord.Embed(
            title="サーバー復旧",
            description=f"REST API に再接続しました。オンライン: {player_count}",
            color=discord.Color.green(),
            timestamp=datetime.now(timezone.utc),
        )
        await self.send_embed(embed)

    def format_topic(self, current: int, maximum: int) -> str:
        """トピック文字列をテンプレートから生成する。"""
        # {current} / {max} を置換する
        return self._topic_config.template.format(current=current, max=maximum)

    async def update_topic(self, current: int, maximum: int, *, force: bool = False) -> None:
        """チャンネルトピックを人数表示に更新する。"""
        # 新しいトピック文言を作る
        topic = self.format_topic(current, maximum)
        # 変化がなく dirty でもなければ何もしない
        if not force and not self._topic_dirty and topic == self._last_topic:
            return
        try:
            # Discord チャンネルのトピックを更新する
            await self._channel.edit(topic=topic)
        except discord.HTTPException as exc:
            # レート制限や権限不足時は次回リトライする
            self._topic_dirty = True
            logger.warning("チャンネルトピック更新に失敗しました: %s", exc)
            return
        # 成功したら状態を更新する
        self._last_topic = topic
        self._topic_dirty = False
        logger.debug("トピックを更新しました: %s", topic)
