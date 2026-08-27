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
    display_name = "道路智能分析"
    module_version = "0.1.0"
    api_version = "1"

    def __init__(self, event_bus):
        self._adapter = RoadAdapter(event_bus)

    def workflows(self):
        common = (
            Param("device", "计算设备", "choice", "CUDA", ("CUDA", "CPU")),
            Param("output_dir", "成果目录", "directory", ""),
        )
        return (
            Workflow(
                "road_extraction", "道路提取", "RE", "从遥感影像生成道路中心线、路面与宽度成果。",
                (
                    Step("check", "数据检查"),
                    Step("centerline", "道路中心线提取"),
                    Step("surface", "道路面提取"),
                    Step("width", "道路宽度计算"),
                    Step("export", "结果生成"),
                ),
                (
                    Param("period", "影像期次", "choice", "2024", ("2022", "2024")),
                    Param("mode", "处理模式", "choice", "Fast", ("Fast", "Full")),
                    *common,
                ), "目标提取", 10,
            ),
            Workflow(
                "road_change", "道路变化检测", "RC", "识别两期影像间新增、消失与形态变化的道路。",
                (
                    Step("periods", "选择前后期"), Step("detect", "变化检测"),
                    Step("classify", "变化分类"), Step("export", "结果生成"),
                ),
                (
                    Param("before", "前期", "choice", "2022", ("2020", "2022", "2024")),
                    Param("after", "后期", "choice", "2024", ("2022", "2024", "2026")),
                    Param("threshold", "变化阈值", "float", 0.55), *common,
                ), "变化检测", 10,
            ),
            # This extra workflow demonstrates that editing only this plugin changes the shell.
            Workflow(
                "road_timeseries", "道路长时序分析", "RT", "分析多期道路网络的演化趋势。",
                (
                    Step("series", "时序数据检查"), Step("align", "跨期配准"),
                    Step("trend", "趋势分析"), Step("export", "报告生成"),
                ),
                (
                    Param("start_year", "起始年份", "integer", 2018),
                    Param("end_year", "结束年份", "integer", 2024),
                    Param("include_report", "生成统计报告", "boolean", True), *common,
                ), "变化检测", 30,
            ),
        )

    def tools(self):
        return (ToolDefinition("edit_feature", "道路人工编辑"),)

    def result_types(self):
        return (ResultTypeDefinition("road_vector", "道路矢量", "line/polygon"),)

    def handle_command(self, command: Command):
        if command.action == "run":
            workflow = next(item for item in self.workflows() if item.id == command.workflow_id)
            self._adapter.run(command, workflow)
        else:
            self._adapter.execute_tool(command)


def create_plugin(event_bus):
    return RoadPlugin(event_bus)
