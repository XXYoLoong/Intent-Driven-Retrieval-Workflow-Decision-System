# Vault 项目接入与 yoloong_develop 分支指南

本文说明如何在项目经理的 Gitee 仓库 [Vault](https://gitee.com/hold-ryue-in-hand/Vault) 上创建 `yoloong_develop` 分支，并接入本系统（Intent-Driven Retrieval & Workflow Decision System），在其前端上设置可视化问答界面（高级智脑问答助手）。

---

## 一、前置条件

- 本系统已全部推送到：<https://github.com/XXYoLoong/Intent-Driven-Retrieval-Workflow-Decision-System.git>
- 项目经理仓库：<https://gitee.com/hold-ryue-in-hand/Vault>
- 本地当前在**本系统**的 `main` 分支，尚未连接 Vault 仓库

---

## 二、克隆 Vault 并创建 yoloong_develop 分支

在**新的工作目录**下操作（不要在本系统项目根目录里直接加 remote 混用，避免冲突）：

### 1. 克隆 Vault（Gitee）

```bash
# 选一个目录，例如与当前项目同级
cd F:\
git clone https://gitee.com/hold-ryue-in-hand/Vault.git Vault-repo
cd Vault-repo
```

### 2. 创建并推送 yoloong_develop 分支

```bash
# 基于默认分支（一般为 main 或 master）创建你的开发分支
git checkout -b yoloong_develop

# 推送到 Gitee，并设置上游
git push -u gitee yoloong_develop
```

若 Gitee 远程名为 `origin`，则：

```bash
git push -u origin yoloong_develop
```

### 3. 确认分支

在 Gitee 页面上打开 Vault 仓库，应能看到 `yoloong_develop` 分支。

---

## 三、接入本系统（两种常见方式）

### 方式 A：本系统作为独立后端服务（推荐）

- **思路**：本系统保持独立仓库与进程，只提供 API；Vault 前端通过 HTTP 调用。
- **优点**：职责清晰、部署灵活、不污染 Vault 仓库代码结构。
- **步骤**：
  1. 在本系统项目里正常启动后端：`python run.py`（例如 `http://localhost:8000`）。
  2. 在 Vault 前端项目中配置「智脑问答」的 API Base URL 指向 `http://localhost:8000`（或部署后的域名）。
  3. 在 Vault 前端新增「高级智脑问答」页面/模块，调用：
     - `POST /v1/chat` 或 `POST /v1/chat/stream`（流式）
     - 可选：`GET /v1/workflows/runs/{run_id}` 等（若需展示工作流运行状态）。
  4. 若 Vault 与后端不同端口/域名，需在本系统或 Vault 侧配置 CORS（本系统 `main.py` 已允许 `allow_origins=["*"]`，一般可直接用）。

### 方式 B：将本系统作为 Vault 的子目录或子模块

- **思路**：在 Vault 的 `yoloong_develop` 分支里，把本系统作为子目录或 git submodule 放入（例如 `Vault-repo/intent_system/`），由 Vault 统一启动或统一部署。
- **步骤**（子目录方式示例）：
  1. 在 Vault 仓库根目录下新建目录，如 `intent_system`。
  2. 将本系统除 `.git` 外的内容复制进去，或在 Vault 内 `git subtree add` / 直接复制。
  3. 在 Vault 的 README 或部署文档中说明：智脑问答依赖 `intent_system`，需先 `cd intent_system && pip install -r requirements.txt && python run.py`。
  4. 前端同上，配置 API Base URL 指向本系统服务地址。

**建议**：优先用**方式 A**，后端独立运行，Vault 只做前端与业务集成；若项目经理明确要求代码合在一个仓库，再用方式 B。

---

## 四、在 Vault 前端设置「高级智脑问答」界面

在 **Vault 项目**的 `yoloong_develop` 分支中：

1. **确定前端技术栈**  
   打开 Vault 前端代码（如 `web/`、`frontend/`、`src/` 等），确认是 Vue / React / 其他。

2. **新增问答页面/入口**  
   - 新增路由，例如：`/brain-qa` 或 `/intent-qa`。  
   - 页面标题可命名为「高级智脑问答」或「智脑助手」。

3. **调用本系统 API**  
   - **同步回答**：`POST /v1/chat`，Body 示例：
     ```json
     {
       "message": "用户输入的问题",
       "context": { "tenant_id": "default" },
       "options": { "output_format": "steps" }
     }
     ```
   - **流式回答**（推荐）：`POST /v1/chat/stream`，使用 SSE 或 fetch 流式读取，解析 `event: delta_answer` / `event: final` 等，见 [使用说明 - 流式聊天接口](03_使用说明.md#2-流式聊天接口)。

4. **环境配置**  
   在 Vault 前端增加环境变量或配置项，例如：
   - `VITE_INTENT_API_BASE=http://localhost:8000`（Vite）
   - 或 `REACT_APP_INTENT_API_BASE=...`（Create React App）  
   请求时拼成：`${API_BASE}/v1/chat` / `${API_BASE}/v1/chat/stream`。

5. **界面元素建议**  
   - 输入框 + 发送按钮。  
   - 回答展示区（支持 Markdown 渲染，因本系统返回 steps 等格式）。  
   - 可选：引用来源（本系统 `meta.citations`）、加载中/流式打字效果。

---

## 五、你本地当前仓库不要直接添加 Vault 的 remote

你当前在「Intent-Driven Retrieval & Workflow Decision System」的 `main` 分支，且已全部推送到 GitHub，**不要**在该项目里执行：

```bash
git remote add gitee https://gitee.com/hold-ryue-in-hand/Vault.git
```

否则会把两个不同项目混在一起，容易误 push 或误合并。  
正确做法：**单独克隆 Vault 到新目录**，在新目录里创建 `yoloong_develop` 并做接入与前端开发。

---

## 六、操作清单小结

| 步骤 | 位置 | 操作 |
|------|------|------|
| 1 | 新目录 | `git clone https://gitee.com/hold-ryue-in-hand/Vault.git Vault-repo` |
| 2 | Vault-repo | `git checkout -b yoloong_develop` → `git push -u origin yoloong_develop` |
| 3 | 本系统项目 | 保持独立，`python run.py` 启动后端（或按部署方式启动） |
| 4 | Vault-repo 前端 | 配置智脑 API Base URL，新增问答页，调用 `/v1/chat` 或 `/v1/chat/stream` |
| 5 | 文档 | 在 Vault 的 README 或内部文档中说明：智脑能力由 Intent-Driven 系统提供，接口见 doc/03_使用说明.md |

---

## 七、后续可补充

- 若 Vault 仓库结构（前端目录、框架）确定，可在本文补充「在 Vault 中具体在哪个文件加路由、哪个文件发请求」的示例。
- 若采用方式 B（子目录/子模块），可补充在 Vault 内的具体路径与启动顺序。
