"""
檔案用途：艾薇手工坊 (Ivy House) 虛擬開發團隊 (Virtual Dev Team)
使用方式：python scripts/dev_team.py "您的開發需求"

角色：
1. 艾薇規劃師 (Planner): 產出 Spec
2. 全端工程師 (Engineer): 實際讀寫檔案與寫作程式碼
3. 艾薇品管員 (QA): 審查程式碼

具備能力：
- 讀取專案檔案
- 寫入/修改專案檔案
"""

import os
import sys
from textwrap import dedent
from typing import List, Optional

# CrewAI imports
from crewai import Agent, Crew, Process, Task
from crewai_tools import FileReadTool, FileWriterTool, DirectoryReadTool
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI

# 載入 .env 檔案
# 優先嘗試讀取 ifp.env，如果沒有才讀 .env
if os.path.exists("ifp.env"):
    load_dotenv("ifp.env")
else:
    load_dotenv()

# 設定 Model
# 判斷是否使用 Gemini
model_name = os.getenv("OPENAI_MODEL_NAME", "openai/gpt-4o-mini")
api_key = os.getenv("GOOGLE_API_KEY")

if "gemini" in model_name.lower() or api_key:
    # 使用 Google Gemini
    print(f"🤖 使用 Google Gemini 模型: {model_name}")

    # CrewAI 對於 Gemini 的支援：
    # 1. 模型名稱需要以 "gemini/" 開頭 (例如 "gemini/gemini-1.5-pro")
    # 2. 需要環境變數 GOOGLE_API_KEY (已由 .env載入)
    # 3. 為了避開 OpenAI Key 檢查，有時需要設個假值
    if "OPENAI_API_KEY" not in os.environ:
        os.environ["OPENAI_API_KEY"] = "NA"

    # 處理模型名稱
    if model_name.startswith("openai/"):
        # 如果原本是 openai/gemini... (怪怪的) 就只取後面
        clean_name = model_name.replace("openai/", "")
    else:
        clean_name = model_name

    if not clean_name.startswith("gemini/"):
        # 確保有 gemini/ 前綴
        final_model = f"gemini/{clean_name}"
    else:
        final_model = clean_name

    # [FIX] 自動修正目前 API 不支援的模型名稱
    if "gemini-3.0" in final_model:
        print(f"⚠️ 偵測到尚未開放的 {final_model}，自動切換至穩定的 gemini-1.5-pro")
        final_model = "gemini/gemini-1.5-pro"

    default_llm = final_model
    advanced_llm = final_model
else:
    # 使用 OpenAI (預設)
    print(f"🤖 使用 OpenAI 模型: {model_name}")
    default_llm = model_name
    advanced_llm = os.getenv("OPENROUTER_MODEL_PLANNER", "openai/gpt-4o")


# ==============================================================================
# 工具定義 (Tool Definitions)
# ==============================================================================
# 讓 Agent 可以讀寫當前目錄下的檔案
file_read_tool = FileReadTool()
file_write_tool = FileWriterTool()
dir_read_tool = DirectoryReadTool()

# ==============================================================================
# 角色定義 (Agent Definitions)
# ==============================================================================


class IvyDevAgents:
    def planner_agent(self):
        return Agent(
            role="艾薇規劃師 (Planner)",
            goal="產出符合『鼎新 A1』邏輯與專案規範的開發規格書 (Spec)",
            backstory=dedent("""
                你是艾薇手工坊的首席系統規劃師。
                你極度熟悉專案現有的檔案結構與商業邏輯 (BOM, 庫存, 效期)。
                你的工作是將使用者的需求轉化為工程師可執行的 Spec。
                你必須先『閱讀現有相關檔案』確認邏輯後，再產出規格。
            """),
            tools=[file_read_tool, dir_read_tool],  # 規劃師需要看現有檔案才能規劃
            verbose=True,
            allow_delegation=False,
            llm=advanced_llm,
        )

    def engineer_agent(self):
        return Agent(
            role="全端工程師 (The Engineer)",
            goal="實作功能並直接修改程式碼檔案",
            backstory=dedent("""
                你是一名實戰派的全端工程師，擁有檔案系統的讀寫權限。
                你負責根據 Planner 的 Spec，**直接修改或建立** 專案中的程式碼檔案。
                你嚴格遵守由 QA 審查的規範 (ivy_house_rules.md)。
                寫入檔案前，你務必確認內容是完整且可執行的程式碼。
            """),
            tools=[file_read_tool, file_write_tool, dir_read_tool],  # 工程師有核心寫入權限
            verbose=True,
            allow_delegation=False,
            llm=default_llm,
        )

    def qa_agent(self):
        return Agent(
            role="艾薇品管員 (Ivy QA)",
            goal="審查工程師的修改，確保無資安風險且符合規範",
            backstory=dedent("""
                你是最嚴格的 Code Reviewer。
                你會檢查工程師剛寫入的檔案內容 (或計畫寫入的內容)。
                如果有嚴重問題 (Hard-code key, 邏輯錯誤)，你會要求工程師重寫。
            """),
            tools=[file_read_tool],  # QA 需要讀檔來檢查
            verbose=True,
            allow_delegation=False,
            llm=advanced_llm,
        )

    def meta_ads_expert_agent(self):
        return Agent(
            role="Meta廣告數據專家 (Meta Ads Expert)",
            goal="協助撰寫 Meta Marketing API 串接與數據分析的 Python 程式碼",
            backstory=dedent("""
                你是 Meta 行銷 API 與數據分析的專家。
                你的專長是協助全端工程師處理複雜的廣告數據邏輯。
                你知道 ROAS = Revenue / Spend。
                你精通 'facebook-business' Python 套件與 pandas 資料處理。
                你的程式碼風格乾淨模組化，且總是優先使用 pandas 處理 CSV 數據。
            """),
            tools=[
                file_read_tool
            ],  # 專家主要是提供諮詢與程式碼片段，不一定直接寫檔，但可以給 Engineer 參考
            verbose=True,
            allow_delegation=False,
            llm=advanced_llm,
        )


# ==============================================================================
# 任務定義 (Task Definitions)
# ==============================================================================


class IvyDevTasks:
    def plan_task(self, agent, user_request):
        return Task(
            description=dedent(f"""
                **使用者需求**：
                {user_request}

                **任務**：
                1. 使用工具掃描當前目錄，理解專案結構。
                2. 根據需求，讀取相關的程式碼檔案 (例如 app.py, scripts/...)。
                3. 撰寫一份詳細的開發規格 (Spec)，包含要修改哪些檔案、具體邏輯為何。
                4. 確保符合『鼎新 A1』邏輯與『繁體中文』規範。
            """),
            agent=agent,
            expected_output="一份包含檔案修改路徑與邏輯的 Markdown 規格書。",
        )

    def implement_task(self, agent, context_input):
        return Task(
            description=dedent(f"""
                **依據規格**：
                (請參考上一份任務的 Spec)

                **任務**：
                1. 根據 Spec，使用 FileWriterTool **實際建立或修改** 檔案。
                2. 這是來真的！請確保程式碼可以運作。
                3. 每一個檔案修改前，請先讀取舊內容確認上下文。
                4. 嚴格遵守：單檔 < 500 行，加上中文檔案用途註釋。
            """),
            agent=agent,
            context=context_input,  # 傳入 Planner 的產出
            expected_output="列出已修改或建立的檔案清單，並簡述修改內容。",
        )

    def review_task(self, agent, context_input):
        return Task(
            description=dedent(f"""
                **審查變更**：
                (請參考工程師的實作報告)

                **任務**：
                1. 讀取工程師剛修改的檔案。
                2. 執行 Code Review Checklist：
                   - 🚨 無 Hard-code API Key?
                   - 🏢 符合 ERP 邏輯?
                   - 💻 檔案是否有中文註釋?
                3. 產出審查報告。若有問題，明確指出需要修正的地方 (雖然此流程不再回頭修改，但需留紀錄)。
            """),
            agent=agent,
            context=context_input,  # 傳入 Engineer 的產出
            expected_output="一份 Code Review 通過確認書或改善建議。",
        )


# ==============================================================================
# 執行流程 (Execution Flow)
# ==============================================================================


def run_dev_team(request: str):
    agents = IvyDevAgents()
    tasks = IvyDevTasks()

    planner = agents.planner_agent()
    engineer = agents.engineer_agent()
    qa = agents.qa_agent()
    expert = agents.meta_ads_expert_agent()  # 新增專家

    # 定義任務順序
    plan = tasks.plan_task(planner, request)
    implement = tasks.implement_task(engineer, [plan])
    review = tasks.review_task(qa, [implement])

    # 專家可以在 Engineer 實作時提供協助 (透過 CrewAI 的協作機制，或者我們可以在這裡不顯式分配任務，
    # 僅作為 resource，也可以讓 Engineer 有權限 delegate 問題給專家)
    # 但為了展現專家的價值，我們這裡把專家加入 Crew agents 列表

    crew = Crew(
        agents=[planner, engineer, qa, expert],  # 加入专家
        tasks=[plan, implement, review],
        process=Process.sequential,
        verbose=True,
    )

    print(f"\n🤖 艾薇虛擬開發團隊啟動！\n目標任務：{request}\n")
    result = crew.kickoff()
    return result


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("請提供開發需求。例如：python scripts/dev_team.py '幫我新增一個 user_login 模組'")
        sys.exit(1)

    user_req = sys.argv[1]
    run_dev_team(user_req)
