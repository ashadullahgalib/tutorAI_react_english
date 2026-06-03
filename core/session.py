from dataclasses import dataclass, field


@dataclass
class SessionState:
    chat_history: list = field(default_factory=list)
    current_topic: str | None = None
    active_concept: str | None = None
    last_answer_entity: str | None = None
    current_subject: str | None = None

    def reset(self):
        self.chat_history.clear()
        self.current_topic = None
        self.active_concept = None
        self.last_answer_entity = None
        self.current_subject = None

    def trim_history(self, limit: int):
        if len(self.chat_history) > limit:
            self.chat_history = self.chat_history[-limit:]

    def remember(self, role: str, content: str, limit: int):
        self.chat_history.append({"role": role, "content": content})
        self.trim_history(limit)

    def update_from_retrieved(self, retrieved: list):
        if retrieved:
            top = retrieved[0]
            self.current_topic = f"{top.get('topic','')} {top.get('subtopic','')}".lower().strip()
            self.active_concept = self.current_topic
