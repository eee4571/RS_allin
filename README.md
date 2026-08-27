# 遥感智能解译综合平台（插件化原型）

这是一个独立的 PySide6 桌面软件原型。它用统一地图工作空间承载道路、建筑物提取与建筑物变化三个独立模块，当前所有处理均为定时器驱动的 Mock，不包含真实算法。

## 运行

```powershell
python -m pip install -r requirements.txt
python main.py
```

运行测试：

```powershell
python -m unittest discover -s tests -v
```

## 目录与职责

```text
main.py / main_window.py    组装通用基础设施和展示层
core/                       稳定的数据契约、总线、注册中心与共享上下文
modules/*/plugin.py         模块能力、工作流、步骤、参数、工具、结果声明
modules/*/adapter.py        原独立软件的适配边界（本轮为 Mock）
widgets/                    完全由描述模型驱动的通用 Qt 控件
styles/                     统一视觉样式
tests/                      插件发现、兼容性隔离和依赖边界测试
```

`ModuleRegistry.discover()` 自动扫描 `modules` 下提供 `create_plugin(event_bus)` 的插件包。主窗口只依赖 Registry、CommandBus、EventBus 和数据模型，不导入任何具体插件或 Adapter。

## 一次按钮点击如何流转

```text
QPushButton（运行工作流）
        ↓
WorkflowPanel 收集动态参数
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
对应 Adapter（当前为 TimedMockAdapter）
```

`WorkflowPanel` 不调用 `road.run()`，也不知道道路插件的类名。工具按钮同样转成 `Command(action="edit_feature")` 等统一命令。

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
状态栏 / 进度条 / WorkflowPanel / LogPanel
```

Adapter 和 Plugin 都没有主窗口引用，也不会操作 Qt 控件。结果通过 `ResultAvailable` 和 `LayerAdded` 事件进入共享 `LayerManager`，再同步到项目树和地图空间。

## Road 模块以后更新

修改道路内部流程时，只改：

- `modules/road/plugin.py`：增加、删除或调整 Workflow、Step、Parameter、Tool、ResultType；
- `modules/road/adapter.py`：接入或升级原道路软件的调用方式；
- 道路模块自己的内部算法文件（未来新增）。

完全不需要修改：

- `main_window.py`；
- `widgets/ribbon.py`；
- `widgets/workflow_panel.py`；
- `widgets/parameter_panel.py`。

当前 `RoadPlugin` 已仅靠自己的描述新增“道路长时序分析”，顶部功能区和右侧工作流会在重启后自动出现，作为这一扩展能力的演示。

## 增加第四个模块（例如水体提取）

新增：

```text
modules/water/__init__.py
modules/water/plugin.py
modules/water/adapter.py
```

`plugin.py` 实现 `ProcessingModule` 并导出 `create_plugin(event_bus)`。由于启动时自动发现插件，甚至无需维护硬编码注册清单；Registry 会完成注册、API v1 兼容性校验和命令路由。水体工作流会自动进入 Ribbon 和同一个 WorkflowPanel。

如果插件声明的 `api_version` 不是 `1`，Registry 会将其记录为禁用模块，主程序继续启动，并在日志中显示当前版本和支持版本。

