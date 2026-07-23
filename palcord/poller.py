"""プレイヤー差分と REST 到達性のポーリング。"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from palcord.notifier import Notifier, player_key
from palcord.palworld_client import PalworldAPIError, PalworldClient

logger = logging.getLogger(__name__)


class PlayerPoller:
    """定期的に REST API を監視し、入退出と到達性を通知する。"""

    def __init__(
        self,
        client: PalworldClient,
        notifier: Notifier,
        interval_seconds: float,
    ) -> None:
        # REST クライアント
        self._client = client
        # Discord 通知担当
        self._notifier = notifier
        # ポーリング間隔
        self._interval = interval_seconds
        # 前回のプレイヤー辞書（key -> player）
        self._known: dict[str, dict[str, Any]] = {}
        # 到達不能状態かどうか
        self._unreachable = False
        # 初回スナップショット取得済みか
        self._initialized = False
        # バックグラウンドタスク
        self._task: asyncio.Task[None] | None = None
        # 停止フラグ
        self._stopped = False

    def start(self) -> None:
        """ポーリングループを開始する。"""
        # 二重起動を防ぐ
        if self._task and not self._task.done():
            return
        # 停止フラグを下ろす
        self._stopped = False
        # バックグラウンドタスクを起動する
        self._task = asyncio.create_task(self._run(), name="palcord-poller")

    async def stop(self) -> None:
        """ポーリングループを停止する。"""
        # 停止を要求する
        self._stopped = True
        # タスクが無ければ終了
        if not self._task:
            return
        # 実行中ならキャンセルする
        self._task.cancel()
        try:
            await self._task
        except asyncio.CancelledError:
            # キャンセルは想定どおり
            pass
        self._task = None

    async def _run(self) -> None:
        """メインのポーリングループ。"""
        # 停止されるまで繰り返す
        while not self._stopped:
            try:
                # 1 回分の監視処理を実行する
                await self._tick()
            except Exception:
                # 予期せぬ例外でもループを継続する
                logger.exception("ポーリング中に予期せぬエラーが発生しました。")
            # 次のポーリングまで待機する
            await asyncio.sleep(self._interval)

    async def _fetch_snapshot(
        self,
    ) -> tuple[list[dict[str, Any]], int, int, dict[str, Any] | None]:
        """プレイヤー一覧と人数上限、任意で info を取得する。"""
        # プレイヤー一覧を取得する
        players = await self._client.get_players()
        # メトリクスから人数情報を取る（失敗しても一覧件数で代替）
        maximum = max(len(players), 1)
        current = len(players)
        try:
            metrics = await self._client.get_metrics()
            # API の現在人数があれば優先する
            if metrics.get("currentplayernum") is not None:
                current = int(metrics["currentplayernum"])
            # 最大人数があれば使う
            if metrics.get("maxplayernum") is not None:
                maximum = int(metrics["maxplayernum"])
        except PalworldAPIError as exc:
            # メトリクス失敗は一覧だけで継続する
            logger.warning("metrics 取得に失敗しました: %s", exc)
        # 起動通知用に info も試みる
        info: dict[str, Any] | None = None
        try:
            info = await self._client.get_info()
        except PalworldAPIError:
            # info は任意なので失敗しても無視する
            info = None
        return players, current, maximum, info

    async def bootstrap(self) -> None:
        """起動直後のスナップショット取得と通知。"""
        try:
            # 初回スナップショットを取る
            players, current, maximum, info = await self._fetch_snapshot()
        except PalworldAPIError as exc:
            # 起動時未到達を記録して通知する
            self._unreachable = True
            await self._notifier.notify_startup(None, [], reachable=False)
            await self._notifier.notify_unreachable(str(exc))
            return
        # 既知プレイヤー辞書を初期化する
        self._known = {player_key(p): p for p in players}
        self._initialized = True
        self._unreachable = False
        # 起動ステータスを通知する
        await self._notifier.notify_startup(info, players, reachable=True)
        # トピックを初期人数で更新する
        await self._notifier.update_topic(current, maximum, force=True)

    async def _tick(self) -> None:
        """1 回分の差分検知処理。"""
        try:
            # 現状スナップショットを取得する
            players, current, maximum, _info = await self._fetch_snapshot()
        except PalworldAPIError as exc:
            # 既に未到達なら重複通知しない
            if not self._unreachable:
                self._unreachable = True
                await self._notifier.notify_unreachable(str(exc))
            else:
                logger.debug("継続して未到達: %s", exc)
            return

        # 復旧した場合は一度だけ通知する
        if self._unreachable:
            self._unreachable = False
            await self._notifier.notify_recovered(len(players))

        # キー付き辞書に変換する
        current_map = {player_key(p): p for p in players}

        # 初回未初期化なら差分通知せずベースラインだけ作る
        if not self._initialized:
            self._known = current_map
            self._initialized = True
            await self._notifier.update_topic(current, maximum, force=True)
            return

        # 入室プレイヤーを検出する
        joined_keys = set(current_map) - set(self._known)
        # 退室プレイヤーを検出する
        left_keys = set(self._known) - set(current_map)

        # 入室通知を送る
        for key in sorted(joined_keys):
            await self._notifier.notify_join(current_map[key], current, maximum)
        # 退室通知を送る
        for key in sorted(left_keys):
            await self._notifier.notify_leave(self._known[key], current, maximum)

        # 既知状態を更新する
        self._known = current_map
        # 人数変化または dirty ならトピックを更新する
        await self._notifier.update_topic(current, maximum)
