# 供应商注册进度追踪系统 / Supplier Registration Progress Tracker

专业、干净的内部工具，用于追踪国外供应商的注册进度（供应商注册进度追踪系统）。

**完全本地化 | Fully Local-First**  
- SQLite 数据库 + 附件均在 `data/` 文件夹（可放在共享盘 / OneDrive 供团队使用）
- 无需任何外部服务

## 功能亮点 / Key Features (完全匹配需求)

- 📊 **仪表盘**：KPI 卡片（Total / In Progress / Completed / Delayed + 逾期）、状态分布饼图、平台 breakdown、最近活动
- 📋 **供应商列表**：公司（中+英）、国家、平台、状态（彩色徽章）、截止日期（逾期红标）、负责人(Owner)、最后更新；支持搜索 + Status/Platform/Country 多选过滤；可排序；Excel 导出（尊重当前筛选）
- ➕ **添加/编辑**：完整表单（国家、平台、截止日期、内部负责人、联系人、备注等）
- 📋 **详情视图（核心）**：
  - 可视化状态步骤器（Not Started → In Progress → Documents Submitted → Under Review → Approved / Rejected / On Hold），可点击推进
  - 文件上传区（多文件 + 拖拽支持），文件列表带「上传人」、下载、删除
  - 团队评论区（固定操作人 “Stella - 注册” 署名发帖）
  - 统一活动记录（状态变更 + 评论合并时间线）
- 👥 **固定操作人**：所有评论、文件上传、状态记录、默认负责人均使用固定值 “Stella - 注册”。侧边栏已移除选择器，界面更干净。
- 📤 **Excel 导出**：专业格式（带颜色、筛选后数据）
- 🌱 **演示数据**：已**彻底关闭**自动生成。启动时为完全干净状态（无任何示例数据）。你可以通过界面手动添加真实供应商。
- 🇨🇳 **中英双语**：默认中文，随时切换

## 技术栈 / Tech Stack

- Streamlit (最新稳定版)
- SQLite (stdlib sqlite3)
- pandas + openpyxl (Excel 导出)
- plotly (仪表盘专业图表)

## 快速开始 / Quick Start (Windows PowerShell 推荐)

1. 进入目录
   ```powershell
   cd supplier-tracker-streamlit
   ```

2. 创建虚拟环境并安装依赖
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   ```

3. 运行
   ```powershell
   streamlit run app.py
   ```

   浏览器会自动打开 http://localhost:8501

**首次运行自动完成**：
- 创建 `data/suppliers.db`
- 创建 `data/uploads/`
- **不会**插入任何示例数据（完全干净状态）

你现在可以直接手动添加真实的供应商数据。

**日常使用流程**（强烈推荐）：
1. 操作人固定为 “Stella - 注册” —— 所有评论、上传、状态记录、默认负责人均自动使用此人。
2. 查看「仪表盘」了解整体进度。
3. 去「供应商列表」，用搜索 + 国家/平台/状态过滤，点击表格行。
4. 点击「查看详情」打开完整注册视图：
   - 用步骤器点击推进状态（会自动记录历史，带操作人）。
   - 拖拽或选择文件上传（会记录上传人）。
   - 在团队评论区发帖（作者自动署名为 “Stella - 注册”）。
   - 下方统一活动记录同时看到状态变更和评论。
5. 任何时候用「导出当前结果 (Excel)」备份筛选后的数据。

**清空所有数据**：左侧边栏「数据管理」区域点击「🗑️ 清空所有数据」→ 二次确认即可（会删除所有记录 + 所有上传文件，保留数据库表结构）。适合在正式使用前回到干净状态。

**停止**：终端里按 `Ctrl + C`。

## 数据位置与备份 / Data Location & Backup

- 数据库：`data/suppliers.db`
- 附件文件：`data/uploads/<supplier_id>/...`（真实文件，可直接打开）
- **备份**：直接复制整个 `data/` 文件夹即可（可放在公司共享盘或 OneDrive 供全团队使用）。

**团队共享推荐做法**：
- 把整个 `supplier-tracker-streamlit` 文件夹（或仅 `data/` 子文件夹）放在内部共享位置。
- 每个人在自己机器上 `streamlit run app.py`（或用同一个 Python 环境）。
- 操作人固定为 “Stella - 注册”，模拟统一的内部操作记录。
- 所有数据实时共享（SQLite + 文件）。

## 主要页面与协作流程 / Pages & Collaboration Flow

1. **仪表盘**：KPI（Total / In Progress / Completed / Delayed）、状态饼图、平台分布、最近活动。
2. **供应商列表**：搜索 + 多维过滤（含国家）、表格（公司+国家+平台+状态+截止+负责人）、行选中后「查看详情」是主入口。
3. **详情视图（最重要）**：
   - 可视化步骤器（可点击推进 7 种状态）
   - 文件区（多文件 + 拖拽 + 上传人显示）
   - 团队评论（固定 “Stella - 注册” 署名）
   - 统一活动时间线（状态变更 + 评论）
4. **添加供应商**：标准表单（负责人默认 “Stella - 注册”）。

**固定操作人**：所有评论、附件、状态变更、默认负责人均使用 “Stella - 注册”。

## 自定义 / Customization

- 固定操作人：`utils/constants.py` 的 `FIXED_ACTOR`（当前为 "Stella - 注册"）
- 状态 / 平台 / 国家：同文件对应常量
- 翻译：`utils/i18n.py`
- 样式：`ui/components.py` 的 inject_global_css（stepper、评论气泡等）
- 主题（可选）：在项目根建 `.streamlit/config.toml`

## 生产使用建议 / Production Tips

- 可将 `data/` 放在共享网络盘或定期备份。
- 多人使用建议部署到内部服务器（Streamlit 支持）。
- 大量数据后可考虑将过滤下推到 SQL（当前客户端 pandas 过滤对数百条已足够快）。

## 常见问题 / Troubleshooting

- **想回到完全干净状态**：使用左侧边栏的「🗑️ 清空所有数据」按钮（推荐），或直接删除 `data/suppliers.db` + `data/uploads/` 文件夹后重启应用。
- **中文显示**：Windows Streamlit 通常正常；如乱码可尝试系统安装更多 CJK 字体。
- **端口冲突**：`streamlit run app.py --server.port 8502`
- **想完全重置**：删除整个 `data/` 文件夹后重启（会重新创建 + 播种）。
- **团队使用**：把 `data/` 放在共享位置即可实时同步。

## 许可证 / License

内部工具专用（公司内部使用）。

---

**开发维护**：使用本计划中定义的清晰分层结构，便于长期维护。

Enjoy tracking your supplier registrations! / 祝注册追踪工作顺利！

---

## 部署到 Streamlit Community Cloud

本项目可以部署到 **Streamlit Community Cloud**（免费），但有重要限制需要了解。

### 重要限制（必须阅读）

- **数据持久性**：Streamlit Community Cloud 使用临时文件系统。每次应用重启、休眠或重新部署时，`data/` 目录（包括 `suppliers.db` 和所有上传的文件）都会被**清空**。
- **文件上传**：`st.file_uploader` 本身可以工作（会话期间可上传和下载），但文件只保存在当前容器的临时磁盘上，重启后消失。
- **适合场景**：演示、内部小团队试用、原型验证。
- **生产/重要数据建议**：
  - 频繁使用侧边栏的 **「📤 导出全部 (Excel)」** 进行备份。
  - 考虑部署到支持持久化磁盘的平台（Railway、Render、Fly.io、AWS、内部服务器等）。
  - 或者将数据库迁移到 PostgreSQL（Neon / Supabase 免费层）+ 对象存储。

### 部署步骤

1. **准备仓库**
   ```bash
   # 推荐：将整个 supplier-tracker-streamlit 文件夹作为独立仓库根目录推送
   # 或者保持当前结构，使用子路径部署
   git init
   git add .
   git commit -m "Prepare for Streamlit Community Cloud"
   git remote add origin https://github.com/你的用户名/supplier-tracker-streamlit.git
   git push -u origin main
   ```

2. **部署到 Streamlit Cloud**
   - 访问 https://share.streamlit.io
   - 点击 **New app**
   - 连接你的 GitHub 账号并选择仓库
   - **Main file path** 填写：
     - 如果仓库根目录就是 `supplier-tracker-streamlit` 的内容：`app.py`
     - 如果仓库根目录包含 `supplier-tracker-streamlit` 文件夹：`supplier-tracker-streamlit/app.py`
   - 点击 **Deploy**

3. **首次运行**
   - 应用会自动创建 `data/` 目录（在容器内）。
   - 因为我们已经关闭了自动 seed，启动后是完全干净状态。
   - 你可以立即手动添加供应商测试。

4. **推荐的 .streamlit/config.toml**
   - 项目中已包含（见 `.streamlit/config.toml`），包含了适合云端的 `headless` 设置和专业主题。

5. **Secrets（可选）**
   - 目前不需要 `st.secrets`（使用本地 SQLite）。
   - 如果未来迁移到 Postgres，可在 Streamlit Cloud 的 **Secrets** 面板配置数据库连接字符串。

### 让云端体验更好的一些技巧

- 在侧边栏底部已添加数据位置提示。
- 建议在团队内部文档中强调“定期导出备份”。
- 如果想在云端也保留少量演示数据，可以手动添加几条后导出，再在需要时重新导入。

### 更可靠的部署选项（推荐用于真实使用）

- **Railway / Render / Fly.io**：支持持久化磁盘卷 + 免费额度，`data/` 可以持久保留。
- **Docker**：本地或自建服务器使用 Docker 卷挂载 `data/`。
- **Supabase + Streamlit**：把 SQLite 换成 Supabase Postgres + Storage（文件直接存对象存储）。

部署后有问题欢迎反馈！
