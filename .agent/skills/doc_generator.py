# -*- coding: utf-8 -*-
"""
.agent/skills/doc_generator.py
=====================================
用途：Python 文件自動生成工具
職責：從 Python 檔案中提取 docstring，自動產生 Markdown 格式說明文件
=====================================

使用方式：
    python .agent/skills/doc_generator.py <file_path>

輸出：
    Markdown 格式的文件內容
"""

import sys
import ast
from pathlib import Path
from typing import Optional, List


def extract_docstring(node: ast.AST) -> Optional[str]:
    """從 AST 節點中提取 docstring"""
    if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
        if node.body and isinstance(node.body[0], ast.Expr):
            if isinstance(node.body[0].value, ast.Constant):
                value = node.body[0].value.value
                if isinstance(value, str):
                    return value.strip()
    return None


def get_function_signature(node: ast.FunctionDef) -> str:
    """取得函式簽名"""
    args = []
    for arg in node.args.args:
        arg_str = arg.arg
        if arg.annotation:
            arg_str += f": {ast.unparse(arg.annotation)}"
        args.append(arg_str)

    signature = f"{node.name}({', '.join(args)})"

    if node.returns:
        signature += f" -> {ast.unparse(node.returns)}"

    return signature


def generate_markdown(file_path: str) -> str:
    """從 Python 檔案生成 Markdown 文件"""
    path = Path(file_path)

    # 檢查檔案是否存在
    if not path.exists():
        return f"# 錯誤\n\n檔案不存在：`{file_path}`"

    # 讀取並解析檔案
    try:
        content = path.read_text(encoding="utf-8")
        tree = ast.parse(content)
    except SyntaxError as e:
        return f"# 錯誤\n\n無法解析 Python 檔案：`{str(e)}`"
    except Exception as e:
        return f"# 錯誤\n\n讀取檔案失敗：`{str(e)}`"

    # 開始生成 Markdown
    md_lines: List[str] = []

    # 標題 (使用檔案名稱)
    md_lines.append(f"# {path.name}")
    md_lines.append("")

    # 模組層級 docstring
    module_doc = extract_docstring(tree)
    if module_doc:
        md_lines.append("## 模組說明")
        md_lines.append("")
        md_lines.append(module_doc)
        md_lines.append("")

    # 收集類別與函式
    classes: List[ast.ClassDef] = []
    functions: List[ast.FunctionDef] = []

    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.ClassDef):
            classes.append(node)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            functions.append(node)

    # 生成類別文件
    if classes:
        md_lines.append("## 類別 (Classes)")
        md_lines.append("")
        for cls in classes:
            md_lines.append(f"### `{cls.name}`")
            md_lines.append("")
            cls_doc = extract_docstring(cls)
            if cls_doc:
                md_lines.append(cls_doc)
                md_lines.append("")

            # 列出類別方法
            methods = [n for n in cls.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
            if methods:
                md_lines.append("**方法：**")
                md_lines.append("")
                for method in methods:
                    sig = get_function_signature(method)
                    method_doc = extract_docstring(method)
                    md_lines.append(f"- `{sig}`")
                    if method_doc:
                        # 只取第一行作為簡短說明
                        first_line = method_doc.split('\n')[0]
                        md_lines.append(f"  - {first_line}")
                md_lines.append("")

    # 生成函式文件
    if functions:
        md_lines.append("## 函式 (Functions)")
        md_lines.append("")
        for func in functions:
            sig = get_function_signature(func)
            md_lines.append(f"### `{sig}`")
            md_lines.append("")
            func_doc = extract_docstring(func)
            if func_doc:
                md_lines.append(func_doc)
            else:
                md_lines.append("*（無 docstring）*")
            md_lines.append("")

    # 如果沒有任何內容
    if not classes and not functions and not module_doc:
        md_lines.append("*此檔案沒有可提取的 docstring。*")

    return "\n".join(md_lines)


def main():
    """主程式入口"""
    if len(sys.argv) < 2:
        print("# 錯誤")
        print("")
        print("使用方式：`python doc_generator.py <file_path>`")
        sys.exit(1)

    file_path = sys.argv[1]
    markdown = generate_markdown(file_path)
    print(markdown)


if __name__ == "__main__":
    main()
