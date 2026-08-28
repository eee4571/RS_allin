from core.models import (
    Command,
    ParameterDefinition as Param,
    ResultTypeDefinition,
    ToolDefinition,
    WorkflowDefinition as Workflow,
    WorkflowStep as Step,
)
from core.module_api import ProcessingModule
from modules.road.adapter import RoadAdapter


class RoadPlugin(ProcessingModule):
    module_id = "road"
    display_name = "道路变化检测"
    module_version = "0.2.0"
    api_version = "1"

    def __init__(self, event_bus):
        self._adapter = RoadAdapter(event_bus)

    def workflows(self):
        advanced = (
            Param("device", "计算设备", "choice", "CUDA", ("CUDA", "CPU")),
            Param("change_threshold", "变化检测阈值", "float", 0.55),
            Param("processing_mode", "处理模式", "choice", "标准", ("快速", "标准")),
        )
        full_steps = (
            Step("check", "数据检查"),
            Step("extract", "道路提取"),
            Step("width", "道路宽度计算"),
            Step("change", "相邻期变化检测"),
            Step("update", "成果更新"),
        )
        return (
            Workflow(
                "full_pipeline",
                "完整道路处理",
                "",
                "按区域和期次自动补算缺失成果，并更新相邻期道路变化。",
                full_steps,
                (
                    Param("area_id", "区域", "string", ""),
                    Param("periods", "处理期次", "string", "2022,2024"),
                    *advanced,
                ),
                "道路处理",
                10,
            ),
            Workflow(
                "rerun_period",
                "重跑指定期次",
                "",
                "重新生成一个期次的道路中心线、道路面与道路宽度成果。",
                (
                    Step("check", "数据检查"),
                    Step("extract", "道路提取"),
                    Step("width", "道路宽度计算"),
                    Step("update", "成果更新"),
                ),
                (
                    Param("area_id", "区域", "string", ""),
                    Param("period", "期次", "string", "2024"),
                    Param("update_related", "更新相关成果", "boolean", True),
                    *advanced,
                ),
                "道路处理",
                20,
            ),
            Workflow(
                "rerun_change_pair",
                "重跑指定变化对",
                "",
                "重新计算所选前后期之间的道路变化成果。",
                (
                    Step("check", "数据检查"),
                    Step("change", "变化检测"),
                    Step("update", "成果更新"),
                ),
                (
                    Param("area_id", "区域", "string", ""),
                    Param("before", "前期", "string", "2022"),
                    Param("after", "后期", "string", "2024"),
                    Param("update_related", "更新相关成果", "boolean", True),
                    *advanced,
                ),
                "道路处理",
                30,
            ),
        )

    def tools(self):
        return (
            ToolDefinition(
                "update_after_edit",
                "编辑后更新相关成果",
                description="供未来平台统一地图编辑完成后触发；本轮不提供 UI。",
            ),
        )

    def result_types(self):
        return (
            ResultTypeDefinition("road_centerline", "道路中心线", "line"),
            ResultTypeDefinition("road_surface", "道路面", "polygon"),
            ResultTypeDefinition("road_width", "道路宽度", "line"),
            ResultTypeDefinition("road_change", "道路变化结果", "line/polygon"),
        )

    def set_project_context(self, context):
        super().set_project_context(context)
        self._adapter.set_project_context(context)

    def handle_command(self, command: Command):
        workflows = {item.id: item for item in self.workflows()}
        if command.action == "run":
            workflow = workflows.get(command.workflow_id)
            if workflow is None:
                raise ValueError(f"未知道路工作流：{command.workflow_id}")
            self._adapter.run(command, workflow)
            return
        self._adapter.handle_action(command)


def create_plugin(event_bus):
    return RoadPlugin(event_bus)


def create_operation_page(**kwargs):
    """Lazy module-owned UI factory discovered without shell coupling."""
    from modules.road.ui.road_panel import RoadPanel

    return RoadPanel(**kwargs)
