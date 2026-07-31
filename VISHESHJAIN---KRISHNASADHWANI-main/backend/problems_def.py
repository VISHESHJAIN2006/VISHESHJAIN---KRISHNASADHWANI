"""
Original DSA problem bank.
Each problem = metadata + a verified reference solution + a case generator.
Test cases are produced by RUNNING the reference solution on generated
inputs -- never hand-typed -- so expected outputs are guaranteed correct
for the given solution.

Input/Output convention:
  - `gen_cases(rng)` yields raw Python objects (the function argument(s))
  - `solve(*args)` is the reference solution, returns the expected result
  - For import into the platform, input is serialized as one JSON value
    per line (or a JSON list of args), output as JSON.
"""
import random
import json
import heapq
from collections import deque, Counter

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def rand_list(rng, n_min=0, n_max=12, lo=-50, hi=50):
    n = rng.randint(n_min, n_max)
    return [rng.randint(lo, hi) for _ in range(n)]

def rand_string(rng, n_min=1, n_max=12, alphabet="abcdefg"):
    n = rng.randint(n_min, n_max)
    return "".join(rng.choice(alphabet) for _ in range(n))

# ---------------------------------------------------------------------------
# Reference solutions (one per problem)
# ---------------------------------------------------------------------------

def sol_pair_sum(arr, target):
    seen = {}
    for i, v in enumerate(arr):
        need = target - v
        if need in seen:
            return [seen[need], i]
        seen[v] = i
    return [-1, -1]

def sol_max_subarray(arr):
    if not arr:
        return 0
    best = cur = arr[0]
    for v in arr[1:]:
        cur = max(v, cur + v)
        best = max(best, cur)
    return best

def sol_rotate_array(arr, k):
    n = len(arr)
    if n == 0:
        return []
    k %= n
    return arr[-k:] + arr[:-k] if k else arr[:]

def sol_product_except_self(arr):
    n = len(arr)
    res = [1] * n
    left = 1
    for i in range(n):
        res[i] = left
        left *= arr[i]
    right = 1
    for i in range(n - 1, -1, -1):
        res[i] *= right
        right *= arr[i]
    return res

def sol_first_unique_char(s):
    c = Counter(s)
    for i, ch in enumerate(s):
        if c[ch] == 1:
            return i
    return -1

def sol_valid_anagram(a, b):
    return Counter(a) == Counter(b)

def sol_longest_common_prefix(words):
    if not words:
        return ""
    prefix = words[0]
    for w in words[1:]:
        while not w.startswith(prefix):
            prefix = prefix[:-1]
            if not prefix:
                return ""
    return prefix

def sol_reverse_words(s):
    return " ".join(reversed(s.split()))

def sol_group_anagrams(words):
    groups = {}
    for w in words:
        key = "".join(sorted(w))
        groups.setdefault(key, []).append(w)
    return sorted([sorted(v) for v in groups.values()])

def sol_ll_middle(arr):
    # array represents a singly linked list; return value of the middle node
    n = len(arr)
    if n == 0:
        return None
    return arr[n // 2]

def sol_ll_reverse(arr):
    return arr[::-1]

def sol_ll_has_cycle(arr, pos):
    # arr = node values, pos = index the tail connects back to (-1 = no cycle)
    return pos != -1

def sol_ll_remove_nth_from_end(arr, n):
    idx = len(arr) - n
    if idx < 0 or idx >= len(arr):
        return arr[:]
    return arr[:idx] + arr[idx + 1:]

def sol_valid_parentheses(s):
    pairs = {')': '(', ']': '[', '}': '{'}
    stack = []
    for ch in s:
        if ch in "([{":
            stack.append(ch)
        elif ch in pairs:
            if not stack or stack.pop() != pairs[ch]:
                return False
    return not stack

def sol_min_stack_final_min(ops):
    # ops: list of ["push", v] / ["pop"] -> returns min at the end
    stack = []
    for op in ops:
        if op[0] == "push":
            stack.append(op[1])
        elif op[0] == "pop" and stack:
            stack.pop()
    return min(stack) if stack else None

def sol_next_greater_element(arr):
    res = [-1] * len(arr)
    stack = []
    for i, v in enumerate(arr):
        while stack and arr[stack[-1]] < v:
            res[stack.pop()] = v
        stack.append(i)
    return res

def sol_daily_temperatures(arr):
    res = [0] * len(arr)
    stack = []
    for i, v in enumerate(arr):
        while stack and arr[stack[-1]] < v:
            j = stack.pop()
            res[j] = i - j
        stack.append(i)
    return res

def sol_queue_via_stacks_final_state(ops):
    # ops: ["enqueue", v] / ["dequeue"] on a FIFO queue -> returns remaining list
    q = deque()
    for op in ops:
        if op[0] == "enqueue":
            q.append(op[1])
        elif op[0] == "dequeue" and q:
            q.popleft()
    return list(q)

def sol_sliding_window_max(arr, k):
    if not arr or k <= 0:
        return []
    dq = deque()
    res = []
    for i, v in enumerate(arr):
        while dq and arr[dq[-1]] <= v:
            dq.pop()
        dq.append(i)
        if dq[0] <= i - k:
            dq.popleft()
        if i >= k - 1:
            res.append(arr[dq[0]])
    return res

def _build_tree(level_arr):
    # level_arr uses None for missing nodes, standard level-order build
    if not level_arr or level_arr[0] is None:
        return None
    class N:
        __slots__ = ("v", "l", "r")
        def __init__(self, v):
            self.v = v; self.l = None; self.r = None
    root = N(level_arr[0])
    q = deque([root])
    i = 1
    while q and i < len(level_arr):
        node = q.popleft()
        if i < len(level_arr):
            lv = level_arr[i]; i += 1
            if lv is not None:
                node.l = N(lv); q.append(node.l)
        if i < len(level_arr):
            rv = level_arr[i]; i += 1
            if rv is not None:
                node.r = N(rv); q.append(node.r)
    return root

def sol_tree_max_depth(level_arr):
    root = _build_tree(level_arr)
    def depth(n):
        if n is None:
            return 0
        return 1 + max(depth(n.l), depth(n.r))
    return depth(root)

def sol_tree_inorder(level_arr):
    root = _build_tree(level_arr)
    out = []
    def go(n):
        if n is None:
            return
        go(n.l); out.append(n.v); go(n.r)
    go(root)
    return out

def sol_tree_is_balanced(level_arr):
    root = _build_tree(level_arr)
    ok = True
    def h(n):
        nonlocal ok
        if n is None:
            return 0
        lh, rh = h(n.l), h(n.r)
        if abs(lh - rh) > 1:
            ok = False
        return 1 + max(lh, rh)
    h(root)
    return ok

def sol_tree_level_order_sums(level_arr):
    root = _build_tree(level_arr)
    if root is None:
        return []
    res = []
    q = deque([root])
    while q:
        s = 0
        for _ in range(len(q)):
            n = q.popleft()
            s += n.v
            if n.l: q.append(n.l)
            if n.r: q.append(n.r)
        res.append(s)
    return res

def sol_graph_bfs_order(n, edges, start):
    adj = [[] for _ in range(n)]
    for a, b in edges:
        adj[a].append(b); adj[b].append(a)
    for a in adj:
        a.sort()
    visited = [False] * n
    order = []
    q = deque([start])
    visited[start] = True
    while q:
        u = q.popleft()
        order.append(u)
        for v in adj[u]:
            if not visited[v]:
                visited[v] = True
                q.append(v)
    return order

def sol_graph_has_path(n, edges, src, dst):
    adj = [[] for _ in range(n)]
    for a, b in edges:
        adj[a].append(b); adj[b].append(a)
    visited = [False] * n
    stack = [src]
    visited[src] = True
    while stack:
        u = stack.pop()
        if u == dst:
            return True
        for v in adj[u]:
            if not visited[v]:
                visited[v] = True
                stack.append(v)
    return src == dst

def sol_graph_connected_components(n, edges):
    parent = list(range(n))
    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x
    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb
    for a, b in edges:
        union(a, b)
    return len({find(i) for i in range(n)})

def sol_graph_shortest_path_len(n, edges, src, dst):
    adj = [[] for _ in range(n)]
    for a, b in edges:
        adj[a].append(b); adj[b].append(a)
    dist = [-1] * n
    dist[src] = 0
    q = deque([src])
    while q:
        u = q.popleft()
        for v in adj[u]:
            if dist[v] == -1:
                dist[v] = dist[u] + 1
                q.append(v)
    return dist[dst]

def sol_climb_stairs(n):
    if n <= 2:
        return max(n, 1)
    a, b = 1, 2
    for _ in range(3, n + 1):
        a, b = b, a + b
    return b

def sol_coin_change(coins, amount):
    INF = float("inf")
    dp = [0] + [INF] * amount
    for i in range(1, amount + 1):
        for c in coins:
            if c <= i and dp[i - c] + 1 < dp[i]:
                dp[i] = dp[i - c] + 1
    return dp[amount] if dp[amount] != INF else -1

def sol_lis_length(arr):
    if not arr:
        return 0
    dp = [1] * len(arr)
    for i in range(len(arr)):
        for j in range(i):
            if arr[j] < arr[i]:
                dp[i] = max(dp[i], dp[j] + 1)
    return max(dp)

def sol_knapsack01(weights, values, cap):
    n = len(weights)
    dp = [0] * (cap + 1)
    for i in range(n):
        for w in range(cap, weights[i] - 1, -1):
            dp[w] = max(dp[w], dp[w - weights[i]] + values[i])
    return dp[cap]

def sol_edit_distance(a, b):
    n, m = len(a), len(b)
    dp = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(n + 1):
        dp[i][0] = i
    for j in range(m + 1):
        dp[0][j] = j
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            if a[i - 1] == b[j - 1]:
                dp[i][j] = dp[i - 1][j - 1]
            else:
                dp[i][j] = 1 + min(dp[i - 1][j - 1], dp[i - 1][j], dp[i][j - 1])
    return dp[n][m]

def sol_activity_selection(intervals):
    intervals = sorted(intervals, key=lambda p: p[1])
    count = 0
    last_end = float("-inf")
    for s, e in intervals:
        if s >= last_end:
            count += 1
            last_end = e
    return count

def sol_min_coins_greedy(coins, amount):
    coins = sorted(coins, reverse=True)
    count = 0
    for c in coins:
        if amount <= 0:
            break
        take = amount // c
        count += take
        amount -= take * c
    return count if amount == 0 else -1

def sol_gcd(a, b):
    while b:
        a, b = b, a % b
    return a

def sol_is_prime(n):
    if n < 2:
        return False
    i = 2
    while i * i <= n:
        if n % i == 0:
            return False
        i += 1
    return True

def sol_power_mod(base, exp, mod):
    return pow(base, exp, mod)

def sol_count_set_bits(n):
    return bin(n).count("1")

def sol_single_number(arr):
    x = 0
    for v in arr:
        x ^= v
    return x

def sol_subsets(arr):
    res = [[]]
    for v in arr:
        res += [s + [v] for s in res]
    return sorted(sorted(s) for s in res)

def sol_permutations_count(arr):
    from math import factorial
    return factorial(len(arr))

def sol_binary_search(arr, target):
    lo, hi = 0, len(arr) - 1
    while lo <= hi:
        mid = (lo + hi) // 2
        if arr[mid] == target:
            return mid
        elif arr[mid] < target:
            lo = mid + 1
        else:
            hi = mid - 1
    return -1

def sol_merge_sort(arr):
    return sorted(arr)

def sol_kth_largest(arr, k):
    return heapq.nlargest(k, arr)[-1] if 1 <= k <= len(arr) else None


# ---------------------------------------------------------------------------
# Problem bank: (title, topic, difficulty, statement, constraints, solve, gen_cases)
# ---------------------------------------------------------------------------

def make_bank():
    bank = []

    def add(title, topic, difficulty, statement, constraints, arity, solve, gen_cases):
        bank.append(dict(
            title=title, topic=topic, difficulty=difficulty,
            statement=statement, constraints=constraints,
            arity=arity, solve=solve, gen_cases=gen_cases,
        ))

    # ---------------- Arrays ----------------
    add("Index Pair With Target Sum", "Arrays", "EASY",
        "Given an array of integers and a target value, return the indices of "
        "the first pair of elements (in scan order) whose values add up to the "
        "target. If no such pair exists, return [-1, -1].",
        "1 <= n <= 1000, values fit in 32-bit signed range.",
        2, sol_pair_sum,
        lambda rng: (rand_list(rng, 2, 15), rng.randint(-30, 30)))

    add("Largest Contiguous Sum", "Arrays", "MEDIUM",
        "Given an array of integers, find the largest possible sum of any "
        "contiguous (non-empty) subarray.",
        "1 <= n <= 2000.",
        1, sol_max_subarray,
        lambda rng: (rand_list(rng, 1, 15),))

    add("Rotate Array Right By K", "Arrays", "EASY",
        "Given an array and a non-negative integer k, rotate the array to the "
        "right by k steps and return the resulting array.",
        "0 <= n <= 20, 0 <= k <= 100.",
        2, sol_rotate_array,
        lambda rng: (rand_list(rng, 0, 12), rng.randint(0, 15)))

    add("Product Of All Other Elements", "Arrays", "MEDIUM",
        "Given an array of integers, return a new array where each element is "
        "the product of all elements except itself. Division is not allowed.",
        "1 <= n <= 15, avoid overflow-sensitive assumptions.",
        1, sol_product_except_self,
        lambda rng: (rand_list(rng, 1, 8, -6, 6),))

    add("Kth Largest Element", "Arrays", "MEDIUM",
        "Given an array of integers and an integer k, return the kth largest "
        "element in the array (1-indexed from the largest).",
        "1 <= k <= n <= 20.",
        2, sol_kth_largest,
        lambda rng: (rand_list(rng, 1, 12), rng.randint(1, 5)))

    # ---------------- Strings ----------------
    add("First Non-Repeating Character", "Strings", "EASY",
        "Given a lowercase string, return the index of its first "
        "non-repeating character, or -1 if every character repeats.",
        "1 <= |s| <= 200, lowercase letters only.",
        1, sol_first_unique_char,
        lambda rng: (rand_string(rng, 1, 15),))

    add("Anagram Check", "Strings", "EASY",
        "Given two lowercase strings, determine whether the second is an "
        "anagram of the first.",
        "1 <= |s| <= 200.",
        2, sol_valid_anagram,
        lambda rng: (rand_string(rng, 1, 10), rng.choice([
            lambda s: "".join(rng.sample(s, len(s))), lambda s: rand_string(rng, 1, 10)])(rand_string(rng, 1, 10))))

    add("Longest Common Prefix", "Strings", "EASY",
        "Given a list of lowercase words, return the longest string that is a "
        "prefix of every word in the list. Return an empty string if none.",
        "1 <= words.length <= 10.",
        1, sol_longest_common_prefix,
        lambda rng: ([rand_string(rng, 1, 8) for _ in range(rng.randint(1, 6))],))

    add("Reverse Word Order", "Strings", "EASY",
        "Given a sentence with words separated by single spaces, return a new "
        "sentence with the words in reverse order.",
        "1 <= |s| <= 300.",
        1, sol_reverse_words,
        lambda rng: (" ".join(rand_string(rng, 1, 6) for _ in range(rng.randint(1, 8))),))

    add("Group Anagrams Together", "Strings", "MEDIUM",
        "Given a list of lowercase words, group the words that are anagrams "
        "of each other. Return the groups sorted for determinism.",
        "1 <= words.length <= 12.",
        1, sol_group_anagrams,
        lambda rng: ([rand_string(rng, 1, 5) for _ in range(rng.randint(1, 8))],))

    # ---------------- Linked List (array-encoded) ----------------
    add("Middle Of Linked List", "Linked List", "EASY",
        "A singly linked list is given as an array of node values in order. "
        "Return the value of the middle node (if two middles, the second one).",
        "0 <= n <= 30.",
        1, sol_ll_middle,
        lambda rng: (rand_list(rng, 0, 15),))

    add("Reverse Linked List", "Linked List", "EASY",
        "A singly linked list is given as an array of node values. Return the "
        "array of values representing the reversed list.",
        "0 <= n <= 30.",
        1, sol_ll_reverse,
        lambda rng: (rand_list(rng, 0, 15),))

    add("Detect Linked List Cycle", "Linked List", "MEDIUM",
        "A linked list is given as an array of node values plus an index pos "
        "indicating where the tail connects back to (or -1 if the list is "
        "acyclic). Return true if the list has a cycle.",
        "0 <= n <= 30, -1 <= pos < n.",
        2, sol_ll_has_cycle,
        lambda rng: (rand_list(rng, 1, 10), rng.choice([-1, rng.randint(0, 5)])))

    add("Remove Nth Node From End", "Linked List", "MEDIUM",
        "A singly linked list is given as an array. Remove the nth node "
        "counting from the end and return the resulting array.",
        "1 <= n <= length.",
        2, sol_ll_remove_nth_from_end,
        lambda rng: (rand_list(rng, 1, 12), rng.randint(1, 8)))

    # ---------------- Stack ----------------
    add("Balanced Brackets", "Stack", "EASY",
        "Given a string containing only the characters ( ) [ ] { }, determine "
        "whether the brackets are balanced and properly nested.",
        "1 <= |s| <= 200.",
        1, sol_valid_parentheses,
        lambda rng: ("".join(rng.choice("()[]{}") for _ in range(rng.randint(1, 12))),))

    add("Minimum Value Tracker", "Stack", "MEDIUM",
        "A sequence of push/pop operations is applied to a stack. Given the "
        "operations in order, return the minimum value remaining on the stack "
        "after all operations, or null if the stack ends empty.",
        "1 <= ops.length <= 50.",
        1, sol_min_stack_final_min,
        lambda rng: ([rng.choice([["push", rng.randint(-20, 20)], ["pop"]]) for _ in range(rng.randint(1, 10))],))

    add("Next Greater Element", "Stack", "MEDIUM",
        "Given an array, for each element find the next element to its right "
        "that is strictly greater. If none exists, use -1.",
        "1 <= n <= 20.",
        1, sol_next_greater_element,
        lambda rng: (rand_list(rng, 1, 12, 0, 30),))

    add("Daily Temperature Wait", "Stack", "MEDIUM",
        "Given a list of daily temperatures, return for each day how many "
        "days you'd have to wait until a warmer temperature. Use 0 if never.",
        "1 <= n <= 20.",
        1, sol_daily_temperatures,
        lambda rng: (rand_list(rng, 1, 12, 30, 100),))

    # ---------------- Queue ----------------
    add("FIFO Queue Simulation", "Queue", "EASY",
        "A sequence of enqueue/dequeue operations is applied to an initially "
        "empty FIFO queue. Return the remaining elements in order after all "
        "operations are applied.",
        "1 <= ops.length <= 50.",
        1, sol_queue_via_stacks_final_state,
        lambda rng: ([rng.choice([["enqueue", rng.randint(-20, 20)], ["dequeue"]]) for _ in range(rng.randint(1, 10))],))

    add("Sliding Window Maximum", "Queue", "HARD",
        "Given an array and a window size k, return an array of the maximum "
        "value in every contiguous window of size k as it slides left to right.",
        "1 <= k <= n <= 20.",
        2, sol_sliding_window_max,
        lambda rng: (rand_list(rng, 1, 12, -20, 20), rng.randint(1, 5)))

    # ---------------- Trees (level-order array, null = missing) ----------------
    add("Binary Tree Max Depth", "Trees", "EASY",
        "A binary tree is given as a level-order array (null marks a missing "
        "child). Return the maximum depth of the tree.",
        "0 <= nodes <= 30.",
        1, sol_tree_max_depth,
        lambda rng: (_rand_tree_array(rng),))

    add("Binary Tree Inorder Values", "Trees", "EASY",
        "A binary tree is given as a level-order array (null marks a missing "
        "child). Return the values in inorder traversal.",
        "0 <= nodes <= 20.",
        1, sol_tree_inorder,
        lambda rng: (_rand_tree_array(rng, 15),))

    add("Check Height-Balanced Tree", "Trees", "MEDIUM",
        "A binary tree is given as a level-order array. Return true if for "
        "every node, the heights of its left and right subtrees differ by at "
        "most 1.",
        "0 <= nodes <= 25.",
        1, sol_tree_is_balanced,
        lambda rng: (_rand_tree_array(rng, 20),))

    add("Level Order Sums", "Trees", "MEDIUM",
        "A binary tree is given as a level-order array. Return an array with "
        "the sum of node values at each depth level, top to bottom.",
        "0 <= nodes <= 25.",
        1, sol_tree_level_order_sums,
        lambda rng: (_rand_tree_array(rng, 20),))

    # ---------------- Graphs ----------------
    add("Breadth-First Traversal Order", "Graphs", "MEDIUM",
        "Given an undirected graph with n nodes (0-indexed) and a list of "
        "edges, return the BFS visiting order starting from a given node "
        "(neighbors visited in increasing order).",
        "1 <= n <= 15.",
        3, sol_graph_bfs_order,
        lambda rng: _rand_graph(rng))

    add("Path Existence Check", "Graphs", "EASY",
        "Given an undirected graph with n nodes and a list of edges, "
        "determine whether a path exists between two given nodes.",
        "1 <= n <= 15.",
        4, sol_graph_has_path,
        lambda rng: _rand_graph_pair(rng))

    add("Count Connected Components", "Graphs", "MEDIUM",
        "Given an undirected graph with n nodes and a list of edges, return "
        "the number of connected components.",
        "1 <= n <= 15.",
        2, sol_graph_connected_components,
        lambda rng: _rand_graph(rng)[:2])

    add("Shortest Path Length (Unweighted)", "Graphs", "MEDIUM",
        "Given an undirected, unweighted graph with n nodes and a list of "
        "edges, return the length of the shortest path between two nodes, or "
        "-1 if unreachable.",
        "1 <= n <= 15.",
        4, sol_graph_shortest_path_len,
        lambda rng: _rand_graph_pair(rng))

    # ---------------- Dynamic Programming ----------------
    add("Staircase Step Combinations", "Dynamic Programming", "EASY",
        "You are climbing a staircase with n steps, taking either 1 or 2 "
        "steps at a time. Return how many distinct ways there are to reach "
        "the top.",
        "1 <= n <= 40.",
        1, sol_climb_stairs,
        lambda rng: (rng.randint(1, 30),))

    add("Fewest Coins For Amount", "Dynamic Programming", "MEDIUM",
        "Given a list of coin denominations and a target amount, return the "
        "minimum number of coins needed to make that amount, or -1 if it "
        "cannot be made.",
        "1 <= amount <= 100.",
        2, sol_coin_change,
        lambda rng: (sorted(set(rng.sample(range(1, 15), rng.randint(2, 5)))), rng.randint(0, 40)))

    add("Longest Increasing Subsequence Length", "Dynamic Programming", "MEDIUM",
        "Given an array of integers, return the length of the longest "
        "strictly increasing subsequence.",
        "1 <= n <= 20.",
        1, sol_lis_length,
        lambda rng: (rand_list(rng, 1, 15, 0, 30),))

    add("0/1 Knapsack Maximum Value", "Dynamic Programming", "HARD",
        "Given item weights, item values, and a knapsack capacity, return the "
        "maximum total value obtainable without exceeding the capacity, "
        "using each item at most once.",
        "1 <= n <= 15, capacity <= 50.",
        3, sol_knapsack01,
        lambda rng: _rand_knapsack(rng))

    add("Minimum Edit Distance", "Dynamic Programming", "HARD",
        "Given two strings, return the minimum number of single-character "
        "insertions, deletions, or substitutions to transform the first into "
        "the second.",
        "0 <= |a|, |b| <= 15.",
        2, sol_edit_distance,
        lambda rng: (rand_string(rng, 0, 8, "abc"), rand_string(rng, 0, 8, "abc")))

    # ---------------- Greedy ----------------
    add("Maximum Non-Overlapping Activities", "Greedy", "MEDIUM",
        "Given a list of [start, end] activity intervals, return the maximum "
        "number of activities that can be scheduled without overlap.",
        "1 <= n <= 15.",
        1, sol_activity_selection,
        lambda rng: (_rand_intervals(rng),))

    add("Greedy Coin Count", "Greedy", "EASY",
        "Given a set of coin denominations and an amount, return the number "
        "of coins used when always picking the largest denomination first, "
        "or -1 if the amount can't be made exactly this way.",
        "1 <= amount <= 200.",
        2, sol_min_coins_greedy,
        lambda rng: ([1, 2, 5, 10], rng.randint(0, 100)))

    # ---------------- Math ----------------
    add("Greatest Common Divisor", "Math", "EASY",
        "Given two positive integers, return their greatest common divisor.",
        "1 <= a, b <= 10^6.",
        2, sol_gcd,
        lambda rng: (rng.randint(1, 500), rng.randint(1, 500)))

    add("Prime Number Check", "Math", "EASY",
        "Given an integer n, return true if it is a prime number.",
        "0 <= n <= 10^5.",
        1, sol_is_prime,
        lambda rng: (rng.randint(0, 200),))

    add("Modular Exponentiation", "Math", "MEDIUM",
        "Given base, exponent, and modulus, return base^exponent mod modulus "
        "efficiently.",
        "0 <= exponent <= 10^5, 1 <= modulus <= 10^9.",
        3, sol_power_mod,
        lambda rng: (rng.randint(0, 50), rng.randint(0, 50), rng.randint(1, 1000)))

    add("Count Set Bits", "Math", "EASY",
        "Given a non-negative integer, return the number of 1 bits in its "
        "binary representation.",
        "0 <= n <= 10^9.",
        1, sol_count_set_bits,
        lambda rng: (rng.randint(0, 100000),))

    # ---------------- Bit Manipulation ----------------
    add("Single Non-Duplicate Number", "Bit Manipulation", "EASY",
        "Given an array where every element appears exactly twice except for "
        "one, return that single element.",
        "1 <= n <= 21 (odd length), values fit in 32-bit range.",
        1, sol_single_number,
        lambda rng: _rand_single_number_case(rng))

    # ---------------- Backtracking ----------------
    add("All Subsets Of A Set", "Backtracking", "MEDIUM",
        "Given an array of distinct integers, return all possible subsets "
        "(the power set), sorted for determinism.",
        "0 <= n <= 8.",
        1, sol_subsets,
        lambda rng: (sorted(rng.sample(range(-10, 10), rng.randint(0, 5))),))

    add("Count Total Permutations", "Backtracking", "EASY",
        "Given an array of n distinct elements, return the total number of "
        "distinct permutations possible.",
        "0 <= n <= 8.",
        1, sol_permutations_count,
        lambda rng: (list(range(rng.randint(0, 6))),))

    # ---------------- Sorting & Searching ----------------
    add("Binary Search In Sorted Array", "Sorting & Searching", "EASY",
        "Given a sorted array of distinct integers and a target, return the "
        "index of the target, or -1 if not present.",
        "0 <= n <= 30.",
        2, sol_binary_search,
        lambda rng: _rand_sorted_search_case(rng))

    add("Sort An Integer Array", "Sorting & Searching", "EASY",
        "Given an array of integers, return it sorted in non-decreasing "
        "order.",
        "0 <= n <= 30.",
        1, sol_merge_sort,
        lambda rng: (rand_list(rng, 0, 20),))

    return bank


def _rand_tree_array(rng, max_nodes=20):
    n = rng.randint(0, max_nodes)
    if n == 0:
        return []
    arr = []
    for _ in range(n):
        arr.append(rng.randint(-20, 20) if rng.random() > 0.15 else None)
    if arr[0] is None:
        arr[0] = rng.randint(-20, 20)
    return arr

def _rand_graph(rng):
    n = rng.randint(2, 10)
    edges = set()
    max_edges = rng.randint(0, n * 2)
    for _ in range(max_edges):
        a, b = rng.randint(0, n - 1), rng.randint(0, n - 1)
        if a != b:
            edges.add((min(a, b), max(a, b)))
    start = rng.randint(0, n - 1)
    return (n, sorted(edges), start)

def _rand_graph_pair(rng):
    n, edges, _ = _rand_graph(rng)
    src, dst = rng.randint(0, n - 1), rng.randint(0, n - 1)
    return (n, edges, src, dst)

def _rand_knapsack(rng):
    n = rng.randint(1, 8)
    weights = [rng.randint(1, 10) for _ in range(n)]
    values = [rng.randint(1, 20) for _ in range(n)]
    cap = rng.randint(1, 30)
    return (weights, values, cap)

def _rand_intervals(rng):
    n = rng.randint(1, 10)
    out = []
    for _ in range(n):
        s = rng.randint(0, 20)
        e = s + rng.randint(1, 8)
        out.append([s, e])
    return out

def _rand_single_number_case(rng):
    n_pairs = rng.randint(0, 8)
    vals = []
    for _ in range(n_pairs):
        v = rng.randint(-30, 30)
        vals.extend([v, v])
    unique = rng.randint(-30, 30)
    vals.append(unique)
    rng.shuffle(vals)
    return (vals,)

def _rand_sorted_search_case(rng):
    n = rng.randint(0, 15)
    arr = sorted(rng.sample(range(-30, 30), n))
    target = rng.choice(arr) if arr and rng.random() > 0.3 else rng.randint(-35, 35)
    return (arr, target)
