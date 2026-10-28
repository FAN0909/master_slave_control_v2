# 设备扩展约定

业务层依赖 `base/` 中的接口；`drivers/` 继承对应接口并封装厂商 SDK。
厂商 SDK 在连接时加载，设备层使用标准 `logging`，不依赖 PySide6 或 UI 日志类。

```text
BaseCamera    → CameraD435
BaseHand      → LinkHand
BaseMasterArm → GelloArm
BaseRobotArm  → NrcArm
```

## 新增设备

1. 在 `drivers/` 添加驱动，继承对应基类，构造函数调用 `super().__init__(name)`。
2. 实现抽象方法，保持方法名、参数名及返回值约定一致。
3. 主臂和从臂设置 `MAX_JOINT_COUNT`、`TCP_DIM`，灵巧手实现 `MAX_JOINTS()`。
4. 有使能或 TCP 能力的主臂设置 `supports_enable` / `supports_tcp` 并实现相关方法；
   支持 ServoJ 的从臂设置 `supports_servoj` 并实现相关方法。
5. 将 SDK 的数据转换成接口要求的单位，校验长度及有限数值，并添加模拟 SDK 测试。

## 调用规则

- `Connect()` 可重复调用，已经连接时直接成功；`Disconnect()` 可在未连接时调用。
- 命令成功返回 `True`，失败返回 `False`，详细原因在 `last_error`，同时输出日志。
- 关节或 TCP 读取失败返回 `[]`，禁止用全零数据代替失败，也不补齐或截断无效关节读数。
- 相机没有新帧时返回 `None`，此时 `last_error` 为空；读取异常也返回 `None`，但会设置错误信息。
- 机械臂关节角度使用度；TCP 顺序为 `[X, Y, Z, Rx, Ry, Rz]`，单位为毫米、度。
- 灵巧手位置、速度和力的单位由驱动定义。当前 LinkHand 使用 SDK 的 0～255 原生值，
  速度必须传列表，通道规则见其类说明。
- `True` 表示命令已提交并通过 SDK 的返回值检查，不代表运动已经完成。
- NRC 发送 ServoJ 位置前必须成功调用 `Open_servoJ()`。
- 断开失败时保留尚未释放的句柄，以便重试；未成功释放前不要丢弃驱动实例。
- 同一个驱动实例由所属线程串行操作，不支持并发连接、断开与运动。

## 验证

在项目根目录执行（不连接真实硬件）：

```bash
.venv/bin/python -m unittest discover -s tests -v
```
