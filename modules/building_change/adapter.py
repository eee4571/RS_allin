from core.mock_adapter import TimedMockAdapter


class BuildingChangeAdapter(TimedMockAdapter):
    def __init__(self, event_bus):
        super().__init__(event_bus, "building_change", "building_change")

