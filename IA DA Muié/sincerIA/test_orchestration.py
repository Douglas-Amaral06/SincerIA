import asyncio

from backend.orchestration.cooldown import (
    cooldowns,
)
from backend.orchestration.health import (
    health,
)
from backend.orchestration.router import (
    orchestrator,
)
from backend.personality.engine import (
    personality_engine,
)


async def test(
    title: str,
    user_message: str,
    mode: str = "nuclear",
):

    print()
    print("#" * 70)
    print(title)
    print("#" * 70)

    messages = (
        personality_engine.prepare_messages(
            mode=mode,
            history=[],
            user_message=user_message,
        )
    )

    try:

        result = await orchestrator.chat(
            messages=messages,
            temperature=0.9,
            max_tokens=1000,
        )

        print()
        print(
            f"MODO: {mode}"
        )

        print(
            f"ROTA: {result.route.value}"
        )

        print(
            f"PROVIDER: {result.provider}"
        )

        print(
            f"MODELO: {result.model}"
        )

        print()
        print("RESPOSTA:")
        print(result.content)

        print()
        print("TENTATIVAS:")

        for attempt in result.attempts:

            print(
                {
                    "provider": (
                        attempt.provider
                    ),
                    "model": (
                        attempt.model
                    ),
                    "success": (
                        attempt.success
                    ),
                    "skipped": (
                        attempt.skipped
                    ),
                    "failure": (
                        attempt.failure_kind.value
                        if attempt.failure_kind
                        else None
                    ),
                    "reason": (
                        attempt.reason
                    ),
                }
            )

    except Exception as exc:

        print()
        print("ERRO:")
        print(exc)


async def main():

    await test(
        title="TESTE 1 - NUCLEAR",
        mode="nuclear",
        user_message=(
            "Eu voltei a falar com meu ex "
            "pela quarta vez. Pode falar "
            "na lata o que você acha disso."
        ),
    )

    await test(
        title="TESTE 2 - ÁCIDA",
        mode="acida",
        user_message=(
            "Eu mandei mensagem para uma pessoa "
            "que já tinha me deixado no vácuo "
            "três vezes."
        ),
    )

    await test(
        title="TESTE 3 - SINCERA",
        mode="sincera",
        user_message=(
            "Estou pensando em comprar uma coisa "
            "cara que eu praticamente não vou usar."
        ),
    )

    await test(
        title="TESTE 4 - NORMAL",
        mode="normal",
        user_message=(
            "Fiz uma escolha ruim e estou "
            "arrependida. O que você acha?"
        ),
    )

    await test(
        title="TESTE 5 - REASONING NUCLEAR",
        mode="nuclear",
        user_message=(
            "Analisa tudo: estou há três anos "
            "num relacionamento, terminamos "
            "e voltamos várias vezes, brigamos "
            "pelas mesmas coisas e toda vez "
            "prometemos mudar. Quero que você "
            "identifique o padrão sem inventar "
            "coisas que eu não contei."
        ),
    )

    print()
    print("#" * 70)
    print("HEALTH")
    print("#" * 70)

    print(
        health.snapshot()
    )

    print()
    print("#" * 70)
    print("COOLDOWNS")
    print("#" * 70)

    print(
        cooldowns.snapshot()
    )


if __name__ == "__main__":

    asyncio.run(
        main()
    )