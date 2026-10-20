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

    py_snippet = next(
        (s["code"] for s in details["codeSnippets"] or [] if s["langSlug"] == "python"),
        None,
    )
    if py_snippet is None:
        print(
            f"Problem {number} ({title}) has no Python template "
            "(likely a SQL/Database or Shell problem), so it can't be generated."
        )
        sys.exit(1)
    meta = json.loads(details["metaData"])
    method_name = meta["name"]
    params = meta["params"]
    test_cases = details["exampleTestcaseList"]

    outputs = parse_outputs(details["content"])
    solution_class = build_solution(py_snippet)
    tests_body = build_tests(method_name, params, test_cases, outputs)

    content = f'''"""
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


{solution_class}


def run_tests():
    sol = Solution()

{tests_body}


if __name__ == "__main__":
    run_tests()
'''

    filename = f"{number:04d}_{file_title}.py"
    dest = os.path.join(python_dir, filename)

    with open(dest, "w") as f:
        f.write(content)

    print(f"Created: main/{filename}  [{difficulty}]")


if __name__ == "__main__":
    main()
