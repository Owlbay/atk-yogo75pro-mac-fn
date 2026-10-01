# ATK YOGO 75 PRO：Mac Fn / 地球仪键改造

给 ATK YOGO 75 PRO（USB `373B:119B`，蓝牙 `36B0:3004`）准备的两套修改固件，让键盘在 Mac 模式下的实体 Fn 像 Mac 键盘的 🌐/Fn 一样工作。都基于官方 V1.26，Win 模式保持原厂逻辑。

> **非官方项目，风险自负。** 刷写修改固件可能导致键盘无法使用；救砖路径只验证过「固件完好时退出 bootloader」。固件代码版权归 ATK 所有，本仓库与 ATK 无关。不要用于其他型号。

## 两个版本

| | **v2：完整 Fn**（推荐） | **v4：免主机软件** |
|---|---|---|
| 固件 | `固件/YOGO75PRO-v1.26-MAC-Fn-F24-StandardFRow-v2.bin` | `固件/YOGO75PRO-v1.26-MAC-Fn-Globe-v4.bin` |
| SHA-256 | `e1374c770f0ccf3f34ab6422836663615041023865ae873f7f979b103019c645` | `8415844908cf603d1351ad4b366be223d39d8cf4938a214366bddffe1a45ed38` |
| Mac 模式 Fn 发出 | F24，由 macOS 映射成真正的 Fn | Consumer Globe `0x0C:0x029D` |
| 主机侧 | 需要运行 `主机映射/安装映射.sh` | 不需要 |
| 单按切换输入法 | ✅ | ✅ |
| Fn+F / N / E / Q 等系统快捷键 | ✅ | ❌ |
| Fn+方向键（Home/End/翻页）、Fn+Delete | ✅ | ❌ |
| 默认 F1–F12，Fn+F 行为媒体键 | ✅ | ✅ |
| 实测 | 有线、蓝牙 1 号槽通过（两把键盘） | 有线通过，结果和预期一致 |

官方原包 `固件/YOGO75PRO-v1.26-original.bin`（SHA-256 `a20bc774d12f0a627a150d35d5efb0893ae95e20c6e16fcebe03111c031c5725`）也放在仓库里，用于重新构建和恢复。

### 为什么 v4 做不到完整 Fn

macOS 只把 Apple 私有用途 `0xFF:0x03` 当作 Fn 修饰键，而且只有 Apple 自己的键盘驱动才会保留这个用途；第三方 VID 的键盘发出来会被驱动丢弃。Globe（`0x029D`）对任何键盘都有效，但它在系统里只是普通按键，不是修饰键，所以只有单按的效果。v2 改为发送 F24，再由系统映射（`hidutil UserKeyMapping`）在驱动之后改写成 Fn，以此绕开这个限制。

## 改了什么

两版共用 v2 的 F 行逻辑：按下时根据 Fn 是否按住，决定这一键是标准 F 键还是媒体键，并一直保持到松开，避免先松 Fn 造成卡键。只修改了原包中少量字节，并在原有最后一个 Flash 扇区内追加了一段补丁代码；USB/BLE 描述符、键表和设备身份都不变。

- v2：`工具/globe_patch_v2.s`，Mac 模式下 Fn 作为 F24 加入键盘报告。
- v4：`工具/globe_patch_v4.s`，在 v2 基础上只改 Fn 的上报，通过原有的媒体报告发送 Globe；松开 Fn 时只清除 Globe，不会截断按住中的媒体键。

## 构建与离线验证

```bash
python3 -m venv /tmp/yogo-venv
```

```bash
/tmp/yogo-venv/bin/pip install capstone unicorn hidapi==0.15.0
```

在 `工具/` 目录下（需要 Xcode 命令行工具里的 clang）：

```bash
/tmp/yogo-venv/bin/python build_patch_v2.py
```

```bash
/tmp/yogo-venv/bin/python build_patch_v4.py
```

```bash
/tmp/yogo-venv/bin/python verify_patch_v4.py
```

构建脚本只接受官方 V1.26 原包的精确散列，输出与仓库里的固件逐字节一致。验证脚本用 Unicorn 模拟固件中的相关函数：v2 共 597 项，v4 共 634 项，包括 Win 模式与官方固件的逐项对比。结果存放在 `verification-v2.json` 和 `verification-v4.json`。

## 刷写（必须有线连接，全程不要拔线）

在 `工具/` 目录下：

1. 备份设置（只读）。刷写会把设置重置为默认值，结果存到 `备份/`：
   ```bash
   /tmp/yogo-venv/bin/python probe_device.py
   ```
2. 刷写，`v2`、`v4`、`original` 三选一：
   ```bash
   /tmp/yogo-venv/bin/python flash_yogo.py flash v2 --backup ../备份/<你的备份>.json
   ```
3. 恢复设置，并回读核对设置和键位：
   ```bash
   /tmp/yogo-venv/bin/python restore_runtime_config.py --backup ../备份/<你的备份>.json
   ```

刷写工具按 ATK HUB 的升级协议实现，只接受上面三个固件的固定散列。打开升级接口时，macOS 可能要求授予输入监控权限。也可以随时在 ATK Hub → 设置 → 固件工具 里装回官方 V1.26，这会覆盖本改造。

## v2 的主机映射

```bash
bash 主机映射/安装映射.sh
```

脚本会安装用户级后台任务 `local.atk-yogo.fn-map`，在登录时运行，之后每 5 秒检查一次：给这把键盘的 USB 身份和蓝牙 1–3 号槽加上设备限定的 F24→Fn 映射，键盘重连后几秒内恢复。它只调用系统自带的 `hidutil`，不读取键盘输入，也不联网；保留其他映射，遇到冲突时不会覆盖。换一台 Mac 需要重新安装。

卸载（先用 `--dry-run` 预览）：

```bash
bash 主机映射/卸载映射.sh
```

## 点阵屏

键盘右上角的 6×6 RGB 点阵屏，可以通过有线连接由电脑实时控制，不需要改固件。`工具/点阵屏时钟演示.py` 会滚动显示时钟，只用实时帧命令，不写 Flash。蓝牙在现有固件下不能实时控制。协议细节见 [docs/点阵屏实时控制分析.md](docs/点阵屏实时控制分析.md)，固件地址见 [docs/技术笔记.md](docs/技术笔记.md)。

## 未覆盖

- 2.4 GHz 接收器：身份和描述符由接收器决定，未测试。
- 蓝牙 2、3 号槽：规则已包含，未实测。
- Windows 电脑：只做过离线对比，没有实机测试。
