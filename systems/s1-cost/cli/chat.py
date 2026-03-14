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


def _print_meta(model: str, input_tokens: int, output_tokens: int, cost: float) -> None:
    print(f"  [{model} | {input_tokens} in | {output_tokens} out | ${cost:.6f}]")


def _count_lines(text: str) -> int:
    """Count displayed lines for cursor manipulation."""
    if not text:
        return 0
    cols = _console.width if _HAS_RICH else 80
    lines = 0
    for line in text.split("\n"):
        lines += max(1, -(-len(line) // cols))  # ceil division
    return lines


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

            # Merge pending file context into this message
            prefix = session.consume_file_context()
            message = f"{prefix}\n\n{user_input}" if prefix else user_input
            session.add_user_message(message)

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

            # Re-render with rich markdown if available
            if _HAS_RICH and full_text:
                raw_lines = _count_lines(full_text)
                sys.stdout.write(f"\033[{raw_lines}A\033[J")
                _console.print(Markdown(full_text))
            else:
                print()

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
