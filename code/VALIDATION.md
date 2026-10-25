# 本地验收记录

日期：2026-10-12。代码位于`lunwen2/code`；本轮仅搭建本地演示，不训练、不部署、不提交或推送GitHub，不修改论文正文。

## 已通过

- 后端`backend/.venv/Scripts/python -m pytest -q`：18项通过（2项第三方弃用警告）。覆盖资产缺失拒绝、任务令牌、上传前字节限额、空/超大小/不支持格式、文件路径隔离、队列、鉴权、过期、任务成功失败清理；真实PCM解码/声道均值/重采样/长片段拒绝；Windows真实spawn子进程超时终止。
- 4项特征契约测试通过：用明确的小型测试double，将CPU演示窗口、last4平均、有效时间bin及池化与工作区原extract_mert函数对比，涵盖短音频、45秒与尾部边界。这证明代码契约一致，不是实际MERT的音频准确性或数值重放。
- 前端`npm run test`：18项通过，测试fixture只存在tests中。覆盖缺模型禁上传、M4A转换提醒、限额、头部令牌、重复提交、轮询/暂停恢复/截止/卸载以及更换文件清除旧结果。
- 前端`npm run typecheck`、`npm run lint`、`npm run build`通过；再次build命中缓存。`npm audit --omit=dev`为0项。
- 真实HTTP：`http://localhost:5173/`返回200，页面包含中文标题、文件选择和双轴坐标；`http://127.0.0.1:8000/api/health`返回CPU/no-calibration/not_ready，缺真实权重依赖时POST明确503，没有生成随机预测。
- 复用链路保存在`backend/scripts/smoke_api.py`和`check_readiness.py`，本轮已用真实本地参数执行。

## 尚未验证 / 未完成

- 后续模型准备已完成：CPU Torch2.6.0+cpu、Transformers4.38.2、固定MERT与论文预测头均可用。head SHA匹配，211张量通过，真实HTTP3秒/45秒生成测试音频的完整预测成功（非情绪准确性验证）。
- 模型准备路径、固定revision、head SHA256及CPU安装步骤已写README。真实模型服务已ready、loaded，上传功能可用。
- 浏览器视觉、键盘、音频播放尚未执行；真实MERT上传→结果流程已用生成测试音频验证。HTTP和单元测试不能替代浏览器操作验收，也不证明真实音乐情绪准确性。
- 完整开发依赖扫描仍有7项high（braces/CLI相关）；shadcn为devDependency，仅处理受信任项目文件。未声称全依赖安全通过，发布公网前应升级上游与额外鉴权限流。

## 服务地址与使用范围

本轮启动本地前端5173与API8000，浏览器可打开前者查看缺模型状态。服务不是公网部署，未开启GPU。终止各启动终端会关闭服务；重新启动命令见README。前端停止查询不自动取消后端任务，上传成功的任务由单进程限时执行并清理音频。
