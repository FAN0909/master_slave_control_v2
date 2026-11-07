# Follow Control 数据采集

安装项目依赖（包含 LeRobot 采集依赖）：

```bash
.venv/bin/python -m pip install -r requirements.txt
```

采集时先连接主手、从手和需要的相机，启动跟随，填写 Task 和保存目录，在 Format 下拉框选择 **lerobotV3.0** 或 **lerobotV2.1**，然后依次点击 **StartRecod → StopRecod → Save episode**。停止后也可以选择 **Discard episode**。关闭主窗口时，未保存的已采集 episode 会自动保存。格式在本条 episode 采集期间锁定，下一条可以重新选择。界面标签显示当前保存目录与格式的数据集里已保存的 episode 条数及累计帧数，保存完成后更新。

所选保存目录下分别使用 `lerobot_v21/`、`lerobot_v30/` 作为两个数据集根目录。每次保存会在对应数据集中追加一条 episode，不再为每次采集创建独立数据集；不会上传到 Hugging Face。旧版 `episode-时间-标识/` 文件夹保持原样，不会自动合并。v3.0 使用当前 LeRobot 写入 API；v2.1 使用每条 episode 单独的 Parquet 和 MP4 文件，以及共享的 `meta/info.json`、`meta/episodes.jsonl`、`meta/tasks.jsonl`、`meta/episodes_stats.jsonl`。已有数据集的格式、帧率、相机或关节字段与当前设置不一致时会拒绝追加；要采集另一种字段配置，请选择新的保存目录。数据按参考数据集的核心字段记录：未连接灵巧手时，`observation.state` 是从手反馈、`action` 是从手目标；连接灵巧手时，状态按“从手反馈 + 灵巧手反馈”拼接，动作按“从手目标 + 灵巧手目标”拼接，两者维度相同。不会额外写入 `observation.hand_joints`、`observation.master_joints` 或 `capture_elapsed_s`；主手样本仍用于当前控制/采样对齐逻辑。手部目标在每次跟随开合命令切换时更新，初始目标采用跟随开始时的实测手部位置。`config/recording.json` 设置两种状态/动作向量各自记录的手臂和灵巧手关节数；修改后下一条 episode 生效。相机写入 `observation.images.<camera>`。标准 `timestamp` 仍由帧序号和设定帧率生成。关节数值采用驱动原生单位。采集周期使用启动跟随时的周期，须能整除 1000 毫秒。

设备线程读取后将样本和采集时间发布到共享快照。点击开始后，写入线程先等待一组完整样本来确定字段和图像尺寸，并初始化 LeRobot 数据集；这组预检样本不写入 episode。初始化完成后，独立采样线程才按跟随周期选取最近值并检查时间差，再通过最多 32 帧的队列交给写入线程。相机或关节反馈超过 250 毫秒未更新，或各路采样时间差超过两个采集周期时，该周期不写入样本。停止后日志会报告缺失、时间差过大、队列满次数，以及初始化耗时、队列峰值、单帧写入耗时、实际帧率和最大帧间隔。

彩色视频使用 H.264 fast 流式编码。v3.0 保存时完成视频收尾并写入 Parquet；v2.1 在采集期间分批写 Parquet，保存时收尾视频并生成元数据。界面在完成后恢复操作。首次上机请先采一条短 episode，并检查回放与关节数值。
