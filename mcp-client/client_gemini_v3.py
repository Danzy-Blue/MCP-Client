import asyncio, os, sys
from dotenv import load_dotenv
from google import genai
from google.genai import types
from mcp import ClientSession, StdioServerParameters
from mcp.client.streamable_http import streamablehttp_client
from mcp.client.stdio import stdio_client

load_dotenv()

# Prevent API key conflict
os.environ.pop("GOOGLE_API_KEY", None)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
SERVER_URL     = os.getenv("SERVER_URL", "http://localhost:8000/mcp")
SERVER_SCRIPT  = os.getenv("SERVER_SCRIPT", "server.py")
TRANSPORT      = os.getenv("TRANSPORT", "http").lower()
GEMINI_MODEL   = os.getenv("GEMINI_MODEL", "gemini-2.0-flash-lite")

if not GEMINI_API_KEY:
    print("Error: GEMINI_API_KEY not found in .env")
    sys.exit(1)

# Async client — fixes ExceptionGroup crash in Python 3.14
gemini_client = genai.Client(api_key=GEMINI_API_KEY)

TYPE_MAP = {
    "integer": types.Type.INTEGER,
    "number":  types.Type.NUMBER,
    "string":  types.Type.STRING,
    "boolean": types.Type.BOOLEAN,
    "object":  types.Type.OBJECT,
    "array":   types.Type.ARRAY,
}


async def main():
    try:
        if TRANSPORT == "stdio":
            print(f"Connecting via STDIO → {SERVER_SCRIPT}\n")
            async with stdio_client(StdioServerParameters(command="python", args=[SERVER_SCRIPT])) as (read, write):
                await run_chat(read, write)
        else:
            print(f"Connecting via HTTP → {SERVER_URL}\n")
            async with streamablehttp_client(SERVER_URL) as (read, write, _):
                await run_chat(read, write)
    except Exception as e:
        print(f"\n[!] Connection error: {e}")


async def run_chat(read, write):
    async with ClientSession(read, write) as session:
        await session.initialize()

        tools_result = await session.list_tools()
        print(f"\n tools_result:{tools_result}")
        print(f"\n tools_result.tools:{tools_result.tools}")

        # Build Gemini tool definitions with type + description per property
        gemini_tools = [
            types.Tool(
                function_declarations=[
                    types.FunctionDeclaration(
                        name=t.name,
                        description=t.description,
                        parameters=types.Schema(
                            type=types.Type.OBJECT,
                            properties={
                                k: types.Schema(
                                    type=TYPE_MAP.get(v.get("type", "string"), types.Type.STRING),
                                    description=v.get("description", ""),
                                )
                                for k, v in t.inputSchema.get("properties", {}).items()
                            },
                            required=t.inputSchema.get("required", []),
                        ),
                    )
                ]
            )
            for t in tools_result.tools
        ]

        print(f"Model : {GEMINI_MODEL}")
        print(f"Tools : {[t.name for t in tools_result.tools]}\n")

        # Use aio (async) interface — fixes blocking sync call inside async context
        chat = gemini_client.aio.chats.create(
            model=GEMINI_MODEL,
            config=types.GenerateContentConfig(tools=gemini_tools),
        )

        while True:
            try:
                user_input = input("You: ").strip()
                if not user_input:
                    continue
                if user_input.lower() in ("exit", "quit"):
                    print("Bye!")
                    break

                # Properly awaited — won't block MCP HTTP stream
                response = await chat.send_message(user_input)

                # Handle tool calls
                while (
                    response.candidates[0].content.parts
                    and response.candidates[0].content.parts[0].function_call
                ):
                    part = response.candidates[0].content.parts[0]
                    fn_name = part.function_call.name
                    fn_args = dict(part.function_call.args)  # MapComposite → dict

                    print(f"  [tool call]   {fn_name}({fn_args})")
                    result = await session.call_tool(fn_name, fn_args)
                    tool_output = result.content[0].text if result.content else ""
                    print(f"  [tool result] {tool_output}")

                    response = await chat.send_message(
                        types.Part.from_function_response(
                            name=fn_name,
                            response={"result": tool_output},
                        )
                    )

                # Final reply
                reply = response.text or response.candidates[0].content.parts[0].text or ""
                print(f"Assistant: {reply}\n")

            except Exception as e:
                print(f"\n[!] Error: {e}\n")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nExiting...")