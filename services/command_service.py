class CommandService:
    def validate(self, data):
        if not data.get("device_id"):
            return False, "Missing device_id"
        if not data.get("command"):
            return False, "Missing command"
        return True, None