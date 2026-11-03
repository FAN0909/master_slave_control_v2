# Follow Control 数据采集

安装项目依赖（包含 LeRobot 采集依赖）：

```bash
.venv/bin/python -m pip install -r requirements.txt
```

采集时先连接主手、从手和需要的相机，启动跟随，填写 Task 和保存目录，在 Format 下拉框选择 **lerobotV3.0** 或 **lerobotV2.1**，然后依次点击 **StartRecod → StopRecod → Save episode**。停止后也可以选择 **Discard episode**。关闭主窗口时，未保存的已采集 episode 会自动保存。格式在本条 episode 采集期间锁定，下一条可以重新选择。

每条 episode 保存在所选目录下独立的 `episode-时间-标识` 文件夹，是本地 LeRobot 数据集；不会上传到 Hugging Face。v3.0 使用当前 LeRobot 写入 API；v2.1 使用每条 episode 单独的 Parquet 和 MP4 文件，以及 `meta/info.json`、`meta/episodes.jsonl`、`meta/tasks.jsonl`、`meta/episodes_stats.jsonl`。`observation.state` 是从手关节反馈，`action` 是已发送的从手关节目标，`observation.master_joints` 是主手关节位置。三者及 `observation.hand_joints` 的写入关节数由 `config/recording.json` 分别设置；`action` 使用从手的关节数。修改配置后，下一条 episode 生效；设备线程仍保留完整数据供控制使用。连接的灵巧手和相机会分别写入 `observation.hand_joints` 和 `observation.images.<camera>`。`capture_elapsed_s` 记录实际采样经过的秒数，便于检查漏帧；LeRobot 标准 `timestamp` 仍由帧序号和设定帧率生成。关节数值采用驱动原生单位。采集周期使用启动跟随时的周期，须能整除 1000 毫秒。

设备线程读取后将样本和采集时间发布到共享快照。点击开始后，写入线程先等待一组完整样本来确定字段和图像尺寸，并初始化 LeRobot 数据集；这组预检样本不写入 episode。初始化完成后，独立采样线程才按跟随周期选取最近值并检查时间差，再通过最多 32 帧的队列交给写入线程。相机或关节反馈超过 250 毫秒未更新，或各路采样时间差超过两个采集周期时，该周期不写入样本。停止后日志会报告缺失、时间差过大、队列满次数，以及初始化耗时、队列峰值、单帧写入耗时、实际帧率和最大帧间隔。

彩色视频使用 H.264 fast 流式编码。v3.0 保存时完成视频收尾并写入 Parquet；v2.1 在采集期间分批写 Parquet，保存时收尾视频并生成元数据。界面在完成后恢复操作。首次上机请先采一条短 episode，并检查回放与关节数值。
