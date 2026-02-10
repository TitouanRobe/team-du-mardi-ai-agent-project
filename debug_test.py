"""
DEBUG SCRIPT v2 - More verbose, higher max_llm_calls
Run: python debug_test.py
"""
import traceback
import asyncio

print("=" * 50)
print("  STEP 1: Testing imports...")
print("=" * 50)

try:
    from dotenv import load_dotenv
    load_dotenv()
    print("  ✅ dotenv OK")
except Exception as e:
    print(f"  ❌ dotenv failed: {e}")

try:
    from google.adk.runners import Runner, RunConfig
    from google.adk.sessions import InMemorySessionService
    print("  ✅ google.adk OK")
except Exception as e:
    print(f"  ❌ google.adk failed: {e}")
    traceback.print_exc()
    exit(1)

try:
    from test_agent.supervisor import root_agent
    print(f"  ✅ supervisor OK: agent={root_agent.name}")
    print(f"     sub_agents: {[a.name for a in root_agent.sub_agents]}")
except Exception as e:
    print(f"  ❌ supervisor import failed: {e}")
    traceback.print_exc()
    exit(1)


class Part:
    def __init__(self, text):
        self.text = text


class Message:
    def __init__(self, role, parts):
        self.role = role
        self.parts = parts


async def run_test():
    session_service = InMemorySessionService()

    await session_service.create_session(
        user_id="test_user",
        session_id="test_session_1",
        app_name="travel_agent"
    )
    print("  ✅ Session created")

    runner = Runner(
        agent=root_agent,
        app_name="travel_agent",
        session_service=session_service
    )
    print("  ✅ Runner created")

    print()
    print("=" * 50)
    print("  STEP 2: Running agent (Berlin -> Madrid)...")
    print("  max_llm_calls = 30")
    print("=" * 50)

    prompt = Message(role="user", parts=[Part(text="Je veux voyager de Berlin vers Madrid.")])
    run_config = RunConfig(max_llm_calls=30)

    full_text = ""
    event_count = 0
    all_tool_responses = []

    try:
        async for event in runner.run_async(
            user_id="test_user",
            session_id="test_session_1",
            new_message=prompt,
            run_config=run_config
        ):
            event_count += 1
            author = getattr(event, 'author', '???')
            is_final = getattr(event, 'is_final_response', None)

            # Show raw event info
            print(f"\n{'~'*40}")
            print(f"  Event #{event_count} | Author: {author} | is_final: {is_final}")

            # Check content
            content = getattr(event, 'content', None)
            if content is None:
                print(f"  (empty) content = None")
                continue

            parts = getattr(content, 'parts', None)
            if parts is None:
                print(f"  (empty) content.parts = None")
                # Check if content has text directly
                direct_text = getattr(content, 'text', None)
                if direct_text:
                    print(f"  TEXT (direct): {direct_text[:200]}")
                    full_text += direct_text
                continue

            print(f"  {len(parts)} part(s)")

            for i, part in enumerate(parts):
                part_type = type(part).__name__
                print(f"    Part {i} ({part_type}):")

                # Text
                text = getattr(part, 'text', None)
                if text:
                    preview = text[:200].replace('\n', '\\n')
                    print(f"      TEXT: {preview}")
                    full_text += text

                # Function call
                fc = getattr(part, 'function_call', None)
                if fc:
                    fname = getattr(fc, 'name', '?')
                    fargs = getattr(fc, 'args', {})
                    print(f"      CALL: {fname}({fargs})")

                # Function response
                fr = getattr(part, 'function_response', None)
                if fr:
                    resp_name = getattr(fr, 'name', '?')
                    resp_data = getattr(fr, 'response', '')
                    resp_str = str(resp_data)
                    all_tool_responses.append({"tool": resp_name, "data": resp_str})
                    preview = resp_str[:300].replace('\n', '\\n')
                    print(f"      RESPONSE ({resp_name}): {preview}")

    except Exception as e:
        print(f"\n  Error at event #{event_count}: {e}")
        traceback.print_exc()

    print(f"\n{'='*50}")
    print(f"  SUMMARY")
    print(f"{'='*50}")
    print(f"  Total events: {event_count}")
    print(f"  Text length: {len(full_text)} chars")
    print(f"  Tool responses captured: {len(all_tool_responses)}")

    for tr in all_tool_responses:
        print(f"\n  --- Tool: {tr['tool']} ---")
        print(f"  {tr['data'][:400]}")

    if full_text:
        print(f"\n  --- Final text ---")
        print(f"  {full_text[:800]}")
    else:
        print(f"\n  WARNING: No text captured! The response might be in tool_responses only.")


asyncio.run(run_test())