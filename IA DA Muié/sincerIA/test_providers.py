import asyncio

from backend.providers.registry import PROVIDERS


async def test_provider(
    name,
    provider,
):
    print()
    print("=" * 70)
    print(f"TESTANDO: {name}")
    print(f"MODELO: {provider.model}")
    print("=" * 70)

    if not provider.configured:
        print(
            f"[SKIP] {name}: "
            "API KEY não configurada."
        )
        return

    messages = [
        {
            "role": "system",
            "content": (
                "Você é uma IA direta, sincera e engraçada. "
                "Responda em português brasileiro. "
                "Não explique seu raciocínio interno. "
                "Entregue apenas a resposta final."
            ),
        },
        {
            "role": "user",
            "content": (
                "Responda em apenas uma frase: "
                "por que mandar mensagem para ex "
                "às 2 da manhã geralmente não é "
                "uma ideia brilhante?"
            ),
        },
    ]

    try:
        result = await provider.chat(
            messages=messages,
            temperature=0.7,

            # Antes estava 200.
            # Alguns reasoning models engoliam tudo
            # antes de chegar à resposta.
            max_tokens=800,
        )

        print()
        print("STATUS: OK")

        print(
            f"PROVIDER: {result.provider}"
        )

        print(
            f"MODELO: {result.model}"
        )

        print()
        print("RESPOSTA:")
        print(result.content)

    except Exception as exc:
        print()
        print("STATUS: ERRO")

        print(
            f"{type(exc).__name__}: {exc}"
        )


async def main():

    print()
    print("#" * 70)
    print("SINCERIA - TESTE DOS PROVIDERS")
    print("#" * 70)

    for name, provider in PROVIDERS.items():

        await test_provider(
            name=name,
            provider=provider,
        )

    print()
    print("#" * 70)
    print("TESTE FINALIZADO")
    print("#" * 70)


if __name__ == "__main__":
    asyncio.run(main())