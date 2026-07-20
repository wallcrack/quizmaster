<!--
============================================================
QuizMaster 题目导入示例 — Markdown 格式

格式说明:
  - 每道题以 YAML frontmatter (---...---) 开头
  - frontmatter 中填写题目元数据（type, difficulty, tags 等）
  - frontmatter 后面是题干内容（支持 Markdown / LaTeX）
  - 多道题之间用 --- 分隔

用法: 在题目管理页面上传此 .md 文件即可批量导入
============================================================
-->

---
type: single
difficulty: easy
chapter: 第1章 计算机基础
source: 计算机科学导论
tags: [计算机基础, 硬件, 图片题]
image: cpu_architecture.png
options:
  - 运算器、控制器、存储器
  - 运算器、控制器、输入设备
  - 控制器、存储器、输出设备
  - 运算器、输入设备、输出设备
answer: "0"
explanation: |
  冯·诺依曼架构由五大部分组成：运算器、控制器、存储器、输入设备和输出设备。
  其中运算器、控制器、存储器构成核心三大部件。
---

如图所示，冯·诺依曼计算机体系结构的三大核心部件是什么？

---
type: multiple
difficulty: medium
chapter: 第4章 CSS 布局
source: 前端开发进阶
tags: [CSS, 前端, 布局]
options:
  - Flexbox
  - Float
  - Grid
  - Table 布局
answer: "0,2"
explanation: |
  Flexbox 和 Grid 是现代 CSS 布局的核心技术：
  - **Flexbox**：一维布局，适合行或列方向的排列
  - **Grid**：二维布局，同时控制行和列

  Float 和 Table 布局是传统方式，不推荐在现代项目中使用。
---

以下哪些是现代 CSS 推荐的布局方式？（多选）

---
type: true_false
difficulty: easy
chapter: 第3章 数据结构
source: 算法与数据结构
tags: [算法, 复杂度]
answer: "false"
explanation: |
  二分查找的时间复杂度是 $O(\log n)$，不是 $O(n)$。
  $O(n)$ 是线性查找（顺序查找）的时间复杂度。
---

二分查找（Binary Search）的平均时间复杂度是 $O(n)$。

---
type: subjective
difficulty: hard
chapter: 第2章 算法设计
source: 算法导论
tags: [算法, 动态规划, LaTeX]
---

请解释动态规划的两个核心要素：**最优子结构** 和 **重叠子问题**。

并用以下公式说明动态规划的递推关系：

$$dp[i] = \max(dp[i-1], dp[i-2] + value[i])$$

---
type: single
difficulty: medium
chapter: 第7章 安全基础
source: 网络安全入门
tags: [安全, HTTPS, 图片题]
image: https_flow.png
options:
  - 使用公钥加密数据，使用私钥验证身份
  - 使用公钥验证身份，使用私钥加密数据
  - 公钥和私钥都用于加密
  - 公钥和私钥都用于验证
answer: "0"
explanation: |
  在 HTTPS（TLS/SSL）中：
  - **公钥**：用于加密数据（任何人都可以获取）
  - **私钥**：用于解密数据（仅服务器持有）

  非对称加密确保只有持有私钥的服务器能解密客户端发送的数据。
---

观察下面的 HTTPS 通信流程图，公钥和私钥分别起什么作用？

---
type: multiple
difficulty: medium
chapter: 第10章 部署与运维
source: Docker 实战
tags: [Docker, 容器, DevOps]
options:
  - 容器共享宿主机内核
  - 容器拥有独立的操作系统
  - 容器启动速度快
  - 容器镜像可以分层构建
answer: "0,2,3"
explanation: |
  Docker 容器的特点：
  - 共享宿主机内核（与虚拟机的主要区别）
  - 启动速度快（秒级甚至毫秒级）
  - 分层构建镜像（利于复用和分发）

  容器**不拥有**独立的操作系统，它共享宿主机的 OS 内核。
---

以下关于 Docker 容器的描述，哪些是正确的？（多选）
