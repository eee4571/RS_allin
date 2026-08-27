from core.mock_adapter import TimedMockAdapter


class RoadAdapter(TimedMockAdapter):
    def __init__(self, event_bus):
        super().__init__(event_bus, "road", "road_vector")

