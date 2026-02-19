"""
檔案用途：定義艾薇手工坊 (Ivy House) 的 CrewAI Agents 角色與任務邏輯
角色包含：艾薇規劃師 (Planner)、全端工程師 (Engineer)、艾薇品管員 (QA)
"""

import os
from textwrap import dedent

from crewai import Agent, Crew, Process, Task

# 如果有使用到 tools，可以在此 import，例如 FileReadTool 等
# from crewai_tools import FileReadTool, CodeInterpreterTool

# ==============================================================================
# 角色定義 (Agent Definitions)
# ==============================================================================


class IvyAgents:
    def __init__(self):
        # 這裡的 model 可以根據使用者偏好動態調整
        # 預設使用環境變數中的 OPENAI_MODEL_NAME 或者指定特定的 model string
        self.default_model = os.getenv("OPENAI_MODEL_NAME", "openai/gpt-4o-mini")
        self.advanced_model = os.getenv("OPENROUTER_MODEL_PLANNER", "openai/gpt-4o")

    def planner_agent(self):
        """
        艾薇規劃師 (Planner)
        職責：系統規劃、規格制定、邏輯驗證
        """
        return Agent(
            role="艾薇規劃師 (Planner)",
            goal="產出高品質、符合鼎新 A1 邏輯的系統開發規格書 (Spec)",
            backstory=dedent("""
                你是艾薇手工坊的首席系統規劃師。你擁有深厚的 ERP 與烘焙業領域知識。
                你極度重視資料結構的正確性與邏輯的嚴謹度。
                你的工作是將模糊的需求轉化為工程師可以執行的精確規格。
                你非常熟悉「鼎新 A1」的設計哲學。
            """),
            verbose=True,
            allow_delegation=False,
            llm=self.advanced_model,  # 建議使用更強的模型如 Opus/4o
        )

    def engineer_agent(self):
        """
        全端工程師 (The Engineer)
        職責：程式碼實作、功能開發、除錯
        """
        return Agent(
            role="全端工程師 (The Engineer)",
            goal="根據 Spec 撰寫乾淨、模組化且通過測試的程式碼",
            backstory=dedent("""
                你是一名重視品質的全端工程師。你嚴格遵守 ivy_house_rules.md。
                你堅持「Mock-First」開發，絕不 Hard-code 敏感資訊。
                你的程式碼簡潔易讀，單一檔案絕不超過 300-500 行。
                你只寫繁體中文的註解。
            """),
            verbose=True,
            allow_delegation=False,
            # engineer 可以根據需要掛載工具，例如 FileReadTool, FileWriteTool 等
            # tools=[...],
            llm=self.default_model,
        )

    def qa_agent(self):
        """
        艾薇品管員 (Ivy QA)
        職責：程式碼審查 (Code Review)、邏輯找碴、資安檢查
        """
        return Agent(
            role="艾薇品管員 (Ivy QA)",
            goal="嚴格審查程式碼品質與資安，確保零錯誤交付",
            backstory=dedent("""
                你是團隊中最嚴格的守門員。你的眼睛能抓出任何資安紅線和邏輯漏洞。
                你特別關注這四點：1. 資安紅線 2. ERP 商業邏輯 3. 程式碼品質 4. UI/UX 品牌。
                你只接受完美的程式碼，對於違規事項絕不留情。
            """),
            verbose=True,
            allow_delegation=False,
            llm=self.advanced_model,  # QA 也建議使用較強模型
        )


# ==============================================================================
# 任務定義 (Task Definitions)
# ==============================================================================


class IvyTasks:
    def plan_task(self, agent, user_request):
        return Task(
            description=dedent(f"""
                **接收需求**：
                {user_request}

                **任務**：
                1. 仔細閱讀需求，並以自己的話複述確認。
                2. 產出詳細規格 (Spec)，包含：
                   - 資料庫 Schema (Mermaid 圖或 SQL)
                   - 模組依賴關係
                   - 驗收標準 (AC)
                3. 請確保資料設計符合「鼎新 A1」邏輯與烘焙業特性 (效期、BOM)。
            """),
            agent=agent,
            expected_output="一份完整的 Markdown 格式需求規格書，包含 DB Schema 與驗收標準。",
        )

    def implement_task(self, agent, spec_content):
        return Task(
            description=dedent(f"""
                **依據規格**：
                {spec_content}

                **任務**：
                1. 根據 Spec 開發功能。
                2. 優先建立 Mock Data 進行測試。
                3. 實作核心邏輯與 UI。
                4. 進行自我檢查 (檔案註釋、資安檢查)。
                5. 產出程式碼檔案 (請標註檔案路徑與內容)。
            """),
            agent=agent,
            expected_output="完整的 Python/HTML/JS 程式碼區塊，符合模組化與註釋規範。",
        )

    def review_task(self, agent, code_content):
        return Task(
            description=dedent(f"""
                **審查程式碼**：
                {code_content}

                **任務**：
                請依照以下清單嚴格審查：
                1. 🚨 資安紅線 (有無 Hard-code Key?)
                2. 🏢 商業邏輯 (符合 ERP?)
                3. 💻 程式碼品質 (檔案長度、註釋)
                4. 🎨 UI/UX (符合品牌色?)

                **輸出要求**：
                - 若通過：回覆「✅ 通過審查，可以合併。」
                - 若拒絕：回覆「❌ [檔案:行數] 違反 [規則]：說明原因。」
            """),
            agent=agent,
            expected_output="一份詳細的 Code Review 報告，包含通過/拒絕的結論與具體修改建議。",
        )


# ==============================================================================
# 主要執行入口 (Crew Definition)
# ==============================================================================


def run_ivy_dev_flow(user_request: str):
    """
    執行完整的開發流程：Plan -> Implement -> Review
    """
    agents = IvyAgents()
    tasks = IvyTasks()

    # 1. 實例化 Agents
    planner = agents.planner_agent()
    engineer = agents.engineer_agent()
    qa = agents.qa_agent()

    # 2. 定義 Tasks (這裡示範循序執行，後一個任務吃前一個的輸出)
    #    CrewAI 預設會將前一個 Task 的 output 作為 context 傳給下一個 Task

    task_plan = tasks.plan_task(planner, user_request)
    task_implement = tasks.implement_task(
        engineer, user_request
    )  # Engineer 也需要知道原始需求，或者只依賴 spec
    # 更好的做法是讓 Crew 自動傳遞 context，這裡我們先簡單設定
    # 在 Crew 中，tasks 順序決定了執行順序

    task_implement.context = [task_plan]  # 明確指定依賴

    task_review = tasks.review_task(qa, user_request)  # QA 審查的是 Engineer 的產出
    task_review.context = [task_implement]  # QA 依賴實作結果

    # 3. 建立 Crew
    crew = Crew(
        agents=[planner, engineer, qa],
        tasks=[task_plan, task_implement, task_review],
        process=Process.sequential,  # 循序執行
        verbose=True,
    )

    result = crew.kickoff()
    return result


if __name__ == "__main__":
    # 本地測試用
    print("Initializing Ivy House Crew...")
    sample_request = (
        "我想開發一個『原料過期預警系統』，當原料效期少於 7 天時，在首頁顯示紅色警告卡片。"
    )
    result = run_ivy_dev_flow(sample_request)
    print("\n\n########################\nFINAL RESULT\n########################\n")
    print(result)
