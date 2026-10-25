# Low-Label Output Calibration for Music Emotion Regression

音乐情绪跨数据集少样本输出校准论文初稿及配套图表。

## 阅读入口

- [英文论文正文](manuscript_en.md)
- [HTML阅读版本](manuscript_en.html)（GitHub显示源代码，可下载仓库后本地打开）
- [Word可编辑版本](manuscript_en.docx)
- [图表及图注](figures/captions.md)
- [文献证据记录](working/literature_evidence.json)

## 研究内容

使用冻结MERT音乐表征和DEAM训练的情绪预测头，在PMEmo完整副歌数据上比较5/10首评分预算下的输出校正。预设10首评分、仅唤醒度半强度偏移的主要对比，在334个固定评价风险组代表上使唤醒度均方误差平均降低13.50%。论文正文和附录记录了数据职责、完整对照、适应池稳定性以及结论适用范围。

当前为英文论文初稿，作者信息、目标期刊模板及正式投稿声明需要后续补充。

## CPU音乐情绪演示网站

网站源码位于 [`code/`](code/README.md)，前后端分离：React/TypeScript中文页面与FastAPI CPU后端。支持上传片段、整体双轴预测、10秒窗口/5秒步长评分曲线、播放联动及JSON/CSV导出。窗口曲线来自静态模型，不是经验证的逐秒动态识别；默认无目标域校正。

启动、固定MERT下载和论文预测头校验见 [`code/README.md`](code/README.md)。仓库不包含模型权重、试听音乐、虚拟环境或node_modules；克隆代码后仍需准备真实模型资产。自动测试与真实CPU执行的范围见 [`code/VALIDATION.md`](code/VALIDATION.md) 和 [`code/TIMELINE_UPGRADE-20261012.md`](code/TIMELINE_UPGRADE-20261012.md)。本仓库源码上传不等于公网网站部署。

## 文件结构

- `manuscript_en.*`：Markdown、HTML和Word正文。
- `figures/`：6幅图的PNG/PDF/SVG、图注及来源校验manifest。
- `scripts/`：图表生成、正文结构检查和版本导出脚本。
- `working/`：证据地图、文献记录、章节蓝图及修订说明。

## 脚本说明

在本目录运行 `python scripts/audit_manuscript.py` 可检查正文结构与文件引用。

`python scripts/build_manuscript_outputs.py` 从Markdown更新HTML和Word。先安装 `python -m pip install -r scripts/requirements-documents.txt`（Python 3.10及以上）。HTML使用原生MathML离线显示公式，适合现代Chrome、Edge或Firefox；Word使用Pandoc转换为可编辑的原生公式对象。Markdown采用GitHub支持的 `$...$` 和 `$$...$$` 公式定界符。

运行 `python scripts/test_math_rendering.py` 可核验10个独立公式、行内公式、Word公式结构，并检查相对于原始提交的数学表达式保持不变。`python scripts/test_reporting_integrity.py` 检查贡献措辞修订前后的完整结果表、附录、参考文献和必要限制保持一致。GitHub源码页面只展示HTML代码，阅读HTML需要本地打开；阅读Markdown时请使用渲染视图而非Raw源码。

图表生成依赖`numpy`、`matplotlib`以及原工作区的`进度/`实验JSON。完整原始实验产物、模型权重、音乐音频与本地安装依赖不包含在本仓库；仓库中的`figure_manifest.json`保留来源路径与SHA记录，不能据此声称已公开完整实验数据。

商业歌曲音频未随仓库发布。数据与模型来源请参见论文及参考文献。
