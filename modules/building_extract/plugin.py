from core.models import (
    Command,
    ParameterDefinition as Param,
    ResultTypeDefinition,
    ToolDefinition,
    WorkflowDefinition as Workflow,
    WorkflowStep as Step,
)
from core.module_api import ProcessingModule
from modules.building_extract.adapter import BuildingExtractAdapter


class BuildingExtractPlugin(ProcessingModule):
    module_id = "building_extract"
    display_name = "建筑物提取与量化"
    module_version = "0.1.0"
    api_version = "1"

    def __init__(self, event_bus):
        self._adapter = BuildingExtractAdapter(event_bus)

    def workflows(self):
        return (
            Workflow(
                "building_extraction", "建筑物提取", "BE", "提取建筑物轮廓并生成规范化面要素。",
                (
                    Step("prepare", "数据准备"), Step("extract", "建筑物提取"),
                    Step("refine", "轮廓优化"), Step("attributes", "属性计算"),
                    Step("export", "成果生成"),
                ),
                (
                    Param("image", "输入影像", "file", ""),
                    Param("period", "影像期次", "choice", "2024", ("2022", "2024")),
                    Param("min_area", "最小面积 (㎡)", "float", 20.0),
                    Param("regularize", "轮廓规则化", "boolean", True),
                ), "目标提取", 20,
            ),
            Workflow(
                "building_quantification", "建筑物量化", "BQ", "汇总建筑数量、面积、密度和空间分布指标。",
                (
                    Step("prepare", "建筑数据检查"), Step("calculate", "属性计算"),
                    Step("aggregate", "分区汇总"), Step("statistics", "量化统计"),
                ),
                (
                    Param("building_layer", "建筑物图层", "string", "建筑物提取结果"),
                    Param("group_by", "统计分区", "choice", "行政区", ("行政区", "规则网格", "全域")),
                    Param("grid_size", "网格尺寸", "integer", 500),
                    Param("report", "导出报表", "boolean", True),
                ), "目标提取", 30,
            ),
        )

    def tools(self):
        return (ToolDefinition("edit_feature", "建筑轮廓编辑"),)

    def result_types(self):
        return (ResultTypeDefinition("building_vector", "建筑物矢量", "polygon"),)

    def handle_command(self, command: Command):
        if command.action == "run":
            workflow = next(item for item in self.workflows() if item.id == command.workflow_id)
            self._adapter.run(command, workflow)
        else:
            self._adapter.execute_tool(command)


def create_plugin(event_bus):
    return BuildingExtractPlugin(event_bus)
