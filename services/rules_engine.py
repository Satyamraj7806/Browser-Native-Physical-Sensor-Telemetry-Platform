class RulesEngine:
    def evaluate(self, processed):
        if processed["magnitude"] > 18:
            return "⚠️ Drop Detected"
        return None