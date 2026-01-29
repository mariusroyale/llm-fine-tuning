package com.payment;

import java.util.ArrayList;
import java.util.List;

/**
 * Result of a fraud detection check on a payment.
 * Contains risk score and identified risk factors.
 */
public class FraudCheckResult {

    private int riskScore;
    private List<String> riskFactors;
    private static final int HIGH_RISK_THRESHOLD = 50;

    public FraudCheckResult() {
        this.riskScore = 0;
        this.riskFactors = new ArrayList<>();
    }

    /**
     * Checks if the payment is considered high risk.
     * @return true if risk score exceeds threshold
     */
    public boolean isHighRisk() {
        return riskScore >= HIGH_RISK_THRESHOLD;
    }

    /**
     * Gets the risk level as a category.
     * @return LOW, MEDIUM, or HIGH
     */
    public String getRiskLevel() {
        if (riskScore < 25) {
            return "LOW";
        } else if (riskScore < HIGH_RISK_THRESHOLD) {
            return "MEDIUM";
        } else {
            return "HIGH";
        }
    }

    /**
     * Adds a risk factor to the result.
     * @param factor description of the risk factor
     */
    public void addRiskFactor(String factor) {
        this.riskFactors.add(factor);
    }

    public int getRiskScore() { return riskScore; }
    public void setRiskScore(int riskScore) { this.riskScore = riskScore; }

    public List<String> getRiskFactors() { return riskFactors; }
}
