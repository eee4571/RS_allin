from core.mock_adapter import TimedMockAdapter


class BuildingExtractAdapter(TimedMockAdapter):
    def __init__(self, event_bus):
        super().__init__(event_bus, "building_extract", "building_vector")

