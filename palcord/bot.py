"""Discord Bot 本体の定義。"""

from __future__ import annotations

import logging

import discord
from discord.ext import commands

from palcord.config import AppConfig
from palcord.notifier import Notifier
from palcord.palworld_client import PalworldClient
from palcord.poller import PlayerPoller

logger = logging.getLogger(__name__)


class PalcordBot(commands.Bot):
    """Palworld 連携用 Discord Bot。"""

    def __init__(self, config: AppConfig, client: PalworldClient) -> None:
        # Guilds intent のみ（メッセージ内容は不要）
        intents = discord.Intents.default()
        intents.guilds = True
        # commands.Bot を初期化する
        super().__init__(command_prefix="!", intents=intents)
        # アプリ設定を保持する
        self.app_config = config
        # Palworld REST クライアント
        self.palworld = client
        # 通知・ポーラーは on_ready 後に初期化する
        self.notifier: Notifier | None = None
        self.poller: PlayerPoller | None = None
        # スラッシュ同期を一度だけ行うためのフラグ
        self._synced = False
        # ポーラー起動を一度だけ行うためのフラグ
        self._poller_started = False

    async def setup_hook(self) -> None:
        """拡張（Cog）を読み込む。"""
        # 閲覧系コマンドを読み込む
        await self.load_extension("palcord.cogs.status")
        # 管理系コマンドを読み込む
        await self.load_extension("palcord.cogs.admin")

    async def on_ready(self) -> None:
        """接続完了時にチャンネル解決・同期・ポーラー開始を行う。"""
        # ログイン完了をログに出す
        logger.info("Discord にログインしました: %s", self.user)

        # ギルドを取得する
        guild = self.get_guild(self.app_config.discord.guild_id)
        if guild is None:
            # キャッシュに無ければ API から取得を試みる
            try:
                guild = await self.fetch_guild(self.app_config.discord.guild_id)
            except discord.HTTPException as exc:
                logger.error("ギルド取得に失敗しました: %s", exc)
                return

        # スラッシュコマンドをギルドに同期する（即時反映）
        if not self._synced:
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
            self._synced = True
            logger.info("スラッシュコマンドをギルド %s に同期しました。", guild.id)

        # 通知チャンネルを解決する
        channel = guild.get_channel(self.app_config.discord.channel_id)
        if channel is None:
            try:
                fetched = await self.fetch_channel(self.app_config.discord.channel_id)
            except discord.HTTPException as exc:
                logger.error("通知チャンネル取得に失敗しました: %s", exc)
                return
            channel = fetched
        # テキストチャンネル以外はトピック更新できない
        if not isinstance(channel, discord.TextChannel):
            logger.error("channel_id はテキストチャンネルである必要があります。")
            return

        # Notifier / Poller を初期化する
        if self.notifier is None:
            self.notifier = Notifier(channel, self.app_config.topic)
        if self.poller is None:
            self.poller = PlayerPoller(
                self.palworld,
                self.notifier,
                self.app_config.poll.interval_seconds,
            )

        # ポーラーを一度だけ起動する
        if not self._poller_started:
            self._poller_started = True
            # 起動通知を送ってからループ開始する
            await self.poller.bootstrap()
            self.poller.start()
            logger.info("プレイヤーポーラーを開始しました。")

    async def close(self) -> None:
        """終了時にポーラーと HTTP クライアントを閉じる。"""
        # ポーラーを停止する
        if self.poller is not None:
            await self.poller.stop()
        # REST クライアントを閉じる
        await self.palworld.aclose()
        # Bot 本体を閉じる
        await super().close()
