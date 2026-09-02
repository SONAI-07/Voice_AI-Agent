from prometheus_client import Counter, Gauge, Histogram


# ================================================================
# CALL METRICS
# ================================================================

CALLS_TOTAL = Counter(
    "customer_care_calls_total",
    "Total number of voice calls accepted by the application.",
    ["environment"],
)

CALLS_ACTIVE = Gauge(
    "customer_care_calls_active",
    "Number of currently active voice calls.",
)


CALL_DURATION_SECONDS = Histogram(
    "customer_care_call_duration_seconds",
    "Voice call duration in seconds.",
    buckets=(
        1,
        5,
        10,
        30,
        60,
        120,
        300,
        600,
        1200,
    ),
)


# ================================================================
# AGENT TURN METRICS
# ================================================================

AGENT_TURNS_TOTAL = Counter(
    "customer_care_agent_turns_total",
    "Total number of agent turns processed.",
    ["environment"],
)


AGENT_TURN_ERRORS_TOTAL = Counter(
    "customer_care_agent_turn_errors_total",
    "Total number of failed agent turns.",
    ["environment", "error_type"],
)


AGENT_TURN_LATENCY_SECONDS = Histogram(
    "customer_care_agent_turn_latency_seconds",
    "Agent turn latency in seconds.",
    buckets=(
        0.1,
        0.25,
        0.5,
        1,
        2,
        5,
        10,
        20,
        30,
        60,
    ),
)


AGENT_INTERRUPTS_TOTAL = Counter(
    "customer_care_agent_interrupts_total",
    "Number of agent turns interrupted by the customer.",
)


# ================================================================
# AGENT QUEUE
# ================================================================

AGENT_QUEUE_DEPTH = Gauge(
    "customer_care_agent_queue_depth",
    "Current number of agent turns waiting to be processed.",
)


# ================================================================
# STT
# ================================================================

STT_EVENTS_TOTAL = Counter(
    "customer_care_stt_events_total",
    "Total STT events received.",
    ["event_type"],
)


STT_ERRORS_TOTAL = Counter(
    "customer_care_stt_errors_total",
    "Total STT processing errors.",
    ["error_type"],
)


# ================================================================
# TTS
# ================================================================

TTS_REQUESTS_TOTAL = Counter(
    "customer_care_tts_requests_total",
    "Total TTS synthesis requests.",
)


TTS_ERRORS_TOTAL = Counter(
    "customer_care_tts_errors_total",
    "Total TTS synthesis failures.",
    ["error_type"],
)


TTS_LATENCY_SECONDS = Histogram(
    "customer_care_tts_latency_seconds",
    "TTS synthesis latency.",
    buckets=(
        0.1,
        0.25,
        0.5,
        1,
        2,
        5,
        10,
        20,
    ),
)


# ================================================================
# BUSINESS ACTIONS
# ================================================================

BUSINESS_ACTIONS_TOTAL = Counter(
    "customer_care_business_actions_total",
    "Total business actions attempted.",
    ["action"],
)


BUSINESS_ACTION_ERRORS_TOTAL = Counter(
    "customer_care_business_action_errors_total",
    "Total business action failures.",
    ["action", "error_type"],
)


BUSINESS_ACTION_LATENCY_SECONDS = Histogram(
    "customer_care_business_action_latency_seconds",
    "Business action latency.",
    ["action"],
    buckets=(
        0.1,
        0.5,
        1,
        2,
        5,
        10,
        20,
        30,
    ),
)


# ================================================================
# POST CALL
# ================================================================

POST_CALL_TOTAL = Counter(
    "customer_care_post_call_total",
    "Total post-call processing attempts.",
)


POST_CALL_ERRORS_TOTAL = Counter(
    "customer_care_post_call_errors_total",
    "Total post-call processing failures.",
    ["error_type"],
)


POST_CALL_LATENCY_SECONDS = Histogram(
    "customer_care_post_call_latency_seconds",
    "Post-call processing latency.",
    buckets=(
        0.5,
        1,
        2,
        5,
        10,
        20,
        30,
        60,
        120,
    ),
)


# ================================================================
# PROVIDER HEALTH
# ================================================================

PROVIDER_ERRORS_TOTAL = Counter(
    "customer_care_provider_errors_total",
    "Total external provider errors.",
    ["provider", "operation", "error_type"],
)


PROVIDER_REQUESTS_TOTAL = Counter(
    "customer_care_provider_requests_total",
    "Total external provider requests.",
    ["provider", "operation"],
)


PROVIDER_LATENCY_SECONDS = Histogram(
    "customer_care_provider_latency_seconds",
    "External provider request latency.",
    ["provider", "operation"],
    buckets=(
        0.1,
        0.25,
        0.5,
        1,
        2,
        5,
        10,
        20,
        30,
        60,
    ),
)


# ================================================================
# RESILIENCE
# ================================================================

RETRIES_TOTAL = Counter(
    "customer_care_retries_total",
    "Total external operation retries.",
    ["provider", "operation"],
)


TIMEOUTS_TOTAL = Counter(
    "customer_care_timeouts_total",
    "Total external operation timeouts.",
    ["provider", "operation"],
)