---
title: "Leetcode刷题总结"
date: 2026-08-19
tags: ["leetcode"]
categories: ["数据结构","算法"]
draft: true
---
# 考察的算法模式

[8种重要模式](https://www.bilibili.com/video/BV1Hegc6NEsW/)

| Topic                | Difficulty | Return On Investment |
| -------------------- | ---------- | -------------------- |
| Two Pointers         | Easy       | High                 |
| Sliding Window       | Easy       | High                 |
| Breadth-First Search | Easy       | High                 |
| Depth-First Search   | Medium     | High                 |
| Backtracking         | High       | High                 |
| Heap                 | Medium     | Medium               |
| Binary Search        | Easy       | Medium               |
| Dynamic Programming  | High       | Medium               |
| Divide and Conquer   | Medium     | Low                  |
| Trie                 | Medium     | Low                  |
| Union Find           | Medium     | Low                  |
| Greedy               | High       | Low                  |

涉及的数据结构：
- 线性（Linear）：数组、链表、字符串
- 非线性（Non-Linear）：树、图

## 1. 双指针（Two Pointers）
**适用于线性结构处理**
### 指针同向移动

适合单趟处理或扫描数据

快慢指针法：检测链表种的环或中间节点（慢指针每次移动一步，快指针每次移动两步及以上）

### 指针反向移动
适用于寻找配对或从数据结构两端匹配元素

## 2. 滑动窗口（Sliding Window）
**是双指针的扩展，适合需要追踪==连续序列==的问题**
维护并动态调整窗口大小，以控制窗口中的元素数量。用于管理范围或是满足特定条件的元素子集（比如子数组或子串）
一个指针代表起点，一个指针代表结尾（二者都可移动）

## 3. 二分查找（Binary Search）
**也是双指针的扩展，适用于==排序==的列表，快速查找定位特定值**
扩展：如果列表是按True/False排序，也可用二分查找

## 4. 广度优先查找（Breadth-First-Search，BFS）
**适用于非线性结构（树和图），适合找最短路径或是逐层探索**
可以将**树**看作是**不带环的图**
## 5. 回溯（Backtracking）

## 6. 动态规划（Dynamic Programming，DP）

## 7. 深度优先查找（Depth-First-Search，DFS）
**适合探索所有路径的问题，比如找到树中的所有路径、检测环**
相比BFS更节省内存
## 8. 优先队列（Priority Queue）

