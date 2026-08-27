from core.models import (
    Command,
    ParameterDefinition as Param,
    ResultTypeDefinition,
    ToolDefinition,
    WorkflowDefinition as Workflow,
    WorkflowStep as Step,
)
from core.module_api import ProcessingModule
from modules.building_change.adapter import BuildingChangeAdapter


class BuildingChangePlugin(ProcessingModule):
    module_id = "building_change"
    display_name = "建筑物变化检测"
    module_version = "0.1.0"
    api_version = "1"

    def __init__(self, event_bus):
        self._adapter = BuildingChangeAdapter(event_bus)

    def workflows(self):
        return (
            Workflow(
                "building_change", "建筑物变化检测", "BC", "检测建筑物新增、拆除和轮廓变化。",
                (
                    Step("periods", "前后期数据"), Step("match", "建筑物匹配"),
                    Step("detect", "变化检测"), Step("classify", "变化分类"),
                    Step("export", "成果生成"),
                ),
                (
                    Param("before", "前期", "choice", "2022", ("2020", "2022", "2024")),
                    Param("after", "后期", "choice", "2024", ("2022", "2024", "2026")),
                    Param("iou", "匹配阈值", "float", 0.65),
                    Param("include_modified", "包含轮廓变化", "boolean", True),
                    Param("output_dir", "成果目录", "directory", ""),
                ), "变化检测", 20,
            ),
        )

    def tools(self):
        return (ToolDefinition("review_change", "变化复核"),)

    def result_types(self):
        return (ResultTypeDefinition("building_change", "建筑变化图层", "polygon"),)

    def handle_command(self, command: Command):
        if command.action == "run":
            workflow = next(item for item in self.workflows() if item.id == command.workflow_id)
            self._adapter.run(command, workflow)
        else:
            self._adapter.execute_tool(command)


def create_plugin(event_bus):
    return BuildingChangePlugin(event_bus)
