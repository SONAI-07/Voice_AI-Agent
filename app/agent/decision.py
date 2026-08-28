from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, model_validator


class NextAction(str, Enum):
    ASK_QUESTION = "ask_question"
    CONTINUE = "continue"
    END_CONVERSATION = "end_conversation"


class AgentDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    response: str = Field(min_length=1)
    next_action: NextAction
    next_question: str | None = None
    reasoning_summary: str = Field(min_length=1)

    @model_validator(mode="after")
    def validate_next_question(self):
        if self.next_action == NextAction.ASK_QUESTION:
            if not self.next_question:
                raise ValueError(
                    "next_question is required when next_action is ask_question"
                )

        elif self.next_question is not None:
            raise ValueError(
                "next_question must be null unless next_action is ask_question"
            )

        return self