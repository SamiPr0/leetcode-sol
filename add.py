"""
Usage: python add.py <problem_number>
Creates a new problem file from the template in the main/ directory,
fetching the title, slug, difficulty, code snippet, and example tests from LeetCode.
"""

import sys
import os
import glob
import urllib.request
import urllib.error
import json
import re
import ast
from html import unescape


LEETCODE_GRAPHQL = "https://leetcode.com/graphql"

LIST_QUERY = """
query {
  problemsetQuestionList: questionList(
    categorySlug: ""
    limit: 1
    skip: %d
    filters: {}
  ) {
    questions: data {
      frontendQuestionId: questionFrontendId
      titleSlug
      title
      difficulty
    }
  }
}
"""

DETAIL_QUERY = """
query {
  question(titleSlug: "%s") {
    codeSnippets { langSlug code }
    exampleTestcaseList
    metaData
    content
    isPaidOnly
  }
}
"""


def graphql(query):
    payload = json.dumps({"query": query}).encode()
    req = urllib.request.Request(
        LEETCODE_GRAPHQL,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Referer": "https://leetcode.com/",
            "User-Agent": "Mozilla/5.0",
        },
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read())


def fetch_problem(number):
    data = graphql(LIST_QUERY % (number - 1))
    questions = data["data"]["problemsetQuestionList"]["questions"]
    if not questions or int(questions[0]["frontendQuestionId"]) != number:
        return None
    return questions[0]


def fetch_details(slug):
    data = graphql(DETAIL_QUERY % slug)
    return data["data"]["question"]


def parse_outputs(html):
    """Extract expected output values from the problem HTML content."""
    outputs = []

    # New format: <div class="example-block"> with <span class="example-io">
    new_blocks = re.findall(r'<div class="example-block">(.*?)</div>', html, re.DOTALL)
    for block in new_blocks:
        m = re.search(r"<strong>Output:</strong>\s*<span[^>]*>(.*?)</span>", block, re.DOTALL)
        if not m:
            continue
        raw = re.sub(r"<[^>]+>", "", m.group(1)).strip()
        normalized = raw.replace("true", "True").replace("false", "False").replace("null", "None")
        try:
            outputs.append(repr(ast.literal_eval(normalized)))
        except Exception:
            outputs.append(repr(raw))

    if outputs:
        return outputs

    # Old format: <pre> blocks
    blocks = re.findall(r"<pre>(.*?)</pre>", html, re.DOTALL)
    for block in blocks:
        m = re.search(r"<strong>Output:</strong>\s*(.+)", block)
        if not m:
            continue
        raw = re.sub(r"<[^>]+>", "", m.group(1)).strip()
        normalized = raw.replace("true", "True").replace("false", "False").replace("null", "None")
        try:
            outputs.append(repr(ast.literal_eval(normalized)))
        except Exception:
            outputs.append(repr(raw))
    return outputs


def build_solution(snippet):
    return snippet.rstrip() + "\n        pass"


def parse_cell(text):
    if text.lower() == "null":
        return None
    for cast in (int, float):
        try:
            return cast(text)
        except ValueError:
            pass
    return text


def parse_table_outputs(html):
    """Extract the expected output table of each example of a database problem."""
    outputs = []
    for block in re.findall(r"<pre>(.*?)</pre>", html, re.DOTALL):
        m = re.search(r"<strong>Output:</strong>(.*?)(?:<strong>Explanation|$)", block, re.DOTALL)
        if not m:
            continue
        rows = []
        for line in m.group(1).splitlines():
            line = line.strip()
            if not line.startswith("|"):
                continue
            rows.append(
                [unescape(re.sub(r"<[^>]+>", "", c)).strip() for c in line.strip("|").split("|")]
            )
        if not rows:
            outputs.append(None)
            continue
        outputs.append((rows[0], [[parse_cell(c) for c in r] for r in rows[1:]]))
    return outputs


DB_HELPER = '''def to_records(df):
    """Order-insensitive, NaN-insensitive view of a DataFrame."""
    records = [
        {k: (None if pd.isna(v) else v) for k, v in row.items()}
        for row in df.to_dict("records")
    ]
    return sorted(records, key=repr)
'''


def build_database_tests(func_name, snippet, test_cases, outputs):
    params = re.search(r"def\s+\w+\((.*?)\)", snippet, re.DOTALL).group(1)
    names = [p.split(":")[0].strip() for p in params.split(",") if p.strip()]
    lines = []
    for i, raw in enumerate(test_cases, 1):
        data = json.loads(raw)
        lines.append(f"    # Test {i}")
        for name, table in zip(names, data["headers"]):
            lines.append(
                f"    {name} = pd.DataFrame({data['rows'][table]!r}, columns={data['headers'][table]!r})"
            )
        lines.append(f"    result = {func_name}({', '.join(names)})")
        out = outputs[i - 1] if i <= len(outputs) else None
        if out:
            columns, body = out
            lines.append(f"    expected = pd.DataFrame({body!r}, columns={columns!r})")
            lines.append("    assert to_records(result) == to_records(expected)")
        else:
            lines.append("    # TODO: add the expected output")
        lines.append("")
    lines.append('    print("All tests passed.")')
    return "\n".join(lines)


def build_tests(method_name, params, test_cases, outputs):
    lines = []
    for i, (raw, expected) in enumerate(zip(test_cases, outputs), 1):
        lines.append(f"    # Test {i}")
        values = raw.split("\n")
        call_args = []
        for param, value in zip(params, values):
            name = param["name"]
            lines.append(f"    {name} = {value}")
            call_args.append(name)
        call = f"sol.{method_name}({', '.join(call_args)})"
        lines.append(f"    assert {call} == {expected}")
        lines.append("")
    lines.append('    print("All tests passed.")')
    return "\n".join(lines)


def main():
    if len(sys.argv) != 2:
        print("Usage: python add.py <problem_number>")
        sys.exit(1)

    try:
        number = int(sys.argv[1])
    except ValueError:
        print(f"Error: '{sys.argv[1]}' is not a valid problem number.")
        sys.exit(1)

    python_dir = os.path.join(os.path.dirname(__file__), "main")
    pattern = os.path.join(python_dir, f"{number:04d}_*.py")
    existing = glob.glob(pattern)

    if existing:
        print(f"Problem {number} already exists: {os.path.basename(existing[0])}")
        sys.exit(1)

    print(f"Fetching problem {number} from LeetCode...")
    try:
        problem = fetch_problem(number)
        if not problem:
            print(f"Could not find problem {number} on LeetCode.")
            sys.exit(1)
        details = fetch_details(problem["titleSlug"])
        if details.get("isPaidOnly"):
            print(f"Problem {number} is locked behind LeetCode Premium.")
            sys.exit(1)
    except urllib.error.URLError as e:
        print(f"Network error: {e}")
        sys.exit(1)

    title = problem["title"]
    difficulty = problem["difficulty"]
    slug = problem["titleSlug"]
    link = f"https://leetcode.com/problems/{slug}/"
    file_title = re.sub(r"[^a-z0-9]+", "_", title.lower()).strip("_")

    snippets = {s["langSlug"]: s["code"] for s in details["codeSnippets"] or []}
    meta = json.loads(details["metaData"] or "{}")
    test_cases = details["exampleTestcaseList"]
    header = f'''"""
Problem: {number} - {title}
Difficulty: {difficulty}

Link:
{link}

Time Complexity:
O(...)

Space Complexity:
O(...)

Notes:
"""
'''
    footer = '''

if __name__ == "__main__":
    run_tests()
'''

    if "python" in snippets and "name" in meta and "params" in meta:
        # Regular function problem: Solution class + generated asserts
        outputs = parse_outputs(details["content"])
        solution = build_solution(snippets["python"])
        tests = build_tests(meta["name"], meta["params"], test_cases, outputs)
        body = f"""

{solution}


def run_tests():
    sol = Solution()

{tests}
"""
    elif "python" in snippets:
        # Design / class-based problem: keep the template, leave tests to fill in
        body = f"""

{snippets["python"].rstrip()}


def run_tests():
    # TODO: replay the example operations
    pass
"""
    elif "pythondata" in snippets:
        # Database problem solved with pandas
        snippet = snippets["pythondata"].rstrip()
        outputs = parse_table_outputs(details["content"])
        tests = build_database_tests(meta["name"], snippet, test_cases, outputs)
        body = f"""
{snippet}
    pass


{DB_HELPER}

def run_tests():
{tests}
"""
    else:
        # Shell / anything without a Python template: keep the original as a comment
        langs = ", ".join(snippets) or "none"
        original = "\n".join(
            "# " + line for line in next(iter(snippets.values()), "").splitlines()
        )
        body = f"""
# No Python template for this problem (available: {langs}).
{original}


def run_tests():
    pass
"""

    content = header + body + footer

    filename = f"{number:04d}_{file_title}.py"
    dest = os.path.join(python_dir, filename)

    with open(dest, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"Created: main/{filename}  [{difficulty}]")


if __name__ == "__main__":
    main()
