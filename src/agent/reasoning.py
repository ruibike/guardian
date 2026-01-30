"""
Reasoning Engine - Motor de Raciocínio Autónomo
Implementa Chain of Thought (CoT) para raciocínio estruturado
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict
from enum import Enum


class ThoughtType(Enum):
    OBSERVATION = "observation"      # Observação do ambiente/input
    ANALYSIS = "analysis"            # Análise do problema
    HYPOTHESIS = "hypothesis"        # Hipótese a testar
    ACTION = "action"                # Ação a executar
    RESULT = "result"                # Resultado de uma ação
    CONCLUSION = "conclusion"        # Conclusão final
    ERROR = "error"                  # Erro encontrado


@dataclass
class Thought:
    """Representa um pensamento no processo de raciocínio."""
    type: ThoughtType
    content: str
    timestamp: str
    step: int
    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.type.value,
            "content": self.content,
            "timestamp": self.timestamp,
            "step": self.step,
            "metadata": self.metadata or {}
        }


class ReasoningEngine:
    """
    Motor de raciocínio que implementa Chain of Thought.
    Grava todo o processo de raciocínio para análise posterior.
    """

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.max_steps = config.get("max_steps", 10)
        self.save_to_file = config.get("save_to_file", True)
        self.log_dir = Path(config.get("log_dir", "data/reasoning"))
        self.log_dir.mkdir(parents=True, exist_ok=True)

        self.current_session: List[Thought] = []
        self.session_id: Optional[str] = None

    def start_session(self, task: str) -> str:
        """Inicia uma nova sessão de raciocínio."""
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.current_session = []

        # First thought - observe the task
        self.add_thought(
            ThoughtType.OBSERVATION,
            f"Tarefa recebida: {task}",
            {"task": task}
        )

        return self.session_id

    def add_thought(self, thought_type: ThoughtType, content: str,
                    metadata: Optional[Dict[str, Any]] = None) -> Thought:
        """Adiciona um pensamento à sessão atual."""
        thought = Thought(
            type=thought_type,
            content=content,
            timestamp=datetime.now().isoformat(),
            step=len(self.current_session) + 1,
            metadata=metadata
        )
        self.current_session.append(thought)

        # Auto-save after each thought
        if self.save_to_file:
            self._save_session()

        return thought

    def observe(self, observation: str, metadata: Optional[Dict] = None) -> Thought:
        """Regista uma observação."""
        return self.add_thought(ThoughtType.OBSERVATION, observation, metadata)

    def analyze(self, analysis: str, metadata: Optional[Dict] = None) -> Thought:
        """Regista uma análise."""
        return self.add_thought(ThoughtType.ANALYSIS, analysis, metadata)

    def hypothesize(self, hypothesis: str, metadata: Optional[Dict] = None) -> Thought:
        """Regista uma hipótese."""
        return self.add_thought(ThoughtType.HYPOTHESIS, hypothesis, metadata)

    def act(self, action: str, metadata: Optional[Dict] = None) -> Thought:
        """Regista uma ação."""
        return self.add_thought(ThoughtType.ACTION, action, metadata)

    def record_result(self, result: str, metadata: Optional[Dict] = None) -> Thought:
        """Regista o resultado de uma ação."""
        return self.add_thought(ThoughtType.RESULT, result, metadata)

    def conclude(self, conclusion: str, metadata: Optional[Dict] = None) -> Thought:
        """Regista a conclusão final."""
        return self.add_thought(ThoughtType.CONCLUSION, conclusion, metadata)

    def record_error(self, error: str, metadata: Optional[Dict] = None) -> Thought:
        """Regista um erro."""
        return self.add_thought(ThoughtType.ERROR, error, metadata)

    def get_reasoning_chain(self) -> str:
        """Retorna o raciocínio formatado como texto."""
        lines = ["=== Cadeia de Raciocínio ===\n"]

        for thought in self.current_session:
            icon = self._get_thought_icon(thought.type)
            lines.append(f"[Passo {thought.step}] {icon} {thought.type.value.upper()}")
            lines.append(f"   {thought.content}")
            if thought.metadata:
                lines.append(f"   Metadata: {thought.metadata}")
            lines.append("")

        return "\n".join(lines)

    def _get_thought_icon(self, thought_type: ThoughtType) -> str:
        """Retorna um ícone para cada tipo de pensamento."""
        icons = {
            ThoughtType.OBSERVATION: "👁️",
            ThoughtType.ANALYSIS: "🔍",
            ThoughtType.HYPOTHESIS: "💡",
            ThoughtType.ACTION: "⚡",
            ThoughtType.RESULT: "📊",
            ThoughtType.CONCLUSION: "✅",
            ThoughtType.ERROR: "❌"
        }
        return icons.get(thought_type, "•")

    def _save_session(self):
        """Guarda a sessão atual em ficheiro."""
        if not self.session_id:
            return

        filepath = self.log_dir / f"session_{self.session_id}.json"
        data = {
            "session_id": self.session_id,
            "thoughts": [t.to_dict() for t in self.current_session],
            "total_steps": len(self.current_session)
        }

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def load_session(self, session_id: str) -> bool:
        """Carrega uma sessão anterior."""
        filepath = self.log_dir / f"session_{session_id}.json"

        if not filepath.exists():
            return False

        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.session_id = data["session_id"]
        self.current_session = [
            Thought(
                type=ThoughtType(t["type"]),
                content=t["content"],
                timestamp=t["timestamp"],
                step=t["step"],
                metadata=t.get("metadata")
            )
            for t in data["thoughts"]
        ]

        return True

    def list_sessions(self) -> List[Dict[str, Any]]:
        """Lista todas as sessões de raciocínio gravadas."""
        sessions = []

        for filepath in self.log_dir.glob("session_*.json"):
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    sessions.append({
                        "session_id": data["session_id"],
                        "total_steps": data["total_steps"],
                        "file": str(filepath)
                    })
            except (json.JSONDecodeError, KeyError):
                continue

        return sorted(sessions, key=lambda x: x["session_id"], reverse=True)

    def should_continue(self) -> bool:
        """Verifica se o raciocínio deve continuar."""
        if len(self.current_session) >= self.max_steps:
            return False

        # Check if we have a conclusion
        for thought in self.current_session:
            if thought.type == ThoughtType.CONCLUSION:
                return False

        return True

    def get_summary(self) -> Dict[str, Any]:
        """Retorna um resumo da sessão atual."""
        type_counts = {}
        for thought in self.current_session:
            type_name = thought.type.value
            type_counts[type_name] = type_counts.get(type_name, 0) + 1

        return {
            "session_id": self.session_id,
            "total_thoughts": len(self.current_session),
            "thought_types": type_counts,
            "has_conclusion": any(t.type == ThoughtType.CONCLUSION for t in self.current_session),
            "has_errors": any(t.type == ThoughtType.ERROR for t in self.current_session)
        }
