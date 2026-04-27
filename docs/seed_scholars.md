# 榜单种子候选名单

用于批量创建初始 profile。每个方向按 **资深 / 中坚 / 新锐** 三档分组（新锐 = 首篇论文 < 10 年）。
导入时通过 `/api/scholar-search?q=<name>` 定位 Semantic Scholar ID，再调 `/api/profile` 创建。

---

## A. LLM / NLP （约 30 人）

### 国际 · 资深
- Christopher Manning — Stanford
- Yoshua Bengio — Mila / Université de Montréal
- Dan Jurafsky — Stanford
- Jason Weston — Meta FAIR
- Noah A. Smith — UW / Allen AI
- Luke Zettlemoyer — UW / Meta

### 国际 · 中坚
- Percy Liang — Stanford
- Tatsunori Hashimoto — Stanford
- Jacob Devlin — Google (BERT)
- Colin Raffel — UNC / HF (T5)
- Sebastian Ruder — Google / Cohere
- Douwe Kiela — Contextual AI
- Tim Dettmers — CMU / Allen AI
- Sasha Rush — Cornell

### 国际 · 新锐 / 前沿
- Tri Dao — Princeton (FlashAttention)
- Jared Kaplan — Anthropic (Scaling Laws)
- Aleksander Madry — MIT / OpenAI
- Jiayi Pan — Berkeley
- Percy Liang — Stanford (重复，可删)

### 中文社区
- 刘知远 Zhiyuan Liu — 清华
- 孙茂松 Maosong Sun — 清华
- 黄民烈 Minlie Huang — 清华
- 邱锡鹏 Xipeng Qiu — 复旦
- 车万翔 Wanxiang Che — 哈工大
- 张岳 Yue Zhang — 西湖大学
- 周明 Ming Zhou — 澜舟 / 前 MSRA
- Weizhu Chen — Microsoft (DeepSpeed)
- 赵鑫 Xin Zhao — 人大
- 林衍凯 Yankai Lin — 人大 / 智谱
- 冯岩松 Yansong Feng — 北大
- 万小军 Xiaojun Wan — 北大

---

## B. Computer Vision （约 25 人）

### 国际 · 资深
- Jitendra Malik — Berkeley
- Trevor Darrell — Berkeley
- Andrew Zisserman — Oxford
- Jean Ponce — NYU / INRIA
- Alexei Efros — Berkeley
- Cordelia Schmid — INRIA / Google

### 国际 · 中坚
- Kaiming He — MIT / FAIR (ResNet, MAE)
- Ross Girshick — FAIR
- Ali Farhadi — UW / AI2 (YOLO)
- Piotr Dollár — FAIR
- Phillip Isola — MIT
- Jia Deng — Princeton
- Saining Xie — NYU

### 国际 · 新锐
- Mathilde Caron — Google DeepMind (DINO)
- Maxime Oquab — FAIR (DINOv2)
- Bowen Cheng — FAIR (Mask2Former)
- Xinlei Chen — FAIR

### 中文社区
- 李飞飞 Fei-Fei Li — Stanford
- 贾扬清 Yangqing Jia — LeptonAI / 前阿里
- 任少卿 Shaoqing Ren — Momenta (Faster R-CNN)
- 王兴刚 Xinggang Wang — 华科
- 乔宇 Yu Qiao — Shanghai AI Lab
- 林达华 Dahua Lin — CUHK
- 王井东 Jingdong Wang — 百度 / 前 MSRA
- 代季峰 Jifeng Dai — 清华 / 前商汤

---

## C. VLM / Multimodal / Generative （约 20 人）

### 国际
- Alec Radford — OpenAI (CLIP, GPT)
- Aditya Ramesh — OpenAI (DALL-E)
- Ludwig Schmidt — Anthropic / AI2 (OpenCLIP)
- Björn Ommer — LMU (Stable Diffusion)
- Robin Rombach — Black Forest Labs (Stable Diffusion)
- William (Bill) Peebles — OpenAI (DiT, Sora)
- Saining Xie — NYU (DiT co-author)
- Jiasen Lu — Google / UW
- Jianwei Yang — Microsoft
- Chunyuan Li — ByteDance / 前 Microsoft

### 中文社区
- 张祥雨 Xiangyu Zhang — MEGVII / StepFun
- 周博磊 Bolei Zhou — UCLA
- 朱军 Jun Zhu — 清华
- 鲁继文 Jiwen Lu — 清华
- 刘壮 Zhuang Liu — Meta FAIR / Princeton (ConvNeXt)
- 陈海波 Haibo Chen — 上交 (less VLM, more systems — 可能归 Systems)

---

## D. ML Theory / Systems （约 15 人，可选）

### ML Systems
- Jeff Dean — Google
- Tianqi Chen 陈天奇 — CMU (TVM, MLC)
- Matei Zaharia — Databricks / Stanford (Spark)
- Ion Stoica — Berkeley (Ray)
- Hao Zhang — UCSD (vLLM)
- Zhuohan Li — Berkeley (vLLM)

### ML Theory
- Sanjeev Arora — Princeton
- Tengyu Ma — Stanford
- Jason D. Lee — Princeton
- Peter Bartlett — Berkeley

### RL
- Pieter Abbeel — Berkeley
- Sergey Levine — Berkeley
- Chelsea Finn — Stanford
- 吴翼 Yi Wu — 清华

---

## 规模建议

起步 **~80–100 人**（上面已经够）：
- LLM/NLP ≈ 30
- CV ≈ 25
- VLM/Generative ≈ 20
- Theory/Systems/RL ≈ 15（可选）

覆盖国际 ≈ 60%，中文社区 ≈ 40%，能给"中文圈学者的影响力地图"这个产品定位一个好的起点。

---

## 下一步（实现层）

1. 把本文件整理成 `docs/seed_scholars.json`（结构化，带 `name` / `direction` / `tier`）
2. 写 `backend/scripts/seed_scholars.py`：
   - 读 JSON → 对每人调 `scholar-search` 拿 authorId
   - 调 `POST /api/profile` 自动 discover
   - 等待首轮 refresh 完成
3. 榜单计算：先加一张 `leaderboard_entries` 表缓存排名快照；每 6 小时重算
4. 前端 `/leaderboard` 页面：tabs 切换维度，前 10000 名显示排名，之后显示 `P90` / `P75` 分位
