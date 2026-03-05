class StateAnalyzer:
    """
    Unified state label resolver.
    Priority: sleeping > drowsy > inactive > awake > unknown

    analyze(pose_state, inactive) -> str
      pose_state : str  — state string from SleepPoseDetector
      inactive   : bool — True when person hasn't moved in >20s
    """

    def analyze(self, pose_state: str, inactive: bool = False) -> str:
        if pose_state == "sleeping":
            return "sleeping"
        if pose_state == "drowsy":
            return "drowsy"
        if inactive:
            return "inactive"
        if pose_state == "awake":
            return "awake"
        return pose_state  # "no_person" / "unknown" pass through