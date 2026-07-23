"""管理者限定のスラッシュコマンド。"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Callable, Awaitable

import discord
from discord import app_commands
from discord.ext import commands

from palcord.bot import PalcordBot
from palcord.palworld_client import PalworldAPIError
from palcord.permissions import deny_if_not_admin, is_admin


class ConfirmView(discord.ui.View):
    """破壊的操作の確認用 View。"""

    def __init__(
        self,
        *,
        owner_id: int,
        bot: PalcordBot,
        on_confirm: Callable[[], Awaitable[str]],
        timeout: float = 60.0,
    ) -> None:
        # タイムアウト付き View を初期化する
        super().__init__(timeout=timeout)
        # コマンド実行者のみ操作可能にする
        self._owner_id = owner_id
        # Bot 参照（管理者再チェック用）
        self._bot = bot
        # 確認時に実行する非同期コールバック
        self._on_confirm = on_confirm
        # 結果メッセージを保持する
        self.message: discord.Message | None = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """実行者かつ管理者のみボタン操作を許可する。"""
        # 別ユーザーの操作は拒否する
        if interaction.user.id != self._owner_id:
            await interaction.response.send_message(
                "この確認はコマンド実行者のみ操作できます。",
                ephemeral=True,
            )
            return False
        # 管理者でなくなっていないか再確認する
        if not is_admin(interaction.user, self._bot.app_config):
            await interaction.response.send_message(
                "管理者権限がありません。",
                ephemeral=True,
            )
            return False
        return True

    @discord.ui.button(label="Confirm", style=discord.ButtonStyle.danger)
    async def confirm(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button[ConfirmView],
    ) -> None:
        """確認ボタン押下時の処理。"""
        # 二重実行を防ぐため View を止める
        self.stop()
        # ボタンを無効化する
        for child in self.children:
            if isinstance(child, discord.ui.Button):
                child.disabled = True
        # 処理中であることを示す
        await interaction.response.defer(ephemeral=True)
        try:
            # 実際の REST 操作を実行する
            result = await self._on_confirm()
        except PalworldAPIError as exc:
            # 失敗を返す
            await interaction.followup.send(f"失敗しました: {exc}", ephemeral=True)
            return
        # 成功メッセージを返す
        await interaction.followup.send(result, ephemeral=True)
        # 元メッセージのボタンも無効化表示にする
        if self.message is not None:
            try:
                await self.message.edit(view=self)
            except discord.HTTPException:
                pass

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary)
    async def cancel(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button[ConfirmView],
    ) -> None:
        """キャンセルボタン押下時の処理。"""
        # View を停止する
        self.stop()
        # ボタンを無効化する
        for child in self.children:
            if isinstance(child, discord.ui.Button):
                child.disabled = True
        # キャンセルを通知する
        await interaction.response.edit_message(
            content="キャンセルしました。",
            embed=None,
            view=self,
        )

    async def on_timeout(self) -> None:
        """タイムアウト時にボタンを無効化する。"""
        # 全ボタンを無効にする
        for child in self.children:
            if isinstance(child, discord.ui.Button):
                child.disabled = True
        # メッセージがあれば更新する
        if self.message is not None:
            try:
                await self.message.edit(view=self)
            except discord.HTTPException:
                pass


class AdminCog(commands.Cog):
    """管理者限定コマンド。"""

    def __init__(self, bot: PalcordBot) -> None:
        # Bot 参照を保持する
        self.bot = bot

    @app_commands.command(name="kick", description="プレイヤーをキックします（管理者）")
    @app_commands.describe(userid="対象の userId", message="キック理由")
    async def kick(
        self,
        interaction: discord.Interaction,
        userid: str,
        message: str = "Kicked by admin",
    ) -> None:
        """プレイヤーをキックする。"""
        # 管理者以外は拒否する
        if await deny_if_not_admin(interaction, self.bot.app_config):
            return
        # 応答待ちを示す
        await interaction.response.defer(ephemeral=True)
        try:
            # REST でキックする
            await self.bot.palworld.kick(userid, message)
        except PalworldAPIError as exc:
            await interaction.followup.send(f"失敗しました: {exc}", ephemeral=True)
            return
        await interaction.followup.send(
            f"`{userid}` をキックしました。理由: {message}",
            ephemeral=True,
        )

    @app_commands.command(name="ban", description="プレイヤーを BAN します（管理者）")
    @app_commands.describe(userid="対象の userId", message="BAN 理由")
    async def ban(
        self,
        interaction: discord.Interaction,
        userid: str,
        message: str = "Banned by admin",
    ) -> None:
        """プレイヤーを BAN する。"""
        # 管理者以外は拒否する
        if await deny_if_not_admin(interaction, self.bot.app_config):
            return
        # 応答待ちを示す
        await interaction.response.defer(ephemeral=True)
        try:
            # REST で BAN する
            await self.bot.palworld.ban(userid, message)
        except PalworldAPIError as exc:
            await interaction.followup.send(f"失敗しました: {exc}", ephemeral=True)
            return
        await interaction.followup.send(
            f"`{userid}` を BAN しました。理由: {message}",
            ephemeral=True,
        )

    @app_commands.command(name="unban", description="プレイヤーの BAN を解除します（管理者）")
    @app_commands.describe(userid="対象の userId")
    async def unban(self, interaction: discord.Interaction, userid: str) -> None:
        """プレイヤーの BAN を解除する。"""
        # 管理者以外は拒否する
        if await deny_if_not_admin(interaction, self.bot.app_config):
            return
        # 応答待ちを示す
        await interaction.response.defer(ephemeral=True)
        try:
            # REST で Unban する
            await self.bot.palworld.unban(userid)
        except PalworldAPIError as exc:
            await interaction.followup.send(f"失敗しました: {exc}", ephemeral=True)
            return
        await interaction.followup.send(f"`{userid}` の BAN を解除しました。", ephemeral=True)

    @app_commands.command(name="announce", description="サーバー全体にアナウンスします（管理者）")
    @app_commands.describe(message="アナウンス文言")
    async def announce(self, interaction: discord.Interaction, message: str) -> None:
        """全体アナウンスを送る。"""
        # 管理者以外は拒否する
        if await deny_if_not_admin(interaction, self.bot.app_config):
            return
        # 応答待ちを示す
        await interaction.response.defer(ephemeral=True)
        try:
            # REST でアナウンスする
            await self.bot.palworld.announce(message)
        except PalworldAPIError as exc:
            await interaction.followup.send(f"失敗しました: {exc}", ephemeral=True)
            return
        await interaction.followup.send(f"アナウンスしました: {message}", ephemeral=True)

    @app_commands.command(name="save", description="ワールドを保存します（管理者）")
    async def save(self, interaction: discord.Interaction) -> None:
        """ワールドを保存する。"""
        # 管理者以外は拒否する
        if await deny_if_not_admin(interaction, self.bot.app_config):
            return
        # 応答待ちを示す
        await interaction.response.defer(ephemeral=True)
        try:
            # REST で保存する
            await self.bot.palworld.save()
        except PalworldAPIError as exc:
            await interaction.followup.send(f"失敗しました: {exc}", ephemeral=True)
            return
        await interaction.followup.send("ワールドを保存しました。", ephemeral=True)

    @app_commands.command(
        name="shutdown",
        description="猶予付きでサーバーをシャットダウンします（管理者・要確認）",
    )
    @app_commands.describe(
        waittime="シャットダウンまでの秒数",
        message="プレイヤーへのメッセージ",
    )
    async def shutdown(
        self,
        interaction: discord.Interaction,
        waittime: app_commands.Range[int, 0, 86400] = 60,
        message: str = "Server is shutting down",
    ) -> None:
        """猶予付きシャットダウン（確認ボタン必須）。"""
        # 管理者以外は拒否する
        if await deny_if_not_admin(interaction, self.bot.app_config):
            return

        # 確認時に実行するコールバックを定義する
        async def do_shutdown() -> str:
            # REST でシャットダウンを要求する
            await self.bot.palworld.shutdown(int(waittime), message)
            return f"シャットダウンを開始しました（{waittime} 秒 / {message}）。"

        # 確認 View を用意する
        view = ConfirmView(
            owner_id=interaction.user.id,
            bot=self.bot,
            on_confirm=do_shutdown,
        )
        # 確認 Embed を作る
        embed = discord.Embed(
            title="シャットダウン確認",
            description=(
                f"**{waittime} 秒後**にサーバーをシャットダウンします。\n"
                f"メッセージ: {message}\n\n"
                "実行する場合は Confirm を押してください。"
            ),
            color=discord.Color.orange(),
            timestamp=datetime.now(timezone.utc),
        )
        # 確認メッセージを送る
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        # タイムアウト時の編集用にメッセージを保持する
        view.message = await interaction.original_response()

    @app_commands.command(
        name="stop",
        description="サーバーを即時強制停止します（管理者・要確認）",
    )
    async def stop(self, interaction: discord.Interaction) -> None:
        """即時強制停止（確認ボタン必須）。"""
        # 管理者以外は拒否する
        if await deny_if_not_admin(interaction, self.bot.app_config):
            return

        # 確認時に実行するコールバックを定義する
        async def do_stop() -> str:
            # REST で強制停止する
            await self.bot.palworld.stop()
            return "強制停止を実行しました。"

        # 確認 View を用意する
        view = ConfirmView(
            owner_id=interaction.user.id,
            bot=self.bot,
            on_confirm=do_stop,
        )
        # 警告 Embed を作る
        embed = discord.Embed(
            title="強制停止の確認",
            description=(
                "サーバーを**即時強制停止**します。セーブされない可能性があります。\n\n"
                "実行する場合は Confirm を押してください。"
            ),
            color=discord.Color.red(),
            timestamp=datetime.now(timezone.utc),
        )
        # 確認メッセージを送る
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        # タイムアウト時の編集用にメッセージを保持する
        view.message = await interaction.original_response()


async def setup(bot: commands.Bot) -> None:
    """Cog を Bot に登録する。"""
    # PalcordBot 前提で登録する
    await bot.add_cog(AdminCog(bot))  # type: ignore[arg-type]
