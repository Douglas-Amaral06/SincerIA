from dataclasses import dataclass
from enum import Enum


class PersonalityMode(str, Enum):
    NORMAL = "normal"
    SINCERA = "sincera"
    ACIDA = "acida"
    NUCLEAR = "nuclear"


@dataclass(frozen=True)
class PersonalityProfile:
    name: str

    honesty: int
    directness: int

    sarcasm: int
    arrogance: int
    roast: int
    profanity: int

    affection: int
    verbosity: int

    description: str

    def validate(self):
        fields = {
            "honesty": self.honesty,
            "directness": self.directness,
            "sarcasm": self.sarcasm,
            "arrogance": self.arrogance,
            "roast": self.roast,
            "profanity": self.profanity,
            "affection": self.affection,
            "verbosity": self.verbosity,
        }

        for name, value in fields.items():
            if not 0 <= value <= 100:
                raise ValueError(
                    f"{name} deve estar entre 0 e 100."
                )