# CPU依赖与模型下载记录

2026-10-12。用户授权下载演示模型与依赖。本轮无GPU使用、无新训练、无远端部署、无GitHub推送。

## 已完成

- 后端虚拟环境安装CPU Torch `2.6.0+cpu`、Transformers `4.38.2`、huggingface-hub `0.26.5`、nnAudio `0.3.3`及固定音频依赖。`torch.version.cuda is None`，pip check无冲突。
- 固定MERT `m-a-p/MERT-v1-95M` revision `12af15fef9d0ac838c3f475bfbbf26d2060dd4f5` 下载到`code/models/mert/`。6个文件：README、两个配置、两个Python模型源码与pytorch_model.bin。
- 权重377,552,987字节；SHA256 `a2b8b747f72c06e0595aeae41ae5473f4364938c6b39b2c58be38c48e6bd3fcd`与固定revision API公布LFS匹配；小文件Git blob SHA1逐项核验。
- 原Hub SDK因镜像HEAD元数据缺失失败，官方端点请求停滞后切换显式HTTP GET校验下载，没有绕过门控或忽略校验。
- `verify_backbone_cpu.py`实际载入并比对211个张量；生成一秒静音实际CPU前向得到[1,74,768]有限特征。BACKBONE_CPU_PASS；载入+短前向约1.616秒，不能当成真实音乐、长片段或端到端速度。
- Transformers位置卷积权重重命名警告仍出现，但原始211个张量均相等，不将未验证随机初始化作为结果。
- 下载新增3项回归测试，总后端21项通过。实时health由缺推理依赖转为缺论文预测head，503拒绝上传仍有效。

## 唯一资产阻碍

原实验服务器`connect.nmb2.seetacloud.com:31740`无法建立SSH连接，发生在认证前；未获得训练头。已检查工作区也无该PT文件，不用随机head替代。

所需文件：`/root/autodl-tmp/music-emotion-rebuild-20261008/runs/static-emotion-v2-20261008/mean_mlp-seed20261011/best.pt`；目标`code/models/mean_mlp-seed20261011.pt`；SHA256 `18a8f83c9ed879a6c214f8f21332a048dcf9196c2d8766f89b4cf35e6f3c469d`。

恢复实例或提供新的连接地址后可继续。SSH密码仅从进程环境使用，不写入脚本或本文。此前观测host-key固定核验，任何变化不能静默接受。

## 后续恢复与完成（10:17后）

用户重新提供SSH连接后，预测头成功取回，host-key与既有记录一致，head SHA256与论文记录一致。原端口不可达的阻碍已解除。

`smoke_real_cpu.py`通过真实HTTP API上传3秒和45秒本地生成的双频PCM测试音频，由实际MERT＋论文head完成预测；记录设备cpu、无校正、固定seed/revision、3/45有效bin，结果均有限，服务端上传音频清理通过。处理耗时分别3.473秒和8.761秒；它们是流程测试，不是情绪准确性证据或普遍时延基准。

实时health已为ready、model.loaded=true；完整记录保存在忽略目录`.runtime/real-cpu-upload-check.json`。没有随机head、GPU推理或新训练。

## 沉淀脚本

- `backend/scripts/fetch_source_head.py`：固定SSH身份与headSHA下载（本次无法连接，未成功）。
- `backend/scripts/prepare_models.py`：允许只准备backbone、不生成head；HTTP transport针对镜像HEAD问题。
- `backend/scripts/pinned_http_download.py`：固定commit、LFS/Blob校验与有限文件集，可恢复下载。
- `backend/scripts/verify_backbone_cpu.py`：真实CPU权重及前向检验（本次PASS）。
- `backend/tests/test_download_checks.py`：拒绝错误checksum与不同revision测试。

下载模型、依赖和临时验收文件仍由.gitignore排除。本轮尚无完整音乐情绪预测结果，需匹配论文训练head后验收。
