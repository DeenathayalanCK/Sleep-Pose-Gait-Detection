class StateAnalyzer:

    def analyze(self, eye_closed, nod, inactive):

        if eye_closed and inactive:
            return "sleeping"

        if nod:
            return "drowsy"

        if inactive:
            return "inactive"

        return "normal"