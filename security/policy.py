"""Allow-list policy for Hospital Cluster component interactions."""

policies = (
    # Portal API
    {"src": "admin", "dst": "portal", "opr": "patient:create"},
    {"src": "doctor", "dst": "portal", "opr": "patient:create"},
    {"src": "registrar", "dst": "portal", "opr": "patient:create"},
    {"src": "doctor", "dst": "portal", "opr": "card:create"},
    {"src": "admin", "dst": "portal", "opr": "appointment:create"},
    {"src": "doctor", "dst": "portal", "opr": "appointment:create"},
    {"src": "registrar", "dst": "portal", "opr": "appointment:create"},
    {"src": "doctor", "dst": "portal", "opr": "investigation:create"},
    {"src": "doctor", "dst": "portal", "opr": "prescription:create"},

    # Laboratory API
    {"src": "admin", "dst": "laboratory", "opr": "investigation:list_ordered"},
    {"src": "lab_tech", "dst": "laboratory", "opr": "investigation:list_ordered"},
    {"src": "doctor", "dst": "laboratory", "opr": "investigation:list_ordered"},
    {"src": "admin", "dst": "laboratory", "opr": "investigation:read"},
    {"src": "lab_tech", "dst": "laboratory", "opr": "investigation:read"},
    {"src": "doctor", "dst": "laboratory", "opr": "investigation:read"},
    {"src": "admin", "dst": "laboratory", "opr": "sample:register"},
    {"src": "lab_tech", "dst": "laboratory", "opr": "sample:register"},
    {"src": "admin", "dst": "laboratory", "opr": "sample:to_storage"},
    {"src": "lab_tech", "dst": "laboratory", "opr": "sample:to_storage"},
    {"src": "admin", "dst": "laboratory", "opr": "sample:to_analysis"},
    {"src": "lab_tech", "dst": "laboratory", "opr": "sample:to_analysis"},
    {"src": "admin", "dst": "laboratory", "opr": "analyzer:create"},
    {"src": "tech", "dst": "laboratory", "opr": "analyzer:create"},
    {"src": "admin", "dst": "laboratory", "opr": "workstation:create"},
    {"src": "tech", "dst": "laboratory", "opr": "workstation:create"},
    {"src": "admin", "dst": "laboratory", "opr": "analyzer_result:create"},
    {"src": "lab_tech", "dst": "laboratory", "opr": "analyzer_result:create"},
    {"src": "admin", "dst": "laboratory", "opr": "investigation:complete"},
    {"src": "lab_tech", "dst": "laboratory", "opr": "investigation:complete"},
    {"src": "doctor", "dst": "laboratory", "opr": "investigation:complete"},
    {"src": "admin", "dst": "laboratory", "opr": "equipment:create"},
    {"src": "tech", "dst": "laboratory", "opr": "equipment:create"},
    {"src": "admin", "dst": "laboratory", "opr": "monitoring:add_metric"},
    {"src": "tech", "dst": "laboratory", "opr": "monitoring:add_metric"},
    {"src": "admin", "dst": "laboratory", "opr": "diagnostic:add"},
    {"src": "tech", "dst": "laboratory", "opr": "diagnostic:add"},

    # Pharmacy API
    {"src": "admin", "dst": "pharmacy", "opr": "prescription:read"},
    {"src": "pharmacist", "dst": "pharmacy", "opr": "prescription:read"},
    {"src": "doctor", "dst": "pharmacy", "opr": "prescription:read"},
    {"src": "admin", "dst": "pharmacy", "opr": "scanner:prescription"},
    {"src": "pharmacist", "dst": "pharmacy", "opr": "scanner:prescription"},
    {"src": "scanner", "dst": "pharmacy", "opr": "scanner:prescription"},
    {"src": "admin", "dst": "pharmacy", "opr": "scanner:medicine"},
    {"src": "pharmacist", "dst": "pharmacy", "opr": "scanner:medicine"},
    {"src": "scanner", "dst": "pharmacy", "opr": "scanner:medicine"},
    {"src": "admin", "dst": "pharmacy", "opr": "prescription:dispense"},
    {"src": "pharmacist", "dst": "pharmacy", "opr": "prescription:dispense"},

    # LLM API
    {"src": "admin", "dst": "llm", "opr": "llm:generate_report"},
    {"src": "doctor", "dst": "llm", "opr": "llm:generate_report"},
    {"src": "lab_tech", "dst": "llm", "opr": "llm:generate_report"},
    {"src": "admin", "dst": "llm", "opr": "llm:read_reports"},
    {"src": "doctor", "dst": "llm", "opr": "llm:read_reports"},
    {"src": "patient", "dst": "llm", "opr": "llm:read_reports"},

    # Service-to-database access
    {"src": "portal", "dst": "postgres", "opr": "patient:create"},
    {"src": "portal", "dst": "postgres", "opr": "card:create"},
    {"src": "portal", "dst": "postgres", "opr": "appointment:create"},
    {"src": "portal", "dst": "postgres", "opr": "investigation:create"},
    {"src": "portal", "dst": "postgres", "opr": "prescription:create"},
    {"src": "laboratory", "dst": "postgres", "opr": "investigation:list_ordered"},
    {"src": "laboratory", "dst": "postgres", "opr": "investigation:read"},
    {"src": "laboratory", "dst": "postgres", "opr": "sample:register"},
    {"src": "laboratory", "dst": "postgres", "opr": "sample:to_storage"},
    {"src": "laboratory", "dst": "postgres", "opr": "sample:to_analysis"},
    {"src": "laboratory", "dst": "postgres", "opr": "analyzer:create"},
    {"src": "laboratory", "dst": "postgres", "opr": "workstation:create"},
    {"src": "laboratory", "dst": "postgres", "opr": "analyzer_result:create"},
    {"src": "laboratory", "dst": "postgres", "opr": "investigation:complete"},
    {"src": "laboratory", "dst": "postgres", "opr": "equipment:create"},
    {"src": "laboratory", "dst": "postgres", "opr": "monitoring:add_metric"},
    {"src": "laboratory", "dst": "postgres", "opr": "diagnostic:add"},
    {"src": "pharmacy", "dst": "postgres", "opr": "prescription:read"},
    {"src": "pharmacy", "dst": "postgres", "opr": "scanner:prescription"},
    {"src": "pharmacy", "dst": "postgres", "opr": "scanner:medicine"},
    {"src": "pharmacy", "dst": "postgres", "opr": "prescription:dispense"},
    {"src": "llm", "dst": "postgres", "opr": "llm:generate_report"},
    {"src": "llm", "dst": "postgres", "opr": "llm:read_reports"},
)


def check_operation(id, details) -> bool:
    """Check whether a source can perform an operation against a destination."""
    src: str = details.get("source")
    dst: str = details.get("deliver_to")
    opr: str = details.get("operation")

    if not all((src, dst, opr)):
        return False

    print(f"[info] checking policies for event {id}, {src}->{dst}: {opr}")
    return {"src": src, "dst": dst, "opr": opr} in policies
