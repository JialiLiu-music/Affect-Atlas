# 音乐情绪实验室前端

React 19 + TypeScript + TanStack Start + shadcn/ui 的中文科研演示界面。所有预测均来自 FastAPI；缺少真实模型资产时禁用上传，绝不生成随机值、示例分数或模拟截图。

## 独立运行

要求 Node.js >= 22.12，使用 npm。工作目录为 `E:\project\test\ljl\lunwen2\code\frontend`。

```powershell
npm install
npm run dev
```

浏览器打开 `http://localhost:5173`。端口固定且 `strictPort: true`，被占用时退出而非切换端口。前端自身无需模型、GPU、外部图片或模型下载。默认连接 `http://127.0.0.1:8000`。

自定义后端：把 `apps/web/.env.example` 复制为 `apps/web/.env.local`，设置 `VITE_API_BASE_URL`，然后重启开发服务。可选 `VITE_API_AUTH_TOKEN` 用于后端启用 `MER_API_TOKEN` 时的上传和任务查询：POST /api/jobs 与 GET /api/jobs/{id} 都发送 `Authorization: Bearer ...`。健康检查不发送 Bearer。VITE 环境变量会进入浏览器，不能作为服务端私密凭据；只适用于受信任本地演示，不要填写其他服务的 secret。

FastAPI 需要允许源 `http://localhost:5173` 的跨域请求，允许 POST multipart、GET 和 `Authorization` / `X-Job-Token` 请求头。生产静态/SSR 构建可运行 `npm run build`，产物分别在 `apps/web/dist/client` 与 `apps/web/dist/server`。本任务不包含云部署。

## 真实接口与交互

- 每 5 秒检查 GET /api/health；请求超时 15 秒，明确显示后端原始错误、模型不可用原因、资产缺失与队列状态。`loaded: false` 不单独禁上传：后端可以在首个任务懒加载，是否可提交以 `status: ready` 与 `assets_available` 为准。
- 接受 WAV / MP3 / FLAC / OGG；M4A 必须先转换，不宣传后端未支持的格式。浏览器 `accept` 只是提示，解码与最终格式判定仍由后端执行。前端检查空文件、大小和 M4A 扩展名，默认限制 20 MiB、1–90 秒（最终时长检查由后端执行）。
- POST /api/jobs 使用 multipart 字段 `file`，GET /api/jobs/{id} 使用 `X-Job-Token`。访问令牌只保存在当前组件内存中，不写 localStorage、URL 或日志；刷新页面不会恢复任务。
- 每 2 秒查询任务状态，最多 20 分钟（计时从任务创建成功开始）；单次查询 15 秒超时。网络失败暂停并允许恢复查询，无需重新上传；暂停时间仍计入 20 分钟总上限。组件卸载、完成和新任务会 abort 请求并清除计时器。停止前端查询不会取消后端任务。
- 上传和处理中禁止重复提交及更换文件。选择新文件或移除当前文件时清除上一任务结果，避免将旧结果显示为新音乐的输出。
- 本地音频预览使用 object URL，在切换文件/卸载时 revoke。没有外部音频服务。
- 二维图横轴 valence（愉悦度）、纵轴 arousal（唤醒度），刻度为 -1、-0.5、0、0.5、1。圆点仅在真实任务完成后出现。
- 原始 valence/arousal 的阅读数值统一显示四位小数，悬停 title 与 JSON/CSV 保留完整精度；四舍五入不作为中性类别判断。整体二维图仅使用 display 字段裁剪到 [-1,1]；窗口曲线使用原始值，超范围时自动扩展纵轴、不裁剪原始线。积极/消极、平静/激动只是数值方向，不是可靠类别，没有概率、准确率或校准宣传。
- `Prediction.timeline` 为可选字段，兼容旧任务；缺失或空 points 明确提示重新分析，不补造窗口或曲线。契约为 `kind: exploratory_static_windows`、10 秒窗口、5 秒步长、`feature_context: reused_full_clip_mert_windows`、`validated_dynamic_model: false`、`smoothed: false`、`points` 与后端 `disclaimer`。每点包含 index、start/end/center_seconds、feature_bins、valence/arousal、display_valence/display_arousal 与 out_of_range。时长不超过 10 秒为单点整段，较长音频末尾追加末窗；窗口构造与特征复用由后端负责。
- 宽幅 SVG 图用两条不同颜色曲线及明确图例，横轴为秒、纵轴为归一化评分。曲线连接真实窗口中心评分，仅一个窗口时只画两个维度的真实点、不连线或伪插值；连线不代表中间时刻模型预测。
- 点击图点或原生键盘可操作的片段按钮选择窗口，显示起止/中心、特征时间箱、双评分和相对整体差值。只将本地播放器 seek 到起点，不自动播放。timeupdate/seeked 同步播放线；暂停保留位置。窗口可重叠，“播放所在”优先选择包含当前位置、中心最近的窗口，距离相同按后端顺序；已选窗口与播放所在独立标识。
- 切换/移除音频、重新分析时清空选择和播放位置，暂停旧音频。上传/任务处理中禁重复提交和清除文件。failed 终态不再显示等待说明或进度条，明确任务已停止查询。
- 完整 JSON 导出仅包含 Prediction（含时间窗、声明与原始精度），不包含任务对象或访问令牌。CSV 每窗口一行，列为 start,end,center,bins,valence,arousal，UTF-8 BOM + CRLF 便于 Excel。CSV 仅数字列、不带用户文件名或文本输入；固定安全文件名，下载使用 Blob object URL 并及时 revoke。旧任务仍能导出 JSON，但禁止空窗口 CSV。
- 窗口结果是复用一次完整 MERT 特征的静态窗口探索，不是经验证的动态模型、逐秒情绪轨迹或实时识别；未经平滑与校准，不应用论文的 13.5% 校准效果。
- 后端契约约定上传声音临时处理后删除；实际文件删除与 CPU 限制由后端负责，前端不能单独证明。演示不是医疗建议。

## 验证

```powershell
npm run test
npm run typecheck
npm run lint
npm run build
```

自动测试使用显式独立 fixtures，原有 18 项接口/任务测试保持通过，新增 12 项窗口、播放、导出及失败终态回归测试，共 30 项（4 个测试文件）。Vitest 同时发现 `.test.ts` / `.test.tsx`；纯函数覆盖四位格式、保留原精度、重叠窗口最近中心选择、扩展原值纵轴、BOM 数字 CSV、完整 JSON、固定文件名和 object URL 撤销。组件测试覆盖窗口按钮及 SVG 点选择、seek 不自动播放、播放线/重叠高亮同步、暂停保留位置、选择/播放重置、单点无连线、旧任务无伪曲线。`npm run test/typecheck/lint/build` 全部通过。测试 fixtures 不进入生产页面，不能证明真实 MERT 预测效果。

本次升级仅做前端自动测试、类型检查、lint 与生产构建；没有重复启动 8000/5173 服务。未使用 OpenCLI 或实际浏览器做视觉、原生键盘交互和音频听播验收；jsdom 组件测试不代替真实浏览器验收。真实 CPU 推理及新时间窗接口由父任务验证，本 README 不声称已验收新后端结果。

依赖审计注意：shadcn CLI/CSS构建包已移到devDependencies，`npm audit --omit=dev`报告0项漏洞。完整开发依赖扫描仍报告7项high，根源为braces深层模式栈耗尽（GHSA-vfj7-8cjw-p6xm），经fast-glob/ts-morph/@shadcn/registry传播。未使用force破坏性降级；构建时只处理项目内受信任文件，后续需跟随上游修复更新锁文件。生产扫描通过不代表完整安全审查已完成。

## 文件结构

- `apps/web/src/routes/index.tsx`：中文上传、状态、二维图、原始数值及解释。
- `apps/web/src/routes/__root.tsx`：中文 HTML 文档、页面标题和 noindex。
- `apps/web/src/lib/api.ts`：契约类型、fetch、认证头、文件验证。
- `apps/web/src/lib/use-analysis.ts`：健康检查、上传、轮询、重试与清理。
- `apps/web/src/components/timeline-panel.tsx`：真实时间窗 SVG、片段选择、差值与 JSON/CSV 导出。
- `apps/web/src/lib/timeline.ts`：纯格式化、重叠选择、原值坐标域、CSV/JSON 与下载清理。
- `apps/web/src/lib/use-timeline-player.ts`：本地 audio ref、seek、播放位置同步和重置。
- `apps/web/src/lib/*.test.ts`、`components/*.test.tsx`、`timeline.fixtures.ts`：接口、任务、纯函数及播放选择组件测试；显式 fixtures 仅被测试导入。
- `apps/web/vite.config.ts`：独立开发/预览端口 5173。
- `packages/ui/src/components/`：CLI 生成的 shadcn Button、Card、Badge、Alert、Input、Label、Progress、Separator。
- `packages/ui/src/styles/globals.css`：浅色响应式视觉，系统中文字体、减少动画支持。
- `package-lock.json`：npm 工作区依赖锁。

## 脚手架记录与权限

先运行 `npx --yes shadcn@latest init --help` 确认 `--name` 与非交互选项，然后使用：

```powershell
npx --yes shadcn@latest init --preset b1D0eCA4 --template start --monorepo --rtl --pointer --name frontend --yes
```

生成真实 TanStack Start monorepo（apps/web + packages/ui），保留共享组件库；中文文档设置 `dir=ltr`。本任务只修改 frontend 目录，无 backend/论文/父目录 git 变更，没有 commit 或 push；不执行 SEO 推广、Cloudflare 接入或外部图片生成。
