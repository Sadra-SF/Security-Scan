class ScannerType:
    STATIC = "static"
    DYNAMIC = "dynamic"
    NETWORK = "network"

    ALL = {STATIC, DYNAMIC, NETWORK}


class Severity:
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

    ORDER = [INFO, LOW, MEDIUM, HIGH, CRITICAL]