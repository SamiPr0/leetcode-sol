# LeetCode Practice

Solutions to LeetCode problems in **Python**.

## Adding a new problem

```bash
python add.py <problem_number>
```

This will:
- Fetch the problem title, difficulty, and link from LeetCode
- Generate a file in `main/` with the solution stub and example test cases pre-filled
- Print an error if the problem already exists or requires a Premium subscription

**Example:**
```bash
python add.py 53
# Created: main/0053_maximum_subarray.py  [Medium]
```

Once the file is created, fill in your solution. The expected outputs in each `assert` are already filled in.

## 📊 Progress tracker

See the live tracker: **https://samipr0.github.io/leetcode-sol/**

It reads the `main/` folder straight from GitHub in the browser, so nothing needs to be committed when you add a problem.

