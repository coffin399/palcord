"""閲覧系スラッシュコマンド。"""

from __future__ import annotations

import json
from datetime import datetime, timezone

import discord
from discord import app_commands
from discord.ext import commands

from palcord.bot import PalcordBot
from palcord.notifier import player_display_name
from palcord.palworld_client import PalworldAPIError


def _truncate(text: str, limit: int = 1000) -> str:
    """Discord フィールド向けに文字列を切り詰める。"""
    # 短い場合はそのまま返す
    if len(text) <= limit:
        return text
    # 末尾に省略記号を付ける
    return text[: limit - 3] + "..."


class StatusCog(commands.Cog):
    """サーバー状態の閲覧コマンド。"""

    def __init__(self, bot: PalcordBot) -> None:
        # Bot 参照を保持する
        self.bot = bot

    @app_commands.command(name="help", description="Palcord の使い方とコマンド一覧を表示します")
    async def help(self, interaction: discord.Interaction) -> None:
        """ボット紹介とコマンド一覧。"""
        # ヘルプ Embed を組み立てる
        embed = discord.Embed(
            title="Palcord Help",
            description=(
                "Palworld サーバー向け Discord 連携ボットです。\n"
                "REST API 経由で入退出通知・人数表示・サーバー管理ができます。"
            ),
            color=discord.Color.blurple(),
            timestamp=datetime.now(timezone.utc),
        )
        # 自動通知の概要
        embed.add_field(
            name="自動通知",
            value=(
                "・プレイヤー入室 / 退室\n"
                "・REST API 未到達 / 復旧\n"
                "・ボット起動時ステータス\n"
                "・チャンネルトピックの人数表示"
            ),
            inline=False,
        )
        # 誰でも使えるコマンド
        embed.add_field(
            name="一般コマンド",
            value=(
                "`/help` — このヘルプ\n"
                "`/players` — オンラインプレイヤー一覧\n"
                "`/info` — サーバー情報\n"
                "`/metrics` — FPS・人数・uptime など\n"
                "`/settings` — サーバー設定の要約"
            ),
            inline=False,
        )
        # 管理者限定コマンド
        embed.add_field(
            name="管理コマンド（admin_ids のみ）",
            value=(
                "`/kick` — キック\n"
                "`/ban` — BAN\n"
                "`/unban` — BAN 解除\n"
                "`/announce` — 全体アナウンス\n"
                "`/save` — ワールド保存\n"
                "`/shutdown` — 猶予付きシャットダウン（要 Confirm）\n"
                "`/stop` — 即時強制停止（要 Confirm）"
            ),
            inline=False,
        )
        # 補足
        embed.set_footer(text="管理コマンドは config.yaml の discord.admin_ids で制御されます")
        # 自分にだけ見えるように送る
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="players", description="オンラインプレイヤー一覧を表示します")
    async def players(self, interaction: discord.Interaction) -> None:
        """オンラインプレイヤー一覧。"""
        # 応答待ちを示す
        await interaction.response.defer(ephemeral=True)
        try:
            # REST から一覧を取得する
            players = await self.bot.palworld.get_players()
        except PalworldAPIError as exc:
            await interaction.followup.send(f"取得に失敗しました: {exc}", ephemeral=True)
            return
        # Embed を組み立てる
        embed = discord.Embed(
            title="オンラインプレイヤー",
            description=f"{len(players)} 人",
            color=discord.Color.blurple(),
            timestamp=datetime.now(timezone.utc),
        )
        # プレイヤーがいない場合
        if not players:
            embed.add_field(name="一覧", value="誰もオンラインではありません。", inline=False)
        else:
            # 各プレイヤーを行として並べる
            lines: list[str] = []
            for player in players:
                name = player_display_name(player)
                level = player.get("level", "?")
                user_id = player.get("userId") or player.get("userid") or "?"
                lines.append(f"**{name}** (Lv {level}) — `{user_id}`")
            embed.add_field(
                name="一覧",
                value=_truncate("\n".join(lines), 1000),
                inline=False,
            )
        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="info", description="サーバー情報を表示します")
    async def info(self, interaction: discord.Interaction) -> None:
        """サーバー情報。"""
        # 応答待ちを示す
        await interaction.response.defer(ephemeral=True)
        try:
            # REST から info を取得する
            data = await self.bot.palworld.get_info()
        except PalworldAPIError as exc:
            await interaction.followup.send(f"取得に失敗しました: {exc}", ephemeral=True)
            return
        # Embed を組み立てる
        embed = discord.Embed(
            title="サーバー情報",
            color=discord.Color.green(),
            timestamp=datetime.now(timezone.utc),
        )
        # 主要フィールドを追加する
        embed.add_field(name="名前", value=str(data.get("servername") or "不明"), inline=True)
        embed.add_field(name="バージョン", value=str(data.get("version") or "不明"), inline=True)
        embed.add_field(
            name="説明",
            value=_truncate(str(data.get("description") or "(なし)"), 500),
            inline=False,
        )
        embed.add_field(
            name="World GUID",
            value=f"`{data.get('worldguid') or '不明'}`",
            inline=False,
        )
        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="metrics", description="サーバーメトリクスを表示します")
    async def metrics(self, interaction: discord.Interaction) -> None:
        """サーバーメトリクス。"""
        # 応答待ちを示す
        await interaction.response.defer(ephemeral=True)
        try:
            # REST から metrics を取得する
            data = await self.bot.palworld.get_metrics()
        except PalworldAPIError as exc:
            await interaction.followup.send(f"取得に失敗しました: {exc}", ephemeral=True)
            return
        # Embed を組み立てる
        embed = discord.Embed(
            title="サーバーメトリクス",
            color=discord.Color.teal(),
            timestamp=datetime.now(timezone.utc),
        )
        # 各メトリクスをフィールドにする
        embed.add_field(name="FPS", value=str(data.get("serverfps", "?")), inline=True)
        embed.add_field(
            name="プレイヤー",
            value=f"{data.get('currentplayernum', '?')}/{data.get('maxplayernum', '?')}",
            inline=True,
        )
        embed.add_field(
            name="Frame time (ms)",
            value=str(data.get("serverframetime", "?")),
            inline=True,
        )
        embed.add_field(name="Uptime (秒)", value=str(data.get("uptime", "?")), inline=True)
        embed.add_field(name="拠点数", value=str(data.get("basecampnum", "?")), inline=True)
        embed.add_field(name="ゲーム内日数", value=str(data.get("days", "?")), inline=True)
        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="settings", description="サーバー設定の要約を表示します")
    async def settings(self, interaction: discord.Interaction) -> None:
        """サーバー設定の要約。"""
        # 応答待ちを示す
        await interaction.response.defer(ephemeral=True)
        try:
            # REST から settings を取得する
            data = await self.bot.palworld.get_settings()
        except PalworldAPIError as exc:
            await interaction.followup.send(f"取得に失敗しました: {exc}", ephemeral=True)
            return
        # JSON 文字列化して切り詰める
        pretty = json.dumps(data, ensure_ascii=False, indent=2)
        embed = discord.Embed(
            title="サーバー設定",
            description=f"```json\n{_truncate(pretty, 3500)}\n```",
            color=discord.Color.dark_gold(),
            timestamp=datetime.now(timezone.utc),
        )
        await interaction.followup.send(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    """Cog を Bot に登録する。"""
    # PalcordBot 前提で登録する
    await bot.add_cog(StatusCog(bot))  # type: ignore[arg-type]
