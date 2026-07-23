"""管理者権限チェックなどの共通ユーティリティ。"""

from __future__ import annotations

import discord

from palcord.config import AppConfig


def is_admin(user: discord.abc.User, config: AppConfig) -> bool:
    """設定された admin_ids に含まれるか判定する。"""
    # Discord ユーザー ID が管理者リストにあるか確認する
    return int(user.id) in config.discord.admin_ids


async def deny_if_not_admin(
    interaction: discord.Interaction,
    config: AppConfig,
) -> bool:
    """管理者でなければ ephemeral で拒否し True を返す。管理者なら False。"""
    # 管理者なら拒否しない
    if is_admin(interaction.user, config):
        return False
    # 未応答なら defer せずに即拒否する
    await interaction.response.send_message(
        "このコマンドは管理者のみ実行できます。",
        ephemeral=True,
    )
    return True
