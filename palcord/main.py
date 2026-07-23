"""Palcord エントリポイント。"""

from __future__ import annotations

import logging
import sys

from palcord.bot import PalcordBot
from palcord.config import (
    CONFIG_PATH,
    ConfigError,
    ensure_config_file,
    load_config,
    validate_runtime_config,
)
from palcord.palworld_client import PalworldClient


def _configure_logging() -> None:
    """標準ログ設定を適用する。"""
    # INFO 以上をコンソールへ出す
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )


def main() -> int:
    """設定を読み込み Bot を起動する。終了コードを返す。"""
    # ログを初期化する
    _configure_logging()
    logger = logging.getLogger("palcord")

    # 既存の有無を記録してから ensure する（初回コピー判定用）
    config_existed = CONFIG_PATH.exists()
    try:
        # 無ければ default からコピーする
        ensure_config_file()
    except ConfigError as exc:
        logger.error("%s", exc)
        return 1

    # 初回コピー直後は編集を促して終了する
    if not config_existed:
        print(
            "\n[Palcord] config.yaml を作成しました。\n"
            f"  場所: {CONFIG_PATH}\n\n"
            "次の項目を編集してから、もう一度 start.bat を実行してください:\n"
            "  - discord.token\n"
            "  - discord.guild_id\n"
            "  - discord.channel_id\n"
            "  - discord.admin_ids（管理コマンド利用者）\n"
            "  - palworld.base_url / password\n"
        )
        return 0

    try:
        # YAML を読み込み必須項目を検証する
        config = load_config()
        validate_runtime_config(config)
    except ConfigError as exc:
        logger.error("%s", exc)
        logger.error("設定ファイルを確認してください: %s", CONFIG_PATH)
        return 1

    # REST クライアントを生成する
    client = PalworldClient(
        base_url=config.palworld.base_url,
        username=config.palworld.username,
        password=config.palworld.password,
    )
    # Bot を生成する
    bot = PalcordBot(config, client)
    try:
        # Discord に接続してイベントループを開始する
        bot.run(config.discord.token, log_handler=None)
    except KeyboardInterrupt:
        # Ctrl+C は正常終了扱い
        logger.info("停止要求を受け取りました。")
        return 0
    except Exception:
        # 予期せぬ起動失敗
        logger.exception("Bot の実行中にエラーが発生しました。")
        return 1
    return 0


if __name__ == "__main__":
    # モジュール直接実行時の入口
    sys.exit(main())
