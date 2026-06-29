class HumanGatePause(Exception):
    def __init__(self, node_id: str) -> None:
        self.node_id = node_id
        super().__init__(f"awaiting human gate: {node_id}")


class ExpandPause(Exception):
    def __init__(self, node_id: str) -> None:
        self.node_id = node_id
        super().__init__(f"awaiting expand confirm: {node_id}")
