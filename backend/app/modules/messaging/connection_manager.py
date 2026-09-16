"""
Registro de conexoes WebSocket ativas, para entregar mensagens na hora a quem esta com
a Inbox aberta. Quem nao esta conectado simplesmente nao recebe nada por aqui -- a
mensagem ja foi persistida pelo POST REST antes de chegar neste modulo, entao ela
aparece do mesmo jeito no proximo carregamento da tela.

Vive em memoria de processo: com mais de um worker de API, cada um teria seu proprio
dicionario e um usuario conectado no worker A nao receberia o push de uma mensagem
processada no worker B (e o motivo do Redis Pub/Sub da Fase 4 da spec) -- fora de
escopo aqui, onde a API roda em um unico worker.
"""
import uuid
from typing import Any

from fastapi import WebSocket


class ConnectionManager:
    def __init__(self):
        # Um set por usuario (nao um unico WebSocket) porque a mesma pessoa pode ter
        # a Inbox aberta em mais de uma aba/dispositivo ao mesmo tempo.
        self._connections: dict[uuid.UUID, set[WebSocket]] = {}

    async def connect(self, user_id: uuid.UUID, websocket: WebSocket) -> None:
        await websocket.accept()
        self._connections.setdefault(user_id, set()).add(websocket)

    def disconnect(self, user_id: uuid.UUID, websocket: WebSocket) -> None:
        conexoes = self._connections.get(user_id)
        if not conexoes:
            return
        conexoes.discard(websocket)
        if not conexoes:
            del self._connections[user_id]

    async def send_to_user(self, user_id: uuid.UUID, payload: dict[str, Any]) -> None:
        conexoes = self._connections.get(user_id)
        if not conexoes:
            return

        # Uma aba fechada sem o handshake de close (rede caiu, aba matada) deixa o
        # socket "morto" no set ate o proximo envio falhar -- por isso a limpeza
        # acontece aqui, na hora de usar, em vez de depender so do disconnect().
        mortos: list[WebSocket] = []
        for ws in conexoes:
            try:
                await ws.send_json(payload)
            except Exception:
                mortos.append(ws)

        for ws in mortos:
            conexoes.discard(ws)
        if not conexoes:
            del self._connections[user_id]


manager = ConnectionManager()
