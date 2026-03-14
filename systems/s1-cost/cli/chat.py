"""Nano Claude Code — lightweight terminal AI assistant via Amazon Bedrock."""

import sys

from utils.bedrock import stream_converse
from utils.metrics import publish_metrics
from cli.commands import handle_command
from cli.session import SYSTEM_PROMPT, Session

try:
    from rich.console import Console
    from rich.markdown import Markdown

    _console = Console()
    _HAS_RICH = True
except ImportError:
    _HAS_RICH = False


def _print_assistant(text: str) -> None:
    if _HAS_RICH:
        _console.print(Markdown(text))
    else:
        print(text)


def _print_meta(model: str, input_tokens: int, output_tokens: int, cost: float) -> None:
    print(f"  [{model} | {input_tokens} in | {output_tokens} out | ${cost:.6f}]")


def main() -> None:
    session = Session(model="sonnet")
    print("Nano Claude Code  (type /help for commands, Ctrl+C to quit)\n")

    try:
        while True:
            try:
                user_input = input("You> ").strip()
            except EOFError:
                break

            if not user_input:
                continue

            if user_input.startswith("/"):
                result = handle_command(user_input, session)
                if result is None:
                    break
                print(result)
                continue

            session.add_user_message(user_input)

            # Stream response
            chunks: list[str] = []
            gen = stream_converse(
                model_name=session.model,
                messages=session.messages,
                system_prompt=SYSTEM_PROMPT,
            )

            print()
            try:
                while True:
                    chunk = next(gen)
                    sys.stdout.write(chunk)
                    sys.stdout.flush()
                    chunks.append(chunk)
            except StopIteration as e:
                usage = e.value or {"input_tokens": 0, "output_tokens": 0}

            full_text = "".join(chunks)
            print("\n")

            # Re-render with rich if available (replaces raw streaming text)
            if _HAS_RICH and full_text:
                # Move cursor up to overwrite raw text — skip for simplicity,
                # just show metadata below the streamed output.
                pass

            input_tokens = usage["input_tokens"]
            output_tokens = usage["output_tokens"]
            cost = session.calculate_cost(input_tokens, output_tokens)

            session.add_assistant_message(full_text)
            session.record_usage(input_tokens, output_tokens, cost)

            _print_meta(session.model, input_tokens, output_tokens, cost)

            # Publish to CloudWatch
            try:
                publish_metrics(
                    model_id=session.model,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    cost_usd=cost,
                )
            except Exception as e:
                print(f"  [CloudWatch publish failed: {e}]")

            print()

    except KeyboardInterrupt:
        print()

    # Exit summary
    s = session.stats
    if s.calls > 0:
        print(f"\nSession total: {s.calls} calls | {s.input_tokens} in / {s.output_tokens} out | ${s.cost_usd:.6f}")
    print("Bye!")


if __name__ == "__main__":
    main()
