import os
from crewai import Agent, Task, Crew, Process

# 保險：如果你只設了 OPENROUTER_API_KEY，也能跑（但我仍建議 Secrets 補 OPENAI_API_KEY）
if not os.getenv("OPENAI_API_KEY") and os.getenv("OPENROUTER_API_KEY"):
    os.environ["OPENAI_API_KEY"] = os.getenv("OPENROUTER_API_KEY")
    os.environ["OPENAI_BASE_URL"] = os.getenv("OPENAI_BASE_URL", "https://openrouter.ai/api/v1")
    os.environ["OPENAI_API_BASE"] = os.getenv("OPENAI_API_BASE", "https://openrouter.ai/api/v1")

# 注意：model 名稱用 OpenRouter 的格式：provider/model
# 你可以先用便宜穩的：openai/gpt-4o-mini 或 anthropic/claude-3.5-haiku
MODEL = os.getenv("OPENROUTER_MODEL", "openai/gpt-4o-mini")

agent = Agent(
    role="Tester",
    goal="Return a short greeting to confirm CrewAI is working.",
    backstory="You are a minimal test agent.",
    allow_delegation=False,
    verbose=True,
    llm=MODEL,
)

task = Task(
    description="Say hello in one sentence.",
    expected_output="One short greeting sentence.",
    agent=agent,
)

crew = Crew(
    agents=[agent],
    tasks=[task],
    process=Process.sequential,
    verbose=True,
)

result = crew.kickoff()
print("\n=== RESULT ===\n", result)
