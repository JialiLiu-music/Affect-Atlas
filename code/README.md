# 音乐情绪 CPU 上传演示站

本目录是论文配套的前后端分离演示代码，**不会使用GPU，也不会返回模拟预测分数**。预测任务是音频片段的整体愉悦度（Valence）与唤醒度（Arousal），不是逐秒情绪轨迹、情绪诊断或预测准确率。

## 功能与限制

- 中文前端：选取音频、本地试听、上传、任务进度、整体双轴坐标和探索性窗口曲线；支持片段详情、播放时间线联动及JSON/CSV导出。
- FastAPI后端：20MB以内、1–90秒WAV/MP3/FLAC/OGG音频，完整处理，不自动截断长曲。M4A须先转换格式。
- 单CPU工作进程逐个处理；模型首次加载后常驻同一推理子进程；最多3个等待任务；单任务含解码/加载最长20分钟，超时终止子进程。
- 音频进入临时目录，成功、失败及服务退出时删除。结果只保留内存，完成后1小时过期。原上传文件名不保存。
- 整体预测默认无校正（`calibration: none`）。没有将论文的PMEmo适应池偏移用于任意上传音乐；真实校正需要目标集合评分。
- 探索性时间窗口：固定10秒窗口、5秒步长；不足10秒返回一个整段窗口，长片段最后补齐尾窗。两轴曲线使用窗口中心时间定位，详细起止时间可查询。
- MERT对整段音频只提取一次，窗口复用已有1Hz特征；静态训练头作用于窗口特征均值。它不是独立裁剪音频后重新提取特征，也不是动态模型，不能解释为每秒情绪真值；窗口短于原45秒训练片段，局部准确性尚未验证。
- 曲线不平滑、不自动套校正，原始窗口值用于JSON/CSV导出；相邻窗口有重叠，不是互相独立的预测样本。
- 前端图上坐标仅为展示裁剪到[-1,1]，原始模型值保留；分数不是概率，也不是对所有听者一致情绪的测量。
- 默认只绑定本机127.0.0.1；目前是本地研究演示，不是已加固的公共匿名上传服务。

## 当前真实状态

2026-10-12：CPU Torch 2.6.0+cpu、Transformers4.38.2和音频依赖已经安装，固定revision MERT及论文mean_mlp预测头均准备完成。预测头SHA与原实验记录一致；211个MERT张量校验通过。健康接口为`ready`，完成首次任务后`loaded=true`，可以上传真实音频。

通过真实HTTP API，3秒和45秒生成测试音频均由实际MERT＋论文预测头完成CPU预测，并清理上传文件；处理耗时分别约3.473秒和8.761秒。它们只证明执行流程，不是音乐情绪准确性评价，也不是所有音乐或设备的速度承诺。浏览器视觉/键盘/播放验收仍未执行。

## 目录

- `backend/app/`：CPU模型、固定特征契约、任务队列、上传边界及接口。
- `backend/scripts/prepare_models.py`：获取固定revision的公开MERT模型，核验既有head。
- `backend/tests/`：接口边界与真实音频解码测试。
- `frontend/`：React/TypeScript中文页面与共享组件，启动命令见下方。
- `models/`：本地模型目录，已忽略，不上传Git。
- `.runtime/uploads/`：短期音频，已忽略，不上传Git。

## 一、启动后端（Windows PowerShell，Python 3.10–3.12）

```powershell
cd E:\project\test\ljl\lunwen2\code\backend
python -m venv .venv
.\.venv\Scripts\python -m pip install --index-url https://pypi.org/simple -r requirements-api.txt
.\.venv\Scripts\python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 1
```

只运行1个API worker，避免队列和临时目录发生多进程归属冲突。接口说明：`http://127.0.0.1:8000/docs`；状态：`http://127.0.0.1:8000/api/health`。

API依赖与推理依赖分开，缺模型时仍可清楚显示服务和资产状态。

## 二、准备真实CPU推理依赖与权重

先停止后端，再在`backend`安装：

```powershell
.\.venv\Scripts\python -m pip install torch==2.6.0 --index-url https://download.pytorch.org/whl/cpu
.\.venv\Scripts\python -m pip install --index-url https://pypi.org/simple -r requirements.txt
```

使用CPU版Torch，并在工作进程中显式禁用CUDA。MERT通过固定revision的自定义模型代码运行；准备脚本将来源与各文件SHA写入manifest，运行时离线读取并检查211个权重张量。

### 预测头（必须使用论文权重）

从已有实验服务器保存以下文件到`code/models/mean_mlp-seed20261011.pt`，不要训练或生成随机替代head：

- 服务器相对路径：`runs/static-emotion-v2-20261008/mean_mlp-seed20261011/best.pt`。
- 所属项目：`/root/autodl-tmp/music-emotion-rebuild-20261008/`。
- SHA256：`18a8f83c9ed879a6c214f8f21332a048dcf9196c2d8766f89b4cf35e6f3c469d`。

本演示事先固定seed20261011，不根据上传结果选择种子；论文13.50%来自三个seed及适应池平均，本演示默认来源预测并不复制那项校正收益。

### 固定MERT版本

```powershell
$env:HF_ENDPOINT='https://hf-mirror.com'
.\.venv\Scripts\python scripts\prepare_models.py --model-dir ..\models\mert --head-path ..\models\mean_mlp-seed20261011.pt
```

固定模型为`m-a-p/MERT-v1-95M`，revision `12af15fef9d0ac838c3f475bfbbf26d2060dd4f5`。脚本先校验head再下载，不接受其他来源的小网络。也可以通过环境变量`MER_MODEL_DIR`/`MER_HEAD_PATH`指向已准备的位置；现有snapshot需要通过来源/文件清单准备，不能只放一份未核验权重冒充论文模型。

重启API后，资产状态转为可用；首次任务会加载并再次检查权重，如任何张量不一致任务明确失败，不返回随机初始化的结果。配置`.env.example`仅作示例，后端从进程环境读变量，不自动加载.env。

如果来源服务器暂不可达，可先只准备公开backbone：

```powershell
$env:HF_ENDPOINT='https://hf-mirror.com'
.\.venv\Scripts\python scripts\prepare_models.py --model-dir ..\models\mert --backbone-only --transport http
```

HTTP方案专用于镜像缺少Hub SDK所需HEAD元信息时，先核对固定commit，再检查权重LFS SHA256和源码/配置Git blob SHA1；支持中断后续传。`--backbone-only`不会生成或替代训练head，也不会启用预测。已有manifest无需重复下载，直接补充匹配SHA的head即可。

`backend/scripts/fetch_source_head.py`可从原实验服务器下载训练head，密码只读`MER_SSH_PASSWORD`进程环境，SSH身份必须匹配工作区原host-key记录；若地址不可达，需要恢复实例或使用有效的新连接信息。`verify_backbone_cpu.py`可独立验证已下载backbone的211张量和实际CPU前向，但没有head时不构成完整音乐情绪预测。

## 三、前端运行

前端Node.js要求22.12或更高。在第三个终端运行：

```powershell
cd E:\project\test\ljl\lunwen2\code\frontend
npm ci
npm run dev
```

打开 `http://localhost:5173`。详细配置见`frontend/README.md`；API默认`http://127.0.0.1:8000`，前端开发端口固定5173。

前后端运行在两个终端，若自定义端口，需要同时调整前端`VITE_API_BASE_URL`和后端`MER_CORS_ORIGINS`。

## 接口契约

- `GET /api/health`：CPU、依赖/资产状态、载入状态、队列及限制。`ready`表示资产预检查可用，初次模型完整载入仍可能报告校验错误；以完成任务作为真实推理成功证据。
- `POST /api/jobs`：multipart字段`file`；返回任务ID和访问令牌。503缺模型、413超大小、415格式不支持、429队列满。
- `GET /api/jobs/{job_id}`：请求头`X-Job-Token`携带令牌，返回阶段、进度、原始双轴预测等。不把令牌放URL或日志。缺失/错误令牌均返回404。

进度是已完成窗口的工作比例，不是ETA；CPU处理时间仅在真实任务完成后报告。

## 测试与复核

```powershell
cd E:\project\test\ljl\lunwen2\code\backend
.\.venv\Scripts\python -m pytest -q
```

音频测试需要安装numpy、soundfile、librosa；接口测试不需要Torch。接口测试用明确的测试worker，不衡量MERT准确性；真实音频测试覆盖完整片段解码、声道均值、重采样、长音频拒绝和损坏/非有限音频拒绝。

特征实现沿用论文：24kHz mono、last4层平均、10秒窗口/5秒步长、1Hz有效中心bin、float32时间平均。末尾不足0.5秒不增加bin，与原始提取器一致；没有对音频套用固定首45秒裁剪。

## 公网部署前

目前不自动部署或推送。公网演示需额外配置HTTPS反向代理、严格上传速率限制、认证/配额、资源监控及隐私告知。可设置`MER_API_TOKEN`要求Bearer访问，但公开前端里预置token无法保密，应由认证后端或用户输入承接；不要把共享密钥作为VITE环境变量打包发布。研究演示服务默认只开放本机，禁止直接无保护地将API绑定公网。

音乐版权和隐私由上传者负责；服务器仅临时处理，模型输出不用于医疗或个体心理诊断。
