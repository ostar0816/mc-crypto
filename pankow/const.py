from enum import Enum, IntEnum

# Task State to update results per each step


class TaskState(Enum):
    STATE_NONE = 'none'
    STATE_PROGRESS = 'progress'
    STATE_STEP_PASSED = 'step_passed'
    # check_balance or exchange success
    STATE_SUCCESS = 'success'
    # A whole trade plan completed
    STATE_COMPLETED = 'completed'
    STATE_FAILED = 'failed'


class OrderRetry(IntEnum):
    # Retry time interval in seconds
    ORDER_COUNT = 5
    STATUS_INTERVAL = 5
    STATUS_LOOP_COUNT = 5
    STATUS_PARTIAL_COUNT = 5


class LoopTag(Enum):
    VERIFY_PAYLOAD = 'verify_payload'
    BALANCE = 'balance'
    PLACE_ORDER = 'place_order'
    ORDER_STATUS = 'order_status'
    FINAL_STATUS = 'final_status'
    CONNECTION_ERROR = 'connection_error'


class ExecutionType(Enum):
    SEQUENTIAL = 'sequential'
    PARALLEL = 'parallel'


class DebugLevel(IntEnum):
    NONE = 0
    INTERNAL = 1
    CLIENT = 2
