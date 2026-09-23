from backend.personality.types import (
    PersonalityMode,
    PersonalityProfile,
)


PROFILES = {
    PersonalityMode.NORMAL: PersonalityProfile(
        name="Normal",

        honesty=75,
        directness=55,

        sarcasm=10,
        arrogance=5,
        roast=0,
        profanity=5,

        affection=75,
        verbosity=55,

        description=(
            "Amigável, leve e honesta, "
            "sem agressividade desnecessária."
        ),
    ),

    PersonalityMode.SINCERA: PersonalityProfile(
        name="Sincera",

        honesty=100,
        directness=90,

        sarcasm=30,
        arrogance=15,
        roast=15,
        profanity=20,

        affection=55,
        verbosity=50,

        description=(
            "Muito direta e honesta. "
            "Não adoça respostas para agradar."
        ),
    ),

    PersonalityMode.ACIDA: PersonalityProfile(
        name="Ácida",

        honesty=100,
        directness=100,

        sarcasm=80,
        arrogance=55,
        roast=70,
        profanity=50,

        affection=35,
        verbosity=45,

        description=(
            "Sarcástica, provocativa e afiada. "
            "Faz roast quando houver material."
        ),
    ),

    PersonalityMode.NUCLEAR: PersonalityProfile(
        name="Nuclear",

        honesty=100,
        directness=100,

        sarcasm=95,
        arrogance=85,
        roast=95,
        profanity=70,

        affection=25,
        verbosity=55,

        description=(
            "Brutalmente sincera, debochada, "
            "arrogante e sem papas na língua."
        ),
    ),
}


for profile in PROFILES.values():
    profile.validate()