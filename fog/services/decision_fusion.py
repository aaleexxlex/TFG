def severity_from_score(score: float) -> str:
    if score >= 0.90:
        return "critical"
    if score >= 0.75:
        return "high"
    if score >= 0.60:
        return "medium"
    return "low"


def fuse_rule_and_ml(rule_score: float, ml_score):
    rule_score = max(0.0, min(1.0, float(rule_score)))

    if ml_score is None:
        final_score = rule_score
        decision_mode = "rules_only"
    else:
        ml_score = max(0.0, min(1.0, float(ml_score)))
        final_score = (0.6 * rule_score) + (0.4 * ml_score)
        decision_mode = "hybrid_rules_ml"

    final_score = max(0.0, min(1.0, final_score))

    return {
        "final_score": final_score,
        "final_severity": severity_from_score(final_score),
        "final_anomaly": final_score >= 0.75,
        "decision_mode": decision_mode,
    }