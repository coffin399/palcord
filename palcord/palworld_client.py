"""Palworld REST API クライアント。"""

from __future__ import annotations

from typing import Any

import httpx


class PalworldAPIError(Exception):
    """REST API 呼び出し失敗を表す例外。"""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        # 親 Exception にメッセージを渡す
        super().__init__(message)
        # HTTP ステータスがあれば保持する
        self.status_code = status_code


class PalworldClient:
    """Basic Auth 付きで Palworld REST API を呼び出すクライアント。"""

    def __init__(
        self,
        base_url: str,
        username: str,
        password: str,
        timeout: float = 10.0,
    ) -> None:
        # 末尾スラッシュを除去してパス結合を安定させる
        self._base_url = base_url.rstrip("/")
        # 非同期 HTTP クライアントを生成する
        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            auth=(username, password),
            timeout=timeout,
            headers={"Accept": "application/json"},
        )

    async def aclose(self) -> None:
        """HTTP クライアントを閉じる。"""
        # 接続プールを解放する
        await self._client.aclose()

    async def _request(
        self,
        method: str,
        path: str,
        json_body: dict[str, Any] | None = None,
    ) -> Any:
        """共通リクエスト処理。成功時は JSON（または空）を返す。"""
        # 先頭スラッシュを揃える
        normalized = path if path.startswith("/") else f"/{path}"
        try:
            # REST API を呼び出す
            response = await self._client.request(
                method,
                normalized,
                json=json_body,
            )
        except httpx.HTTPError as exc:
            # ネットワーク系エラーをアプリ例外に変換する
            raise PalworldAPIError(f"REST API 接続に失敗しました: {exc}") from exc

        # 認証失敗
        if response.status_code == 401:
            raise PalworldAPIError(
                "REST API 認証に失敗しました（ユーザー名/パスワードを確認）。",
                status_code=401,
            )
        # その他のエラーレスポンス
        if response.status_code >= 400:
            # 本文があればメッセージに含める
            detail = response.text.strip() or response.reason_phrase
            raise PalworldAPIError(
                f"REST API エラー ({response.status_code}): {detail}",
                status_code=response.status_code,
            )
        # 本文が空なら None を返す
        if not response.content:
            return None
        # JSON として解釈する
        try:
            return response.json()
        except ValueError as exc:
            raise PalworldAPIError(
                "REST API の応答が JSON ではありません。",
                status_code=response.status_code,
            ) from exc

    async def get_players(self) -> list[dict[str, Any]]:
        """オンラインプレイヤー一覧を取得する。"""
        # GET /players
        data = await self._request("GET", "/players")
        # 応答が無い場合は空リスト
        if not data:
            return []
        # 公式スキーマは {"players": [...]}
        if isinstance(data, dict):
            players = data.get("players", [])
            # リストでなければ不正応答
            if not isinstance(players, list):
                raise PalworldAPIError("players 応答の形式が不正です。")
            return players
        # 配列直返しにも一応対応する
        if isinstance(data, list):
            return data
        raise PalworldAPIError("players 応答の形式が不正です。")

    async def get_info(self) -> dict[str, Any]:
        """サーバー情報を取得する。"""
        # GET /info
        data = await self._request("GET", "/info")
        # 辞書以外は不正
        if not isinstance(data, dict):
            raise PalworldAPIError("info 応答の形式が不正です。")
        return data

    async def get_metrics(self) -> dict[str, Any]:
        """サーバーメトリクスを取得する。"""
        # GET /metrics
        data = await self._request("GET", "/metrics")
        # 辞書以外は不正
        if not isinstance(data, dict):
            raise PalworldAPIError("metrics 応答の形式が不正です。")
        return data

    async def get_settings(self) -> dict[str, Any]:
        """サーバー設定を取得する。"""
        # GET /settings
        data = await self._request("GET", "/settings")
        # 辞書以外は不正
        if not isinstance(data, dict):
            raise PalworldAPIError("settings 応答の形式が不正です。")
        return data

    async def kick(self, userid: str, message: str) -> Any:
        """プレイヤーをキックする。"""
        # POST /kick
        return await self._request(
            "POST",
            "/kick",
            json_body={"userid": userid, "message": message},
        )

    async def ban(self, userid: str, message: str) -> Any:
        """プレイヤーを BAN する。"""
        # POST /ban
        return await self._request(
            "POST",
            "/ban",
            json_body={"userid": userid, "message": message},
        )

    async def unban(self, userid: str) -> Any:
        """プレイヤーの BAN を解除する。"""
        # POST /unban
        return await self._request(
            "POST",
            "/unban",
            json_body={"userid": userid},
        )

    async def announce(self, message: str) -> Any:
        """全体アナウンスを送る。"""
        # POST /announce
        return await self._request(
            "POST",
            "/announce",
            json_body={"message": message},
        )

    async def save(self) -> Any:
        """ワールドを保存する。"""
        # POST /save
        return await self._request("POST", "/save")

    async def shutdown(self, waittime: int, message: str) -> Any:
        """猶予付きでサーバーをシャットダウンする。"""
        # POST /shutdown
        return await self._request(
            "POST",
            "/shutdown",
            json_body={"waittime": waittime, "message": message},
        )

    async def stop(self) -> Any:
        """サーバーを即時強制停止する。"""
        # POST /stop
        return await self._request("POST", "/stop")
