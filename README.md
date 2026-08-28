# 遥感智能解译综合平台（插件化原型）

这是一个独立的 PySide6 桌面软件原型。它用统一地图工作空间承载道路、建筑物提取与建筑物变化三个独立模块，当前所有处理均为定时器驱动的 Mock，不包含真实算法。

## 运行

```powershell
python -m pip install -r requirements.txt
python main.py
```

Windows 下也可以直接双击仓库根目录中的 `启动遥感平台.bat` 启动主页面。启动文件会自动定位仓库目录，并优先使用项目内或系统中的 `pythonw`，无需手动打开命令行。

运行测试：

```powershell
python -m unittest discover -s tests -v
```

## 目录与职责

```text
main.py / main_window.py    组装通用基础设施和展示层
core/                       稳定的数据契约、总线、注册中心与共享上下文
modules/*/plugin.py         模块能力、工作流、步骤、参数、工具、结果声明
modules/*/adapter.py        平台命令到模块任务的适配边界（本轮为 Mock）
modules/road/contracts.py   可序列化 Road Job / Worker JSON-Lines 协议
modules/road/runner.py      未来独立道路环境的进程启动边界
modules/road/ui/            道路模块自有的专用操作页面
widgets/                    完全由描述模型驱动的通用 Qt 控件
styles/                     统一视觉样式
tests/                      插件发现、兼容性隔离和依赖边界测试
```

`ModuleRegistry.discover()` 自动扫描 `modules` 下提供 `create_plugin(event_bus)` 的插件包。注册中心内部保留模块实现用于命令路由，同时生成不可变的 `ModuleDescriptor` 和 `WorkflowCapability` 供后续平台能力接入；当前主页面的 `Ribbon` 使用固定的四个一级模块入口，不读取具体插件实例，也不导入任何具体插件或 Adapter。

`WorkflowDefinition` 只描述一个可执行能力的名称、步骤、参数和可选展示提示。它不是主窗口布局定义：平台可以把同一能力放入 Ribbon、菜单、工具栏或其他入口，而无需修改业务模块。

当前主页面使用统一的内部 ID（`road`、`building_change`、`building_extract`、`agent`）驱动四个顶部入口。点击入口会切换右侧 `ModulePanel` 的对应页面。平台默认根据公开描述生成通用页面；模块也可以在插件入口导出可选的 `create_operation_page` 工厂。道路模块使用自有 `RoadPanel`，建筑模块继续使用通用页面，未注册模块显示平台预留页。

布局采用“左侧统一项目/图层树 + 中央地图上下文栏与地图画布 + 右侧模块操作/日志任务纵向分栏”。项目树支持区域、原始数据、时相、成果和公共数据等通用层级；图层 checkbox 通过展示层信号控制进入地图画布的可见图层集合。

## 后续模块接入时的按钮流转

```text
顶部模块入口
        ↓
右侧 ModulePanel 承载对应模块界面
        ↓
通用页面或模块自有页面表达用户意图
        ↓
生成统一 Command
        ↓
CommandBus.dispatch()
        ↓
ModuleRegistry.dispatch()
        ↓
按 module_id 找到 ProcessingModule
        ↓
Plugin.handle_command()
        ↓
对应 Adapter
```

`ModulePanel` 不判断具体模块。它优先使用 Registry 提供的可选页面工厂，没有工厂时继续根据 `ModuleDescriptor` 和 `WorkflowDefinition` 生成通用参数、步骤与运行按钮。页面不会调用 Adapter 或算法，运行和工具动作统一转换为 `Command`。

## 模块进度如何回到界面

```text
RoadAdapter / BuildingAdapter / ChangeAdapter
        ↓ publish
TaskStarted / TaskProgress / TaskLog / TaskCompleted
        ↓
EventBus（QObject + Signal）
        ↓
MainWindow 的通用状态槽
        ↓
状态栏 / 进度条 / LogPanel
```

Adapter 和 Plugin 都没有主窗口引用，也不会操作 Qt 控件。结果通过 `ResultAvailable` 和 `LayerAdded` 事件进入共享 `LayerManager`，再同步到项目树和地图空间。

## Road 模块以后更新

道路模块当前提供 `full_pipeline`、`rerun_period` 和 `rerun_change_pair` 三个稳定工作流。`RoadPanel` 只让用户选择区域、期次和少量高级参数；项目路径、输入清单与输出位置由 `ProjectContext` 提供。`RoadAdapter` 已不再继承 `TimedMockAdapter`，而是把 Command 转换成可写入 `job.json` 的 `RoadJob`，再把 Mock/Worker 事件映射回平台 Task、Result 与 Layer 事件。

真实算法接入时，主要实现 `RoadProcessRunner.start_job()`（例如使用 `QProcess` 启动独立 Python 环境）并替换 `RoadAdapter.run_mock_job()` 的调用路径。独立 Worker 按 JSON Lines 输出 `started/progress/log/result/completed/error`，无需获得 Qt 或 `ProjectContext` 对象。

修改道路内部流程时，只改：

- `modules/road/plugin.py`：增加、删除或调整 Workflow、Step、Parameter、Tool、ResultType；
- `modules/road/adapter.py`：接入或升级原道路软件的调用方式；
- `modules/road/contracts.py`：在兼容前提下演进 Job 与 Worker 协议；
- `modules/road/runner.py`：配置并启动独立道路环境；
- `modules/road/ui/`：仅在道路业务交互本身变化时调整；
- 道路模块自己的内部算法文件（未来新增）。

完全不需要修改：

- `main_window.py`；
- `widgets/ribbon.py`；
- `widgets/workflow_panel.py`；
- `widgets/parameter_panel.py`。

当前四个顶部模块入口与具体插件能力解耦；未来模块界面可以通过 Platform Contract 接入右侧承载区。

## 增加第四个模块（例如水体提取）

新增：

```text
modules/water/__init__.py
modules/water/plugin.py
modules/water/adapter.py
```

`plugin.py` 实现 `ProcessingModule` 并导出 `create_plugin(event_bus)`。由于启动时自动发现插件，甚至无需维护硬编码注册清单；Registry 会完成注册、API v1 兼容性校验和命令路由。具体能力接入 UI 时，应通过稳定契约进入右侧 `ModulePanel`。

如果插件声明的 `api_version` 不是 `1`，Registry 会将其记录为禁用模块，主程序继续启动，并在日志中显示当前版本和支持版本。
